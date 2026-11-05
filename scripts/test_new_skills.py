#!/usr/bin/env python3
"""Offline behavioral tests for CERT, GIOŚ and BZP; no network or third-party packages."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    path = ROOT / "skills" / name / "scripts" / (name.replace("-", "_") + ".py")
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cert, smog, bzp = load("cert-pl"), load("smog"), load("przetargi")


def fixture(skill, name):
    return json.loads((ROOT / "skills" / skill / "resources" / (name + ".json")).read_text(encoding="utf-8"))


def invoke(module, args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = module.main(args)
    return code, out.getvalue(), err.getvalue()


class OfflineTest(unittest.TestCase):
    def setUp(self):
        self.network = patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network request"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def assert_error(self, module, args, expected):
        code, out, err = invoke(module, args)
        self.assertEqual(code, expected, err)
        self.assertEqual(out, "")
        self.assertIn("error", json.loads(err))
        self.assertIn("type", json.loads(err))


class CertTests(OfflineTest):
    def setUp(self):
        super().setUp()
        self.body = (ROOT / "skills/cert-pl/resources/domains.txt").read_bytes()
        self.domains = cert.parse_list(self.body)

    def test_domain_normalization_and_idn(self):
        self.assertEqual(cert.domain_name("HTTPS://ŻÓŁĆ.example:443/path?q=1#test"), "xn--kda4b0koi.example")
        self.assertEqual(cert.domain_name("BAD.Example."), "bad.example")

    def test_invalid_inputs_never_fetch(self):
        for address in ("", "bad example", "127.0.0.1", "http://[::1]/", "ftp://bad.example", "https://user:pass@bad.example",
                        "https://bad.example:invalid", "https://bad.example\\@good.example", "-bad.example"):
            with self.subTest(address=address):
                self.assert_error(cert, ["check", address], 64)

    def test_match_boundaries_and_negative_contract(self):
        with patch.object(cert, "load_domains", return_value=(self.domains, 1000, False)):
            for address, matched in (("bad.example", "bad.example"), ("x.bad.example", "bad.example"),
                                     ("notbad.example", None), ("bad.example.other", None),
                                     ("nested.example", None), ("x.a.nested.example", "a.nested.example")):
                with self.subTest(address=address):
                    code, out, err = invoke(cert, ["check", address])
                    self.assertEqual((code, err), (0, ""))
                    result = json.loads(out)
                    self.assertEqual(result["matched_domain"], matched)
                    self.assertEqual(result["listed"], matched is not None)
                    if matched is None:
                        self.assertIn("Nie jest to potwierdzenie", result["message"])

    def test_fresh_cache_no_request(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cache.json"
            path.write_text(json.dumps({"source": cert.SOURCE, "fetched_at": 1000, "text": self.body.decode()}))
            domains, timestamp, cached = cert.load_domains(path, now=1299)
            self.assertTrue(cached)
            self.assertEqual(timestamp, 1000)
            self.assertIn("bad.example", domains)

    def test_expired_cache_refresh_failure_is_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cache.json"
            path.write_text(json.dumps({"source": cert.SOURCE, "fetched_at": 1000, "text": self.body.decode()}))
            with patch.object(cert.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
                with self.assertRaises(cert.SkillError) as error:
                    cert.load_domains(path, now=1300)
                self.assertEqual(error.exception.code, 69)

    def test_cache_refresh_atomic_and_future_timestamp_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cache.json"
            path.write_text(json.dumps({"source": cert.SOURCE, "fetched_at": 2000, "text": self.body.decode()}))
            with patch.object(cert.urllib.request, "urlopen", return_value=io.BytesIO(self.body)) as fetch:
                _, timestamp, cached = cert.load_domains(path, now=1000)
            self.assertFalse(cached)
            self.assertEqual(timestamp, 1000)
            self.assertEqual(fetch.call_args[0][0].full_url, cert.SOURCE)
            self.assertEqual(json.loads(path.read_text())["fetched_at"], 1000)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_cache_write_failure_still_returns_live_result(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(cert.urllib.request, "urlopen", return_value=io.BytesIO(self.body)), \
                    patch.object(cert.Path, "mkdir", side_effect=PermissionError("read-only")):
                domains, _, cached = cert.load_domains(Path(folder) / "cache.json", now=1000)
                self.assertFalse(cached)
                self.assertIn("bad.example", domains)

    def test_corrupt_cache_refreshes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cache.json"
            path.write_text("broken JSON")
            with patch.object(cert.urllib.request, "urlopen", return_value=io.BytesIO(self.body)):
                self.assertFalse(cert.load_domains(path, now=1000)[2])

    def test_invalid_upstream_list(self):
        for body in (b"", b"<html>blocked</html>", b"https://bad.example/", b"bad.example\n\xff"):
            with self.assertRaises(cert.SkillError) as error:
                cert.parse_list(body)
            self.assertEqual(error.exception.code, 69)


class SmogTests(OfflineTest):
    def setUp(self):
        super().setUp()
        self.catalog = fixture("smog", "stations")
        self.sensors = fixture("smog", "sensors")
        self.index = fixture("smog", "index")
        self.data = fixture("smog", "measurements")

    def fetch(self, path, params=None):
        if path == "station/findAll":
            return copy.deepcopy(self.catalog)
        if path.startswith("station/sensors/"):
            return copy.deepcopy(self.sensors)
        if path.startswith("aqindex/"):
            return copy.deepcopy(self.index)
        if path.startswith("data/getData/"):
            return copy.deepcopy(self.data)
        raise AssertionError(path)

    def test_city_multiple_stations_and_ascii(self):
        with patch.object(smog, "fetch", side_effect=self.fetch):
            rows = smog.stations("Krakow")
        self.assertEqual([r["id"] for r in rows], [400, 401])

    def test_missing_city(self):
        with patch.object(smog, "fetch", side_effect=self.fetch):
            self.assert_error(smog, ["stations", "--city", "Nieistniejące"], 2)

    def test_station_index_and_measurement_time(self):
        with patch.object(smog, "fetch", side_effect=self.fetch):
            code, out, err = invoke(smog, ["station", "400"])
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data["index"]["category"], self.index["AqIndex"]["Nazwa kategorii indeksu"])
        self.assertEqual(data["measurement_timezone"], "Europe/Warsaw")
        self.assertEqual(data["measurements"][0]["unit"], "µg/m³")
        self.assertEqual(data["measurements"][0]["measured_at"], self.data[smog.DATA][0]["Data"])

    def test_latest_null_uses_older_value_but_reports_gap(self):
        self.data[smog.DATA][0]["Wartość"] = None
        with patch.object(smog, "fetch", side_effect=self.fetch):
            row = smog.latest(self.sensors[smog.SENSORS][0])
        self.assertEqual(row["status"], "latest_slot_missing")
        self.assertEqual(row["measured_at"], self.data[smog.DATA][1]["Data"])
        self.assertEqual(row["latest_slot_at"], self.data[smog.DATA][0]["Data"])

    def test_all_missing_not_zero(self):
        for row in self.data[smog.DATA]:
            row["Wartość"] = None
        with patch.object(smog, "fetch", side_effect=self.fetch):
            row = smog.latest(self.sensors[smog.SENSORS][0])
        self.assertIsNone(row["value"])
        self.assertIsNone(row["measured_at"])
        self.assertEqual(row["status"], "no_current_data")

    def test_zero_is_a_valid_measurement(self):
        self.data[smog.DATA][0]["Wartość"] = 0
        with patch.object(smog, "fetch", side_effect=self.fetch):
            row = smog.latest(self.sensors[smog.SENSORS][0])
        self.assertEqual((row["value"], row["status"]), (0, "available"))

    def test_nearest_station(self):
        with patch.object(smog, "fetch", side_effect=self.fetch):
            code, out, err = invoke(smog, ["near", "50.057678", "19.926189"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["station"]["id"], 400)
        self.assertEqual(json.loads(out)["distance_km"], 0)

    def test_invalid_coordinates_and_ids(self):
        for args in (["near", "nan", "20"], ["near", "91", "20"], ["near", "50", "inf"],
                     ["station", "0"], ["station", "wrong"], ["stations", "--city", ""]):
            self.assert_error(smog, args, 64)

    def test_pagination(self):
        rows = self.catalog[smog.STATIONS]
        pages = [{smog.STATIONS: [row], "totalPages": 2} for row in rows]
        with patch.object(smog, "fetch", side_effect=pages) as fetch:
            self.assertEqual(len(smog.stations()), 2)
        self.assertEqual([c.args[1]["page"] for c in fetch.call_args_list], [0, 1])

    def test_sensor_network_error_not_missing_data(self):
        def broken(path, params=None):
            if path.startswith("data/getData"):
                raise smog.SkillError("offline", "network_error", 69)
            return self.fetch(path, params)
        with patch.object(smog, "fetch", side_effect=broken):
            self.assert_error(smog, ["station", "400"], 69)

    def test_missing_index_and_manual_sensor(self):
        def missing(path, params=None):
            if path.startswith(("aqindex/", "data/getData/")):
                raise smog.SkillError("missing", "not_found", 2)
            return self.fetch(path, params)
        with patch.object(smog, "fetch", side_effect=missing):
            code, out, err = invoke(smog, ["station", "400"])
        self.assertEqual((code, err), (0, ""))
        self.assertIsNone(json.loads(out)["index"]["category"])
        self.assertTrue(all(m["value"] is None for m in json.loads(out)["measurements"]))

    def test_malformed_payload_is_structured_error(self):
        with patch.object(smog, "fetch", return_value={"unexpected": []}):
            self.assert_error(smog, ["stations"], 69)

    def test_actual_http_decoder_and_errors(self):
        with patch.object(smog.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(self.catalog).encode())):
            self.assertEqual(smog.fetch("station/findAll"), self.catalog)
        for status, expected in ((404, 2), (429, 69), (500, 69)):
            error = urllib.error.HTTPError(smog.BASE, status, "error", {}, None)
            with patch.object(smog.urllib.request, "urlopen", side_effect=error):
                with self.assertRaises(smog.SkillError) as result:
                    smog.fetch("station/findAll")
                self.assertEqual(result.exception.code, expected)


class BzpTests(OfflineTest):
    def setUp(self):
        super().setUp()
        self.rows = fixture("przetargi", "notices")

    def test_filters_and_unicode_province(self):
        with patch.object(bzp.Client, "fetch", return_value=self.rows) as fetch:
            code, out, err = invoke(bzp, ["search", "internet", "--voivodeship", "ŁÓDZKIE", "--cpv", "72413000-8",
                                          "--from", "2026-10-01", "--to", "2026-10-31"])
        self.assertEqual((code, err), (0, ""))
        params = fetch.call_args[0][0]
        self.assertEqual(params["OrganizationProvince"], "PL10")
        self.assertEqual(params["CpvCode"], "72413000-8")
        self.assertEqual(params["NoticeType"], "ContractNotice")
        self.assertEqual(params["PublicationDateFrom"], "2026-10-01T00:00:00Z")
        self.assertEqual(json.loads(out)["notices"][0]["id"], self.rows[0]["noticeNumber"])

    def test_empty_results(self):
        with patch.object(bzp.Client, "fetch", return_value=[]):
            self.assert_error(bzp, ["search", "unknown"], 2)

    def test_cpv_without_title_phrase(self):
        with patch.object(bzp.Client, "fetch", return_value=self.rows) as fetch:
            code, out, err = invoke(bzp, ["search", "--cpv", "72413000-8"])
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("OrderObject", fetch.call_args[0][0])
        self.assertEqual(json.loads(out)["count"], 2)

    def test_invalid_args_without_network(self):
        for args in (["search"], ["search", ""], ["search", "x", "--limit", "0"], ["search", "x", "--limit", "501"],
                     ["search", "x", "--from", "2026-02-30"], ["search", "x", "--from", "2026-11-04", "--to", "2026-11-01"],
                     ["search", "x", "--cpv", "abc"], ["search", "x", "--voivodeship", "invalid"],
                     ["notice", "../bad"], ["search", "x", "--after", "invalid"]):
            self.assert_error(bzp, args, 64)

    def test_pagination_caps_pages_and_returns_cursor(self):
        rows = [dict(self.rows[0], objectId="notice-%s" % i) for i in range(101)]
        client = Mock()
        client.fetch.side_effect = [rows[:100], rows[100:]]
        result = bzp.search(client, {"OrderObject": "x"}, 101)
        self.assertEqual([c.args[0]["PageSize"] for c in client.fetch.call_args_list], [100, 1])
        self.assertEqual(client.fetch.call_args_list[1].args[0]["SearchAfter"], "notice-99")
        self.assertEqual(result["next_cursor"], "notice-100")
        self.assertTrue(result["limit_reached"])
        self.assertIsNone(result["has_more"])

    def test_exact_limit_is_not_proof_of_more(self):
        client = Mock()
        client.fetch.return_value = self.rows
        result = bzp.search(client, {}, 2)
        self.assertIsNone(result["has_more"])
        self.assertEqual(client.fetch.call_count, 1)

    def test_short_page_exhausted(self):
        client = Mock()
        client.fetch.return_value = self.rows
        result = bzp.search(client, {}, 20)
        self.assertFalse(result["has_more"])
        self.assertIsNone(result["next_cursor"])

    def test_repeated_cursor_error(self):
        client = Mock()
        client.fetch.return_value = [self.rows[0]]
        with self.assertRaises(bzp.SkillError) as result:
            bzp.search(client, {"SearchAfter": self.rows[0]["objectId"]}, 1)
        self.assertEqual(result.exception.code, 69)

    def test_notice_number_lookup_and_content(self):
        with patch.object(bzp.Client, "fetch", return_value=self.rows) as fetch:
            code, out, err = invoke(bzp, ["notice", self.rows[0]["noticeNumber"]])
        self.assertEqual((code, err), (0, ""))
        row = json.loads(out)["notice"]
        self.assertEqual(fetch.call_args[0][0]["NoticeNumber"], self.rows[0]["noticeNumber"])
        self.assertIn("SEKCJA", row["content_text"])
        self.assertNotIn("font-family", row["content_text"])
        self.assertTrue(row["source_url"].endswith(self.rows[0]["objectId"]))

    def test_notice_must_match_requested_number(self):
        with patch.object(bzp.Client, "fetch", return_value=self.rows[1:]):
            self.assert_error(bzp, ["notice", self.rows[0]["noticeNumber"]], 2)

    def test_missing_deadline_kept_null(self):
        row = dict(self.rows[0], submittingOffersDate=None)
        self.assertIsNone(bzp.summarize(row)["offers_due_at"])

    def test_rate_limit_and_bad_parameters_are_not_empty_results(self):
        for status in (403, 429, 404, 500):
            error = urllib.error.HTTPError(bzp.BASE, status, "error", {}, None)
            with patch.object(bzp.urllib.request, "urlopen", side_effect=error):
                self.assert_error(bzp, ["search", "x"], 69)

    def test_http_decoder_and_spacing(self):
        payload = json.dumps(self.rows).encode()
        with patch.object(bzp.urllib.request, "urlopen", side_effect=[io.BytesIO(payload), io.BytesIO(payload)]), \
                patch.object(bzp.time, "monotonic", side_effect=[10, 10.5, 12.1]), patch.object(bzp.time, "sleep") as sleep:
            client = bzp.Client()
            self.assertEqual(client.fetch({}), self.rows)
            client.fetch({})
            self.assertAlmostEqual(sleep.call_args[0][0], 1.6)

    def test_malformed_upstream_json(self):
        with patch.object(bzp.urllib.request, "urlopen", return_value=io.BytesIO(b"<html>error</html>")):
            self.assert_error(bzp, ["search", "x"], 69)


def suite():
    return unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case)
                              for case in (CertTests, SmogTests, BzpTests))


if __name__ == "__main__":
    raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite()).wasSuccessful() else 1)
