#!/usr/bin/env python3
"""Offline transport adapter behavior and CLI contract checks."""

import contextlib
import copy
import datetime as dt
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("odjazdy", ROOT / "skills/odjazdy/scripts/odjazdy.py")
od = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(od)
FROZEN = dt.datetime(2026, 11, 5, 21, 42, tzinfo=dt.timezone.utc)


def fixture(name):
    return json.loads((ROOT / "skills/odjazdy/resources" / (name + ".json")).read_text(encoding="utf-8"))


def invoke(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = od.main(args)
    return code, out.getvalue(), err.getvalue()


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(od.urllib.request, "urlopen", side_effect=AssertionError("Unexpected network call"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.clock = patch.object(od, "now", return_value=FROZEN)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def assert_error(self, args, expected):
        code, out, err = invoke(args)
        self.assertEqual(code, expected, err)
        self.assertEqual(out, "")
        self.assertIn("error", json.loads(err))

    def test_cities_offline_lists_three_supported_networks(self):
        code, out, err = invoke(["cities"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual({c["id"] for c in json.loads(out)["cities"]}, {"gdansk", "poznan", "szczecin"})

    def test_invalid_inputs_do_not_fetch(self):
        for args in (["stops", "Warszawa"], ["stops", "gdansk", "--lat", "54"], ["stops", "gdansk", "--lat", "nan", "--lon", "18"], ["stops", "poznan", "--lat", "52", "--lon", "16"], ["stops", "poznan"], ["stops", "gdansk", "--limit", "0"], ["departures", "gdansk", "../x"], ["departures", "szczecin", "abc"], ["stops", "gdansk", "--query", " "], ["departures", "poznan", "RKAP71", "--line", ""]):
            with self.subTest(args=args):
                self.assert_error(args, 64)

    def test_szczecin_gps_and_double_escaped_names(self):
        data = {"data": [{"number": "1", "name": "Plac Ko\\u015bciuszki", "latitude": 53.4, "longitude": 14.5}, {"number": "2", "name": "Daleko", "latitude": 53.8, "longitude": 14.8}, {"number": "3", "name": "Techniczny", "latitude": 53.4, "longitude": 14.5, "technical": True}]}
        with patch.object(od, "request", return_value=data):
            result = od.stop_search("szczecin", lat=53.4, lon=14.5, limit=1)
        self.assertEqual(result["stops"][0]["name"], "Plac Kościuszki")
        self.assertEqual(result["stops"][0]["distance_m"], 0)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["matched_count"], 2)

    def test_gdansk_selects_today_instead_of_future_timetable(self):
        def bundle(name):
            return {"lastUpdate": "2026-11-05 02:25:05", "stops": [{"stopId": 1, "stopDesc": name, "stopName": name, "stopLat": 54.3, "stopLon": 18.6}]}
        with patch.object(od, "request", return_value={"2026-11-06": bundle("Future"), "2026-11-04": bundle("Past"), "2026-11-05": bundle("Dziś")}):
            result = od.stop_search("gdansk", "Dzis")
        self.assertEqual(result["stops"][0]["name"], "Dziś")

    def test_peka_stop_uses_tag_for_departure_identifier(self):
        with patch.object(od, "peka", side_effect=[[{"name": "Rondo Kaponiera"}], fixture("poznan-stops")["success"]]):
            result = od.stop_search("poznan", "Rondo Kaponiera")
        self.assertEqual(result["stops"][0]["id"], "RKAP71")
        self.assertEqual(result["stops"][0]["public_code"], "RKAP01")

    def test_szczecin_fresh_board_signed_delay_and_line_filter(self):
        with patch.object(od, "request", return_value=fixture("szczecin-departures")):
            result = od.departures("szczecin", "10822", line="8")
        self.assertEqual(result["freshness"], "current")
        self.assertEqual(result["departures"][0]["delay_seconds"], -30)
        self.assertTrue(result["departures"][0]["usable_realtime"])
        self.assertEqual(result["departures"][0]["destination"], "Gumieńce")
        self.assertEqual(len(result["departures"]), 1)

    def test_szczecin_canceled_and_scheduled_are_distinct(self):
        data = fixture("szczecin-departures")
        data["data"]["departures"][0]["departure_time"]["canceled"] = True
        data["data"]["departures"][1]["departure_time"]["real_time"] = False
        with patch.object(od, "request", return_value=data):
            result = od.departures("szczecin", "10822")
        canceled, scheduled = result["departures"][:2]
        self.assertEqual(canceled["status"], "canceled")
        self.assertFalse(canceled["usable_realtime"])
        self.assertEqual(scheduled["status"], "scheduled")
        self.assertIsNone(scheduled["estimated_at"])

    def test_stale_board_is_flagged_without_dropping_provider_values(self):
        data = fixture("szczecin-departures")
        data["data"]["updated_at"] = "2026-11-05T20:00:00Z"
        with patch.object(od, "request", return_value=data):
            result = od.departures("szczecin", "10822")
        self.assertEqual(result["freshness"], "stale")
        self.assertTrue(result["departures"][0]["realtime"])
        self.assertFalse(result["departures"][0]["usable_realtime"])
        self.assertTrue(result["warnings"])

    def test_gdansk_old_vehicle_and_schedule_missing_is_not_zero_delay(self):
        data = {"lastUpdate": "2026-11-05T21:41:59Z", "departures": [{"routeId": 3, "headsign": "Nowy Port", "status": "REALTIME", "estimatedTime": "2026-11-05T21:45:00Z", "timestamp": "2026-11-05T21:00:00Z"}, {"routeId": 2, "status": "SCHEDULED", "estimatedTime": "2026-11-05T22:00:00Z", "delayInSeconds": 0}]}
        with patch.object(od, "request", return_value=data):
            result = od.departures("gdansk", "2001")
        self.assertTrue(result["departures"][0]["measurement_stale"])
        self.assertFalse(result["departures"][0]["usable_realtime"])
        self.assertIsNone(result["departures"][1]["delay_seconds"])
        self.assertIsNone(result["departures"][1]["estimated_at"])

    def test_peka_local_time_is_not_misinterpreted_as_utc(self):
        data = fixture("poznan-departures")["success"]
        with patch.object(od, "peka", side_effect=[data, FROZEN.timestamp() * 1000]):
            result = od.departures("poznan", "RKAP71")
        first = result["departures"][0]
        self.assertEqual(first["scheduled_local"], "2026-11-05T22:42:00.000")
        self.assertEqual(first["scheduled_timezone"], "Europe/Warsaw")
        self.assertEqual(first["estimated_at"], "2026-11-05T21:42:00Z")
        self.assertIsNone(first["scheduled_at"])
        self.assertEqual(result["freshness"], "unknown")
        self.assertFalse(first["usable_realtime"])
        self.assertIsNone(result["departures"][2]["estimated_at"])

    def test_future_vehicle_timestamp_cannot_be_usable_realtime(self):
        data = {"lastUpdate": "2026-11-05T21:41:59Z", "departures": [{"routeId": 3, "status": "REALTIME", "estimatedTime": "2026-11-05T21:45:00Z", "timestamp": "2026-11-06T21:42:00Z"}]}
        with patch.object(od, "request", return_value=data):
            result = od.departures("gdansk", "2001")
        self.assertTrue(result["departures"][0]["measurement_stale"])
        self.assertFalse(result["departures"][0]["usable_realtime"])

    def test_invalid_departure_timestamp_is_format_error(self):
        for invalid in ("bad-timestamp", "2026-11-05T22:00:00"):
            with self.subTest(invalid=invalid), patch.object(od, "request", return_value={"lastUpdate": "2026-11-05T21:41:59Z", "departures": [{"routeId": 3, "status": "REALTIME", "estimatedTime": invalid}]}):
                self.assert_error(["departures", "gdansk", "2001"], 69)

    def test_empty_board_success_is_not_network_error(self):
        with patch.object(od, "request", return_value={"lastUpdate": "2026-11-05T21:41:59Z", "departures": []}):
            code, out, err = invoke(["departures", "Gdańsk", "2001"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["status"], "no_departures")

    def test_malformed_payload_is_structured_error(self):
        with patch.object(od, "request", return_value={"departures": None}):
            self.assert_error(["departures", "gdansk", "2001"], 69)

    def test_warsaw_day_handles_midnight_and_dst(self):
        self.assertEqual(od.warsaw_date(dt.datetime(2026, 7, 1, 22, 30, tzinfo=dt.timezone.utc)), dt.date(2026, 7, 2))
        self.assertEqual(od.warsaw_date(dt.datetime(2026, 11, 5, 22, 30, tzinfo=dt.timezone.utc)), dt.date(2026, 11, 5))

    def test_fresh_http_cache_and_etag_revalidation(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(od.os.environ, {"ODJAZDY_CACHE_DIR": folder}):
            response = Mock()
            response.read.return_value = b'{"data": []}'
            response.headers = {"Cache-Control": "max-age=60", "ETag": '"v1"'}
            context = Mock()
            context.__enter__ = Mock(return_value=response)
            context.__exit__ = Mock(return_value=False)
            with patch.object(od.urllib.request, "urlopen", return_value=context) as fetch, patch.object(od.time, "time", return_value=1000):
                od.request("https://www.zditm.szczecin.pl/api/v2/stops")
                od.request("https://www.zditm.szczecin.pl/api/v2/stops")
                self.assertEqual(fetch.call_count, 1)
            not_modified = urllib.error.HTTPError("x", 304, "Not Modified", {}, io.BytesIO())
            with patch.object(od.urllib.request, "urlopen", side_effect=not_modified) as fetch, patch.object(od.time, "time", return_value=1061):
                self.assertEqual(od.request("https://www.zditm.szczecin.pl/api/v2/stops"), {"data": []})
                self.assertEqual(fetch.call_args[0][0].get_header("If-none-match"), '"v1"')

    def test_expired_cache_does_not_hide_outage(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(od.os.environ, {"ODJAZDY_CACHE_DIR": folder}):
            with patch.object(od.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
                self.assert_error(["departures", "szczecin", "10822"], 69)


if __name__ == "__main__":
    unittest.main()
