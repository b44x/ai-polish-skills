#!/usr/bin/env python3
"""Offline behavioral tests for PSE prices, coverage, DST, windows and CLI errors."""
import contextlib
import copy
import datetime as dt
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("energia", ROOT / "skills/energia/scripts/energia.py")
energia = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(energia)
FIXTURE = json.loads((ROOT / "skills/energia/resources/day.json").read_text(encoding="utf-8"))["value"]


def invoke(args, rows):
    out, err = io.StringIO(), io.StringIO()
    with patch.object(energia, "get_rows", return_value=(rows, 1793880000, False)):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = energia.main(args)
    return code, out.getvalue(), err.getvalue()


def make_day(date, price=100):
    # Build authoritative UTC intervals from independently fixed DST-day boundaries.
    bounds = {
        "2026-03-29": ("2026-03-28T23:00:00+00:00", 92),
        "2026-10-25": ("2026-10-24T22:00:00+00:00", 100),
    }
    start, count = bounds[date]
    start = dt.datetime.fromisoformat(start)
    rows = []
    for i in range(count):
        a, b = start + dt.timedelta(minutes=i * 15), start + dt.timedelta(minutes=(i + 1) * 15)
        rows.append({"business_date": date, "rce_pln": price,
                     "dtime_utc": b.strftime("%Y-%m-%d %H:%M:%S"),
                     "period_utc": a.strftime("%H:%M") + " - " + b.strftime("%H:%M"),
                     "publication_ts_utc": "2026-03-01 12:00:00"})
    return rows


