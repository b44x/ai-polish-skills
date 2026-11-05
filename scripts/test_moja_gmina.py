#!/usr/bin/env python3
"""Offline behavior tests with synthetic responses matching the official BDL schema."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("moja_gmina", str(ROOT / "skills/moja-gmina/scripts/moja_gmina.py"))
bdl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bdl)

UNIT_A, UNIT_B = "071413018000", "071413032000"


def invoke(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bdl.main(args)
    return code, out.getvalue(), err.getvalue()


class FixtureClient:
    """Explicitly synthetic units, values and attributes; never live statistics."""
    def __init__(self):
        self.responses = []
        self.units = {
            UNIT_A: {"id": UNIT_A, "name": "Powiat testowy A", "level": 5, "kind": "powiat"},
            UNIT_B: {"id": UNIT_B, "name": "Powiat testowy B", "level": 5, "kind": "powiat"},
        }
        self.variables = {72305: {"id": 72305, "subjectId": "P2137", "n1": "ogółem", "n2": "ogółem",
                                  "measureUnitId": 2, "measureUnitName": "osoba", "years": [2023, 2024, 2025]},
                          900: {"id": 900, "n1": "Wskaźnik syntetyczny", "measureUnitId": 5,
                                "measureUnitName": "%", "years": [2023, 2024, 2025]}}
        self.data = {u: {"unitId": u, "totalRecords": 2, "results": [
            {"id": 72305, "measureUnitId": 2, "lastUpdate": "2026-01-01", "values": [
                {"year": "2023", "val": 100, "attrId": 1},
                {"year": "2024", "val": 101 if u == UNIT_A else 202, "attrId": 1},
                {"year": "2025", "val": 102 if u == UNIT_A else None, "attrId": 1}]},
            {"id": 900, "measureUnitId": 5, "values": [{"year": "2025", "val": 5, "attrId": 1}]}]}
                     for u in (UNIT_A, UNIT_B)}
        self.attributes = {"results": [{"id": 1, "name": "wartość", "symbol": "", "description": ""},
                                       {"id": 7, "name": "tajemnica statystyczna", "symbol": "#"},
                                       {"id": 8, "name": "dane szacunkowe", "symbol": "*"}]}

    def fetch(self, path, params=None, ttl=None):
        if path.startswith("units/"):
            return copy.deepcopy(self.units[path.split("/")[-1]])
        if path.startswith("variables/"):
            return copy.deepcopy(self.variables[int(path.split("/")[-1])])
        if path.startswith("data/by-unit/"):
            data = copy.deepcopy(self.data[path.split("/")[-1]])
            requested = {str(value) for name, value in params if name == "var-id"}
            original_count = len(data["results"])
            # Valid fixture series obey the query; deliberately corrupted IDs remain
            # visible to tests that check validation of unexpected upstream results.
            data["results"] = [row for row in data["results"] if str(row["id"]) in requested or row["id"] not in self.variables]
            if data["totalRecords"] == original_count:
                data["totalRecords"] = len(data["results"])
            return data
        if path == "attributes":
            return copy.deepcopy(self.attributes)
        raise AssertionError("Unexpected endpoint " + path)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.client = FixtureClient()

    def test_latest_year_is_common_to_all_units(self):
        comparison = bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])["comparisons"][0]
        self.assertEqual(comparison["year"], 2024)
        self.assertEqual([r["observation"]["value"] for r in comparison["values"]], [101, 202])

    def test_each_indicator_has_its_own_common_year(self):
        rows = bdl.compare(self.client, [UNIT_A, UNIT_B], [72305, 900])["comparisons"]
        self.assertEqual([r["year"] for r in rows], [2024, 2025])

    def test_explicit_year_keeps_missing_values_and_never_substitutes(self):
        result = bdl.compare(self.client, [UNIT_A, UNIT_B], [72305], 2025)["comparisons"][0]
        self.assertEqual(result["year"], 2025)
        self.assertEqual(result["status"], "no_common_data")
        self.assertEqual(result["values"][0]["observation"]["value"], 102)
        self.assertIsNone(result["values"][1]["observation"]["value"])

    def test_no_common_year_is_not_a_mixed_year_comparison(self):
        self.client.data[UNIT_B]["results"][0]["values"] = [{"year": "2022", "val": 200}]
        result = bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])["comparisons"][0]
        self.assertIsNone(result["year"])
        self.assertEqual(result["status"], "no_common_data")
        self.assertTrue(all(row["observation"] is None for row in result["values"]))

    def test_confidential_numeric_sentinel_is_not_zero(self):
        row = self.client.data[UNIT_B]["results"][0]["values"][1]
        row.update(val=0, attrId=7)
        result = bdl.compare(self.client, [UNIT_A, UNIT_B], [72305], 2024)["comparisons"][0]
        value = result["values"][1]["observation"]
        self.assertIsNone(value["value"])
        self.assertEqual(value["source_value"], 0)
        self.assertEqual(value["attribute"]["symbol"], "#")

    def test_actual_zero_and_estimated_attribute_preserved(self):
        attrs = {str(a["id"]): a for a in self.client.attributes["results"]}
        value = bdl.observation({"year": "2024", "val": 0, "attrId": 8}, attrs)
        self.assertEqual(value["value"], 0)
        self.assertEqual(value["attribute"]["name"], "dane szacunkowe")

    def test_unknown_attribute_cannot_hide_missing_data_as_numeric_zero(self):
        value = bdl.observation({"year": "2024", "val": 0, "attrId": 999}, {})
        self.assertIsNone(value["value"])
        self.assertEqual(value["status"], "attribute_unknown")

    def test_confidential_symbol_without_description_is_missing(self):
        value = bdl.observation({"year": "2024", "val": 0, "attrId": 7}, {"7": {"id": 7, "symbol": "#"}})
        self.assertIsNone(value["value"])

    def test_different_geographic_levels_rejected(self):
        self.client.units[UNIT_B]["level"] = 6
        with self.assertRaises(bdl.SkillError) as error:
            bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])
        self.assertEqual(error.exception.code, 64)

    def test_mismatched_measures_are_not_compared(self):
        self.client.data[UNIT_B]["results"][0]["measureUnitId"] = 5
        with self.assertRaises(bdl.SkillError) as error:
            bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])
        self.assertEqual(error.exception.code, 69)

    def test_missing_series_retains_empty_availability(self):
        self.client.data[UNIT_B]["results"] = []
        self.client.data[UNIT_B]["totalRecords"] = 0
        row = bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])["comparisons"][0]
        self.assertEqual(row["status"], "no_common_data")
        self.assertEqual(row["values"][1]["available_years"], [])

    def test_partial_data_page_stops_comparison(self):
        self.client.data[UNIT_A]["totalRecords"] = 5
        with self.assertRaises(bdl.SkillError) as error:
            bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])
        self.assertEqual(error.exception.kind, "upstream_pagination")

    def test_duplicate_years_fail_instead_of_overwriting(self):
        self.client.data[UNIT_A]["results"][0]["values"].append({"year": "2024", "val": 999})
        with self.assertRaises(bdl.SkillError) as error:
            bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])
        self.assertEqual(error.exception.code, 69)

    def test_invalid_upstream_year_cannot_be_coerced_into_valid_year(self):
        for year in [True, False, 2024.75, 2024.0, "2024.5", "24", "2024x", 1994, 9999, None]:
            with self.subTest(year=year):
                client = FixtureClient()
                client.data[UNIT_A]["results"][0]["values"] = [{"year": year, "val": 123, "attrId": 1}]
                with self.assertRaises(bdl.SkillError) as error:
                    bdl.compare(client, [UNIT_A, UNIT_B], [72305, 900])
                self.assertEqual(error.exception.code, 69)

    def test_unrequested_indicator_is_an_upstream_error(self):
        self.client.data[UNIT_A]["results"][0]["id"] = 123456
        with self.assertRaises(bdl.SkillError) as error:
            bdl.compare(self.client, [UNIT_A, UNIT_B], [72305, 900])
        self.assertEqual(error.exception.code, 69)

    def test_incomplete_attribute_dictionary_stops_comparison(self):
        self.client.attributes["totalRecords"] = 20
        with self.assertRaises(bdl.SkillError) as error:
            bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])
        self.assertEqual(error.exception.code, 69)

    def test_duplicate_attribute_cannot_overwrite_description(self):
        self.client.attributes["results"].append({"id": 1, "name": "tajemnica statystyczna"})
        with self.assertRaises(bdl.SkillError) as error:
            bdl.compare(self.client, [UNIT_A, UNIT_B], [72305])
        self.assertEqual(error.exception.code, 69)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(bdl.urllib.request, "urlopen", side_effect=AssertionError("Unexpected network"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_validation_uses_error_stream_without_network(self):
        cases = [["compare", "--units", "1465000", "--indicators", "ludnosc"],
                 ["compare", "--units", UNIT_A, UNIT_A, "--indicators", "ludnosc"],
                 ["indicators", "", "--page", "-1"], ["indicator", "abc"],
                 ["compare", "--units", UNIT_A, "--indicators", "ludnosc", "--year", "1900"]]
        for args in cases:
            with self.subTest(args=args):
                code, out, err = invoke(args)
                self.assertEqual(code, 64)
                self.assertEqual(out, "")
                self.assertIn("error", json.loads(err))

    def test_search_preserves_ambiguity_and_has_next_page(self):
        payload = {"totalRecords": 3, "results": [{"id": UNIT_A, "name": "Test", "kind": "1"}]}
        with patch.object(bdl.Client, "fetch", return_value=payload) as fetch:
            code, out, err = invoke(["units", "Test", "--level", "6", "--limit", "1"])
        self.assertEqual((code, err), (0, ""))
        result = json.loads(out)["result"]
        self.assertTrue(result["has_more"])
        self.assertEqual(result["results"][0]["kind"], "1")
        self.assertEqual(fetch.call_args[0][0], "units/search")

    def test_empty_search_returns_not_found(self):
        with patch.object(bdl.Client, "fetch", return_value={"totalRecords": 0, "results": []}):
            code, out, err = invoke(["indicators", "nieistniejacy"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(json.loads(err)["type"], "not_found")

    def test_population_alias_resolves_real_id_and_metadata(self):
        metadata = FixtureClient().variables[72305]
        with patch.object(bdl.Client, "fetch", return_value=metadata) as fetch:
            code, out, err = invoke(["indicator", "ludnosc"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(fetch.call_args[0][0], "variables/72305")
        self.assertEqual(json.loads(out)["result"]["measureUnitName"], "osoba")


class ClientTests(unittest.TestCase):
    def test_fresh_cache_prevents_request_and_has_original_timestamp(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(bdl.urllib.request, "urlopen", return_value=io.BytesIO(b'{"id":1}')) as fetch:
            client = bdl.Client(cache_dir=folder)
            with patch.object(bdl.time, "time", return_value=1000):
                self.assertEqual(client.fetch("test"), {"id": 1})
            cached = bdl.Client(cache_dir=folder)
            with patch.object(bdl.time, "time", return_value=1001):
                self.assertEqual(cached.fetch("test"), {"id": 1})
            self.assertEqual(fetch.call_count, 1)
            self.assertTrue(cached.responses[0]["cached"])
            self.assertEqual(cached.responses[0]["fetched_at"], bdl.stamp(1000))

    def test_rate_limit_stops_without_retry_and_preserves_retry_after(self):
        error = urllib.error.HTTPError(bdl.BASE, 429, "Rate limit", {"Retry-After": "120"}, None)
        with tempfile.TemporaryDirectory() as folder, patch.object(bdl.urllib.request, "urlopen", side_effect=error) as fetch:
            with self.assertRaises(bdl.SkillError) as raised:
                bdl.Client(cache_dir=folder).fetch("units")
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(raised.exception.code, 69)
        self.assertEqual(raised.exception.details["retry_after"], "120")

    def test_expired_cache_is_not_returned_when_upstream_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(bdl.time, "time", return_value=1000), patch.object(bdl.urllib.request, "urlopen", return_value=io.BytesIO(b'{"id":1}')):
                bdl.Client(cache_dir=folder).fetch("test", ttl=10)
            with patch.object(bdl.time, "time", return_value=1011), patch.object(bdl.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
                with self.assertRaises(bdl.SkillError) as raised:
                    bdl.Client(cache_dir=folder).fetch("test", ttl=10)
                self.assertEqual(raised.exception.code, 69)

    def test_invalid_json_is_upstream_error(self):
        with patch.object(bdl.urllib.request, "urlopen", return_value=io.BytesIO(b'<html>unavailable</html>')):
            with self.assertRaises(bdl.SkillError) as raised:
                bdl.Client(no_cache=True).fetch("units")
        self.assertEqual(raised.exception.kind, "upstream_format")

    def test_optional_key_goes_to_header_only_not_cache(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(bdl.os.environ, {"BDL_API_KEY": "example-key"}):
            with patch.object(bdl.urllib.request, "urlopen", return_value=io.BytesIO(b'{"id":1}')) as fetch:
                bdl.Client(cache_dir=folder).fetch("units")
            request = fetch.call_args[0][0]
            self.assertEqual(request.get_header("X-clientid"), "example-key")
            self.assertNotIn("example-key", request.full_url)
            self.assertNotIn("example-key", next(Path(folder).iterdir()).read_text())


if __name__ == "__main__":
    unittest.main()
