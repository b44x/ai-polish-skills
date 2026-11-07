#!/usr/bin/env python3
"""Offline regressions for ULDK parcel identity, response states and geometry."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dzialki", ROOT / "skills/dzialki/scripts/dzialki.py")
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)
FIXTURES = ROOT / "skills/dzialki/resources"
ID = "022602_1.0003.59"
WGS = (FIXTURES / "parcel-wgs84.txt").read_text(encoding="utf-8")
NATIVE = (FIXTURES / "parcel-2180.txt").read_text(encoding="utf-8")
SEARCH = (FIXTURES / "search.txt").read_text(encoding="utf-8")


def call(argv, response=WGS):
    out, err = io.StringIO(), io.StringIO()
    with patch.object(D, "fetch", return_value=response), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = D.main(argv + ["--no-cache"])
    return code, out.getvalue(), err.getvalue()


class ResponseTests(unittest.TestCase):
    def test_real_parcel_identity_and_admin_fields(self):
        row = D.parse_response(WGS, "GetParcelById", 4326, ID)[0]
        self.assertEqual(row["id"], ID)
        self.assertEqual(row["parcel_number"], "59")
        self.assertEqual(row["commune"], "Złotoryja (miasto)")
        self.assertEqual(row["data_source"], "powiat złotoryjski (wfs)")

    def test_real_search_count_and_district(self):
        rows = D.parse_response(SEARCH, "GetParcelByIdOrNr", 4326)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "022503_5.0003.134")
        self.assertEqual(rows[0]["district"], "Krzewina")

    def test_ambiguous_search_retains_count_when_display_limited(self):
        line = SEARCH.strip().splitlines()[1]
        another = line.replace("022503_5.0003.134", "022503_5.0004.134")
        code, out, err = call(["search", "Krzewina", "134", "--limit", "1"], "2\n" + line + "\n" + another + "\n")
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data["total_matches"], 2)
        self.assertTrue(data["ambiguous"])
        self.assertTrue(data["display_limit_reached"])
        self.assertEqual(len(data["records"]), 1)

    def test_plain_no_results_classified_as_not_found(self):
        for text, method in [("-1 brak wyników\n", "GetParcelById"),
                             ("-1\nbrak wyników\n", "GetParcelByXY"), ("0\n", "GetParcelByIdOrNr")]:
            with self.subTest(text=text), self.assertRaises(D.SkillError) as exc:
                D.parse_response(text, method, 4326)
            self.assertEqual(exc.exception.code, 2)

    def test_no_results_with_technical_diagnostic_is_upstream_failure(self):
        text = "-1 brak wyników\nbłędny format odpowiedzi XML, usługa zwróciła odpowiedź Zbiorcza baza danych obsłużyła zapytanie."
        with self.assertRaises(D.SkillError) as exc:
            D.parse_response(text, "GetParcelById", 4326)
        self.assertEqual((exc.exception.code, exc.exception.kind), (69, "upstream_error"))

    def test_inconsistent_status_count_or_schema_rejected(self):
        line = SEARCH.strip().splitlines()[1]
        for text, method in [("2\n" + line, "GetParcelByIdOrNr"), ("0\n", "GetParcelById"),
                             ("0\nnot a record", "GetParcelById"), ("<html>error</html>", "GetParcelById"),
                             ("9" * 5000, "GetParcelById")]:
            with self.subTest(text=text[:30]), self.assertRaises(D.SkillError) as exc:
                D.parse_response(text, method, 4326)
            self.assertEqual(exc.exception.code, 69)

    def test_unexpected_id_and_duplicates_rejected(self):
        with self.assertRaises(D.SkillError):
            D.parse_response(WGS, "GetParcelById", 4326, "022602_1.0003.60")
        line = WGS.strip().splitlines()[1]
        with self.assertRaises(D.SkillError):
            D.parse_response("2\n" + line + "\n" + line, "GetParcelByIdOrNr", 4326)

    def test_point_query_is_lon_lat_and_containment(self):
        parsed = D.build_parser().parse_args(["point", "--lat", "51.12315", "--lon", "15.915", "--no-cache"])
        with patch.object(D, "fetch", return_value=WGS) as fetch:
            result = D.run(parsed)
        query = D.urllib.parse.parse_qs(D.urllib.parse.urlsplit(fetch.call_args[0][0]).query)
        self.assertEqual(query["request"], ["GetParcelByXY"])
        self.assertEqual(query["xy"], ["15.91500000,51.12315000,4326"])
        self.assertNotIn("radius", query)
        self.assertEqual(result["lookup_semantics"], "parcel_containing_point")


class GeometryTests(unittest.TestCase):
    def test_real_wgs84_geometry_valid_bounds_and_axes(self):
        geo = D.parse_response(WGS, "GetParcelById", 4326)[0]["geometry"]
        self.assertEqual(geo["crs"], "EPSG:4326")
        self.assertEqual(geo["axis_order"], ["longitude", "latitude"])
        self.assertEqual(geo["geojson"]["type"], "Polygon")
        self.assertEqual(geo["vertex_count"], 21)
        self.assertAlmostEqual(geo["bbox"][0], 15.9145177937739)
        self.assertAlmostEqual(geo["bbox"][3], 51.1234011877454)

    def test_native_geometry_has_metres_and_no_nonstandard_geojson(self):
        geo = D.parse_response(NATIVE, "GetParcelById", 2180)[0]["geometry"]
        self.assertEqual(geo["units"], "metres")
        self.assertEqual(geo["axis_order"], ["easting", "northing"])
        self.assertIsNone(geo["geojson"])
        self.assertAlmostEqual(geo["bbox"][0], 284153.367270689)

    def test_polygon_holes_and_multipolygon(self):
        ring = "15 51,15.1 51,15.1 51.1,15 51"
        hole = "15.01 51.01,15.02 51.01,15.02 51.02,15.01 51.01"
        polygon = D.geometry("POLYGON ((%s),(%s))" % (ring, hole), 4326)
        self.assertEqual(len(polygon["geojson"]["coordinates"]), 2)
        multi = D.geometry("MULTIPOLYGON (((%s)),((%s)))" % (ring, ring), 4326)
        self.assertEqual(multi["geojson"]["type"], "MultiPolygon")
        self.assertEqual(len(multi["geojson"]["coordinates"]), 2)

    def test_malformed_unclosed_nonfinite_and_mislabeled_geometry(self):
        for text in ["POINT(15 51)", "POLYGON EMPTY", "POLYGON((15 51,15.1 51,15.1 51.1))",
                     "POLYGON((15 51,15.1 51,NaN 51.1,15 51))", "POLYGON((15 51,15.1 51,1e999 51.1,15 51))",
                     "SRID=2180;POLYGON((15 51,15.1 51,15.1 51.1,15 51))",
                     "POLYGON((284207 366372,284208 366372,284208 366373,284207 366372))",
                     "POLYGON((15 51,15.1 51,15.1 51.1,15 51)))", "POLYGON((15-51,15.1 51,15.1 51.1,15-51))"]:
            with self.subTest(text=text), self.assertRaises(D.SkillError) as exc:
                D.geometry(text, 4326)
            self.assertEqual(exc.exception.code, 69)

    def test_degrees_cannot_be_mislabeled_as_native_metres(self):
        with self.assertRaises(D.SkillError) as exc:
            D.geometry("POLYGON((15 51,15.1 51,15.1 51.1,15 51))", 2180)
        self.assertEqual(exc.exception.code, 69)

    def test_geometry_vertex_bound(self):
        with patch.object(D, "MAX_COORDINATES", 3), self.assertRaises(D.SkillError):
            D.geometry("POLYGON((15 51,15.1 51,15.1 51.1,15 51))", 4326)


class CacheAndContractTests(unittest.TestCase):
    def test_cache_fresh_then_expired_no_stale_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(D, "fetch", return_value=WGS) as fetch, patch.object(D.time, "time", return_value=1000):
                self.assertFalse(D.load("https://example.test/id", "GetParcelById", 4326, ID, folder)[2])
                self.assertEqual(fetch.call_count, 1)
            with patch.object(D.time, "time", return_value=1299), patch.object(D, "fetch", side_effect=AssertionError("No fetch")):
                self.assertTrue(D.load("https://example.test/id", "GetParcelById", 4326, ID, folder)[2])
            with patch.object(D.time, "time", return_value=1300), patch.object(D, "fetch", side_effect=D.SkillError("offline", "network_error", 69)):
                with self.assertRaises(D.SkillError):
                    D.load("https://example.test/id", "GetParcelById", 4326, ID, folder)

    def test_corrupt_numeric_cache_stamp_refreshes_instead_of_crashing(self):
        url = "https://example.test/id"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ("uldk-" + D.hashlib.sha256(url.encode()).hexdigest() + ".json")
            path.write_text(json.dumps({"url": url, "fetched_at": 10 ** 1000, "response": WGS}))
            with patch.object(D, "fetch", return_value=WGS) as fetch:
                self.assertFalse(D.load(url, "GetParcelById", 4326, ID, folder)[2])
                self.assertEqual(fetch.call_count, 1)

    def test_no_cache_never_writes(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(D, "fetch", return_value=WGS):
            D.load("https://example.test/id", "GetParcelById", 4326, ID, folder, no_cache=True)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_invalid_upstream_response_never_cached(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(D, "fetch", return_value="-1 source failure"):
            with self.assertRaises(D.SkillError):
                D.load("https://example.test/id", "GetParcelById", 4326, ID, folder)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_cache_prunes_only_own_namespace(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            for i in range(130):
                (path / ("uldk-%064x.json" % i)).write_text("{}")
            other = path / "unrelated.json"
            other.write_text("{}")
            D.prune_cache(path)
            self.assertEqual(len(list(path.glob("uldk-*.json"))), 128)
            self.assertTrue(other.exists())

    def test_success_strict_json_and_attribution(self):
        code, out, err = call(["id", ID])
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertIn("GUGiK", data["attribution"])
        self.assertEqual(data["total_matches"], 1)
        self.assertFalse(data["ambiguous"])

    def test_validation_before_network(self):
        cases = [[], ["id", "bad"], ["id", ID, "--limit", "0"],
                 ["point", "--lat", "nan", "--lon", "15"],
                 ["point", "--lat", "91", "--lon", "15"],
                 ["point", "--lat", "51"], ["search", "Krzewina", "bad"],
                 ["search", "bad|district", "134"], ["id", ID, "--crs", "9999"]]
        for args in cases:
            out, err = io.StringIO(), io.StringIO()
            with patch.object(D, "fetch", side_effect=AssertionError("Network called")), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = D.main(args)
            self.assertEqual((code, out.getvalue()), (64, ""), args)
            self.assertIn("error", json.loads(err.getvalue()))

    def test_help_zero(self):
        for args in [["--help"], ["id", "--help"], ["point", "--help"]]:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exc:
                D.main(args)
            self.assertEqual(exc.exception.code, 0)

    def test_upstream_errors_have_structured_stderr(self):
        for response, expected in [("-1 brak wyników", 2), ("-1 brak wyników\nbłędny format odpowiedzi XML", 69)]:
            code, out, err = call(["id", ID], response)
            self.assertEqual((code, out), (expected, ""))
            self.assertIn("error", json.loads(err))

    def test_http_and_network_errors(self):
        errors = [urllib.error.URLError("offline"), urllib.error.HTTPError(D.BASE, 429, "limit", None, None)]
        for error in errors:
            with patch.object(D.urllib.request, "urlopen", side_effect=error), self.assertRaises(D.SkillError) as exc:
                D.fetch(D.BASE)
            self.assertEqual(exc.exception.code, 69)
            if isinstance(error, urllib.error.HTTPError):
                error.close()


if __name__ == "__main__":
    unittest.main()