class EnergiaTests(unittest.TestCase):
    def setUp(self):
        network = patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network request"))
        network.start()
        self.addCleanup(network.stop)

    def test_live_fixture_complete_and_conversion(self):
        code, out, err = invoke(["day", "2026-11-04"], FIXTURE)
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertTrue(data["complete"])
        self.assertEqual(data["available_minutes"], 1440)
        self.assertEqual(len(data["intervals"]), 96)
        self.assertEqual(data["intervals"][0]["start_local"], "2026-11-04T00:00:00+01:00")
        self.assertAlmostEqual(data["intervals"][0]["rce_pln_kwh"], 0.89834)

    def test_dst_short_and_long_days_preserve_utc_continuity(self):
        for day, count, minutes in (("2026-03-29", 92, 1380), ("2026-10-25", 100, 1500)):
            code, out, err = invoke(["day", day], make_day(day))
            self.assertEqual((code, err), (0, ""))
            data = json.loads(out)
            self.assertTrue(data["complete"])
            self.assertEqual(data["expected_quarter_hours"], count)
            self.assertEqual(data["available_minutes"], minutes)
        local = [i["start_local"] for i in data["intervals"]]
        self.assertIn("2026-10-25T02:00:00+02:00", local)
        self.assertIn("2026-10-25T02:00:00+01:00", local)

    def test_gap_not_averaged_as_complete_day_or_optimized(self):
        rows = FIXTURE[:10] + FIXTURE[11:]
        code, out, err = invoke(["day", "2026-11-04"], rows)
        self.assertEqual((code, err), (0, ""))
        self.assertFalse(json.loads(out)["complete"])
        code, out, err = invoke(["cheapest", "2026-11-04"], rows)
        self.assertEqual((code, out), (69, ""))
        self.assertEqual(json.loads(err)["type"], "incomplete_data")

    def test_summary_missing_day_exposes_partial_mean(self):
        code, out, err = invoke(["summary", "--from", "2026-11-04", "--to", "2026-11-05"], FIXTURE)
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data["missing_dates"], ["2026-11-05"])
        self.assertIsNone(data["mean_full_period_pln_mwh"])
        self.assertIsNotNone(data["mean_available_pln_mwh"])

    def test_cheapest_window_and_negative_rce_component(self):
        rows = copy.deepcopy(FIXTURE)
        for i, row in enumerate(rows):
            row["rce_pln"] = -200 if 20 <= i < 28 else 400
        code, out, err = invoke(["cheapest", "2026-11-04", "--minutes", "120", "--kwh", "10"], rows)
        self.assertEqual((code, err), (0, ""))
        window = json.loads(out)["window"]
        self.assertEqual(window["start_local"], "2026-11-04T05:00:00+01:00")
        self.assertEqual(window["end_local"], "2026-11-04T07:00:00+01:00")
        self.assertEqual(window["rce_component_pln"], -2)

    def test_hourly_intervals_allow_partial_final_interval(self):
        hourly = []
        for source in FIXTURE[3::4]:
            row = dict(source, rce_pln=100)
            end = dt.datetime.fromisoformat(row["dtime_utc"])
            start = end - dt.timedelta(hours=1)
            row["period_utc"] = start.strftime("%H:%M") + " - " + end.strftime("%H:%M")
            hourly.append(row)
        for minutes, expected_end in ((15, "2026-11-04T00:15:00+01:00"),
                                      (90, "2026-11-04T01:30:00+01:00")):
            code, out, err = invoke(["cheapest", "2026-11-04", "--minutes", str(minutes), "--kwh", "2"], hourly)
            self.assertEqual((code, err), (0, ""))
            window = json.loads(out)["window"]
            self.assertEqual(window["start_local"], "2026-11-04T00:00:00+01:00")
            self.assertEqual(window["end_local"], expected_end)
            self.assertEqual(window["mean_pln_mwh"], 100)
            self.assertEqual(window["rce_component_pln"], .2)

    def test_partial_hour_window_across_spring_clock_jump(self):
        hourly = []
        for index, source in enumerate(make_day("2026-03-29")[3::4]):
            row = dict(source, rce_pln=0 if index in (1, 2) else 1000)
            end = dt.datetime.fromisoformat(row["dtime_utc"])
            start = end - dt.timedelta(hours=1)
            row["period_utc"] = start.strftime("%H:%M") + " - " + end.strftime("%H:%M")
            hourly.append(row)
        code, out, err = invoke(["cheapest", "2026-03-29", "--minutes", "90"], hourly)
        self.assertEqual((code, err), (0, ""))
        window = json.loads(out)["window"]
        self.assertEqual(window["start_local"], "2026-03-29T01:00:00+01:00")
        self.assertEqual(window["end_local"], "2026-03-29T03:30:00+02:00")

    def test_large_finite_prices_do_not_overflow_weighted_means(self):
        rows = [dict(row, rce_pln=1e308) for row in FIXTURE]
        for args in (["day", "2026-11-04"], ["cheapest", "2026-11-04"],
                     ["summary", "--from", "2026-11-04", "--to", "2026-11-04"]):
            code, out, err = invoke(args, rows)
            self.assertEqual((code, err), (0, ""))
            data = json.loads(out)
            value = data["window"]["mean_pln_mwh"] if "window" in data else data["mean_available_pln_mwh"]
            self.assertAlmostEqual(value / 1e308, 1)
        code, out, err = invoke(["cheapest", "2026-11-04", "--kwh", "1000000"], rows)
        self.assertEqual((code, out), (69, ""))
        self.assertEqual(json.loads(err)["type"], "upstream_format")

    def test_window_during_clock_fold_measures_elapsed_minutes(self):
        rows = make_day("2026-10-25", 1000)
        for row in rows[8:16]:
            row["rce_pln"] = 0
        code, out, err = invoke(["cheapest", "2026-10-25", "--minutes", "120"], rows)
        self.assertEqual((code, err), (0, ""))
        window = json.loads(out)["window"]
        self.assertEqual(window["start_local"], "2026-10-25T02:00:00+02:00")
        self.assertEqual(window["end_local"], "2026-10-25T03:00:00+01:00")

    def test_no_data_is_not_zero_or_default_date(self):
        code, out, err = invoke(["day", "2030-01-01"], [])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(json.loads(err)["type"], "not_found")

    def test_validation_rejects_bad_parameters_before_network(self):
        for args in (["day", "2026-02-30"], ["day", "bad"], ["cheapest", "--minutes", "17"],
                     ["cheapest", "--kwh", "nan"], ["summary", "--from", "2026-01-01", "--to", "2026-02-01"],
                     ["summary", "--from", "2026-01-02", "--to", "2026-01-01"]):
            code, out, err = invoke(args, FIXTURE)
            self.assertEqual((code, out), (64, ""), args)
            self.assertIn("error", json.loads(err))

    def test_invalid_upstream_price_and_time_fail(self):
        for field, value in (("rce_pln", None), ("rce_pln", float("nan")), ("dtime_utc", "bad"),
                             ("period_utc", "10:00 - 11:00"), ("business_date", "2026-11-03")):
            rows = copy.deepcopy(FIXTURE)
            rows[0][field] = value
            code, out, err = invoke(["day", "2026-11-04"], rows)
            self.assertEqual((code, out), (69, ""), field)
            self.assertEqual(json.loads(err)["type"], "upstream_format")

    def test_revision_uses_latest_publication_without_double_count(self):
        rows = copy.deepcopy(FIXTURE)
        revision = dict(rows[0], rce_pln=1200, publication_ts_utc="2026-11-05 12:00:00")
        code, out, err = invoke(["day", "2026-11-04"], rows + [revision])
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertTrue(data["complete"])
        self.assertEqual(data["interval_count"], 96)
        self.assertEqual(data["intervals"][0]["rce_pln_mwh"], 1200)

    def test_subsecond_publication_order_and_overlapping_intervals(self):
        rows = copy.deepcopy(FIXTURE)
        rows[0]["publication_ts_utc"] = "2026-11-05 12:00:00"
        revision = dict(rows[0], rce_pln=1200, publication_ts_utc="2026-11-05 12:00:00.100")
        code, out, err = invoke(["day", "2026-11-04"], rows + [revision])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["intervals"][0]["rce_pln_mwh"], 1200)
        rows = copy.deepcopy(FIXTURE)
        rows[3]["period_utc"] = "23:00 - 24:00"
        code, out, err = invoke(["day", "2026-11-04"], rows)
        self.assertEqual((code, out), (69, ""))

    def test_hourly_source_intervals_have_time_weighted_mean(self):
        rows = copy.deepcopy(FIXTURE)
        for row in rows:
            row["rce_pln"] = 100
        rows[3]["period_utc"] = "23:00 - 24:00"
        rows[3]["rce_pln"] = 1000
        rows = rows[3:]
        code, out, err = invoke(["day", "2026-11-04"], rows)
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertTrue(data["complete"])
        self.assertAlmostEqual(data["mean_available_pln_mwh"], 137.5)

    def test_cache_expires_and_never_hides_network_failure(self):
        day = dt.date(2026, 11, 4)
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(energia, "fetch_page", return_value={"value": FIXTURE}), patch.object(energia.time, "time", return_value=1000):
                rows, stamp, cached = energia.get_rows(day, day, folder)
                self.assertFalse(cached)
            with patch.object(energia.time, "time", return_value=1299):
                self.assertTrue(energia.get_rows(day, day, folder)[2])
            with patch.object(energia.time, "time", return_value=1300):
                with patch.object(energia, "fetch_page", side_effect=energia.SkillError("offline", "network_error", 69)):
                    with self.assertRaises(energia.SkillError):
                        energia.get_rows(day, day, folder)

    def test_pagination_rejects_external_url_and_collects_valid_pages(self):
        day = dt.date(2026, 11, 4)
        with patch.object(energia, "fetch_page", return_value={"value": FIXTURE, "nextLink": "https://example.com/data"}) as fetch:
            with self.assertRaises(energia.SkillError):
                energia.get_rows(day, day, no_cache=True)
            self.assertEqual(fetch.call_count, 1)
        with patch.object(energia, "fetch_page", side_effect=[
                {"value": FIXTURE[:48], "nextLink": energia.BASE + "?$after=example"}, {"value": FIXTURE[48:]}]):
            self.assertEqual(len(energia.get_rows(day, day, no_cache=True)[0]), 96)


if __name__ == "__main__":
    unittest.main()
