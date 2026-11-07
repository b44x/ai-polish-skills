#!/usr/bin/env python3
"""Offline regressions for RCN geography, price scope and transaction samples."""

import contextlib
import datetime as dt
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nieruchomosci", ROOT / "skills/nieruchomosci/scripts/nieruchomosci.py")
RCN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RCN)


def raw_row(**changes):
    row = {"_feature_id": "lokale.1", "LOK_ID_LOKALU": "example-local-1",
           "TRAN_LOKALNY_ID_IIP": "example-transaction-1", "TRAN_PRZESTRZEN_NAZW": "example-county",
           "TRAN_CENA_BRUTTO": "500000", "NIER_CENA_BRUTTO": "500000",
           "LOK_CENA_BRUTTO": "500000", "LOK_POW_UZYT": "50", "NIER_UDZIAL": "1/1",
           "LOK_FUNKCJA": "mieszkalna", "TRAN_RODZAJ_TRANS": "wolnyRynek",
           "TRAN_RODZAJ_RYNKU": "rynekWtorny", "NIER_RODZAJ": "nieruchomoscLokalowa",
           "NIER_PRAWO": "wlasnoscLokaluWrazZPrawemZwiazanym", "DOK_DATA": "2026-06-01",
           "DOK_OZNACZENIE": "example-deed-1", "DOK_TWORCA": "EXAMPLE NOTARY"}
    row.update(changes)
    return row


def args(*extra):
    return RCN.build_parser().parse_args(["search", "--lat", "52.2297", "--lon", "21.0122", "--from", "2025-01-01", "--to", "2026-12-31"] + list(extra))


class Geography(unittest.TestCase):
    def test_projection_central_meridian(self):
        north, east = RCN.project(52, 19)
        self.assertAlmostEqual(east, 500000, places=6)
        self.assertAlmostEqual(north, 459309.209, delta=.1)

    def test_projection_warsaw_reference(self):
        north, east = RCN.project(52.2297, 21.0122)
        self.assertAlmostEqual(north, 486757.21, delta=.5)
        self.assertAlmostEqual(east, 637382.204, delta=.5)

    def test_query_uses_native_axis_order(self):
        captured = []
        def fetch(params):
            captured.append(params)
            return [raw_row()], "2026-11-05"
        RCN.search(args(), fetch)
        north, east, _, _, crs = captured[0]["bbox"].split(",")
        self.assertLess(float(north), float(east))
        self.assertEqual(crs, "EPSG:2180")
        self.assertNotIn("srsName", captured[0])

    def test_bbox_includes_curved_edges_and_accepts_exact_size_limit(self):
        parser = RCN.build_parser()
        for west, east in [(18.905, 19.095), (18.9, 19.1)]:
            box, _ = RCN.search_bounds(parser.parse_args(["search", "--bbox", str(west), "52", str(east), "52.1"]))
            for step in range(101):
                north, easting = RCN.project(52, west + (east - west) * step / 100)
                self.assertLessEqual(box[0], north)
                self.assertGreaterEqual(box[2], north)
                self.assertLessEqual(box[1], easting)
                self.assertGreaterEqual(box[3], easting)

    def test_square_radius(self):
        box, location = RCN.search_bounds(args("--radius-km", "2"))
        self.assertAlmostEqual(box[2] - box[0], 4000)
        self.assertAlmostEqual(box[3] - box[1], 4000)
        self.assertEqual(location["shape"], "square")

    def test_invalid_coordinates_and_limits(self):
        for extra in [("--lat", "90"), ("--lon", "0"), ("--radius-km", "0"),
                      ("--scan-limit", "1001"), ("--limit", "0"),
                      ("--min-area", "80", "--max-area", "40"),
                      ("--from", "2026-12-01", "--to", "2026-01-01")]:
            with self.subTest(extra=extra), self.assertRaises(RCN.SkillError):
                RCN.search(args(*extra), lambda _: self.fail("Network should not be called"))

    def test_bbox_constraints(self):
        parser = RCN.build_parser()
        valid = parser.parse_args(["search", "--bbox", "20.99", "52.22", "21.03", "52.24"])
        box, location = RCN.search_bounds(valid)
        self.assertGreater(box[2], box[0])
        self.assertEqual(location["shape"], "bounding_box")
        for values in [["21", "52", "20", "53"], ["14", "49", "24", "54"]]:
            with self.assertRaises(RCN.SkillError):
                RCN.search_bounds(parser.parse_args(["search", "--bbox"] + values))


class Prices(unittest.TestCase):
    def test_object_price_not_transaction_or_property_total(self):
        result = RCN.normalize(raw_row(TRAN_CENA_BRUTTO="600000", NIER_CENA_BRUTTO="550000"), "lokale")
        self.assertEqual(result["object_price_per_m2_pln"], 10000)
        self.assertEqual(result["transaction_price_pln"], 600000)
        self.assertEqual(result["property_price_pln"], 550000)

    def test_garage_share_has_no_rate(self):
        r = RCN.normalize(raw_row(NIER_UDZIAL="1/39", LOK_FUNKCJA="garaz", LOK_POW_UZYT="1080.3", LOK_CENA_BRUTTO="41000"), "lokale")
        self.assertIsNone(r["object_price_per_m2_pln"])
        self.assertEqual(RCN.summarize([r], "lokale")["comparable_transactions"], 0)

    def test_missing_price_share_or_area_has_no_rate(self):
        for changes in [{"LOK_CENA_BRUTTO": None}, {"NIER_UDZIAL": None},
                        {"LOK_POW_UZYT": "0"}, {"LOK_POW_UZYT": "NaN"}, {"LOK_CENA_BRUTTO": "inf"}]:
            with self.subTest(changes=changes):
                self.assertIsNone(RCN.normalize(raw_row(**changes), "lokale")["object_price_per_m2_pln"])

    def test_overflowing_unit_price_and_invalid_deed_date_are_upstream_errors(self):
        for changes in [{"LOK_CENA_BRUTTO": "1e308", "LOK_POW_UZYT": "1e-308"},
                        {"DOK_DATA": "2026-99-99"}]:
            with self.assertRaises(RCN.SkillError) as exc:
                RCN.normalize(raw_row(**changes), "lokale")
            self.assertEqual(exc.exception.code, 69)
        self.assertEqual(RCN.safe_median([1e308, 1e308]), 1e308)

    def test_full_shares(self):
        for value in ["1/1", "100/100", "1", "1,0"]:
            self.assertTrue(RCN.full_share(value))
        for value in [None, "", "1/2", "0/0", "brak"]:
            self.assertFalse(RCN.full_share(value))

    def test_multiple_units_same_transaction_do_not_enter_summary(self):
        rows = [RCN.normalize(raw_row(), "lokale"),
                RCN.normalize(raw_row(LOK_ID_LOKALU="another", _feature_id="lokale.2"), "lokale")]
        self.assertEqual(RCN.summarize(rows, "lokale")["comparable_transactions"], 0)

    def test_count_once_identical_transaction(self):
        row = RCN.normalize(raw_row(), "lokale")
        self.assertEqual(RCN.summarize([row, row], "lokale")["comparable_transactions"], 1)

    def test_distinct_transaction_ids_same_bulk_deed_excluded(self):
        rows = [RCN.normalize(raw_row(), "lokale"),
                RCN.normalize(raw_row(_feature_id="lokale.2", TRAN_LOKALNY_ID_IIP="different-transaction",
                                      LOK_ID_LOKALU="another-local"), "lokale")]
        self.assertEqual(RCN.summarize(rows, "lokale")["comparable_transactions"], 0)

    def test_bulk_total_excludes_lone_component_even_when_peers_outside_sample(self):
        row = RCN.normalize(raw_row(TRAN_CENA_BRUTTO="45000000"), "lokale")
        self.assertEqual(row["object_price_per_m2_pln"], 10000)
        self.assertEqual(RCN.summarize([row], "lokale")["comparable_transactions"], 0)

    def test_same_deed_same_object_has_one_statistical_observation(self):
        rows = [RCN.normalize(raw_row(), "lokale"),
                RCN.normalize(raw_row(_feature_id="lokale.2", TRAN_LOKALNY_ID_IIP="another-id"), "lokale")]
        self.assertEqual(RCN.summarize(rows, "lokale")["comparable_transactions"], 1)

    def test_separate_markets_and_years(self):
        rows = [RCN.normalize(raw_row(), "lokale"),
                RCN.normalize(raw_row(TRAN_LOKALNY_ID_IIP="two", DOK_DATA="2025-06-01"), "lokale"),
                RCN.normalize(raw_row(TRAN_LOKALNY_ID_IIP="three", DOK_OZNACZENIE="deed-three", TRAN_RODZAJ_RYNKU="rynekPierwotny"), "lokale")]
        result = RCN.summarize(rows, "lokale")
        self.assertEqual(len(result["groups"]), 3)
        self.assertEqual(result["comparable_transactions"], 3)
        self.assertFalse(result["is_valuation"])

    def test_only_full_residential_free_market_units(self):
        for changes in [{"LOK_FUNKCJA": "garaz"}, {"TRAN_RODZAJ_TRANS": "przetarg"},
                        {"NIER_PRAWO": None}, {"LOK_ID_LOKALU": None}, {"NIER_UDZIAL": "1/2"}]:
            self.assertEqual(RCN.summarize([RCN.normalize(raw_row(**changes), "lokale")], "lokale")["comparable_transactions"], 0)
        self.assertEqual(RCN.summarize([RCN.normalize(raw_row(), "lokale")], "budynki")["comparable_transactions"], 0)


class SearchAndContract(unittest.TestCase):
    def test_parse_nested_date_and_empty_fields(self):
        raw = b'''<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:ms="urn:example" numberReturned="1"><wfs:member><ms:lokale gml:id="lokale.1"><ms:DOK_DATA><gml:timePosition>2026-01-01</gml:timePosition></ms:DOK_DATA><ms:NIER_UDZIAL/></ms:lokale></wfs:member></wfs:FeatureCollection>'''
        rows, _ = RCN.parse_page(raw)
        self.assertEqual(rows[0]["DOK_DATA"], "2026-01-01")
        self.assertIsNone(rows[0]["NIER_UDZIAL"])

    def test_error_xml_and_inconsistent_count(self):
        for raw in [b"not xml", b"<ExceptionReport/>", b'<FeatureCollection numberReturned="1"/>']:
            with self.assertRaises(RCN.SkillError) as exc:
                RCN.parse_page(raw)
            self.assertEqual(exc.exception.code, 69)

    def test_pagination_and_display_limit(self):
        calls = []
        def fetch(params):
            calls.append(params)
            if len(calls) == 1:
                return [raw_row(_feature_id="lokale.%s" % i, TRAN_LOKALNY_ID_IIP=str(i), DOK_OZNACZENIE=str(i)) for i in range(100)], "date"
            return [raw_row(_feature_id="lokale.100", TRAN_LOKALNY_ID_IIP="100", DOK_OZNACZENIE="100")], "date"
        result = RCN.search(args("--limit", "2"), fetch)
        self.assertEqual([p["startIndex"] for p in calls], [0, 100])
        self.assertEqual(result["scanned_records"], 101)
        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(result["summary"]["comparable_transactions"], 101)
        self.assertFalse(result["scan_limit_reached"])
        self.assertFalse(result["has_more"])

    def test_exact_scan_boundary_unknown_more(self):
        result = RCN.search(args("--scan-limit", "1"), lambda _: ([raw_row()], "date"))
        self.assertTrue(result["scan_limit_reached"])
        self.assertIsNone(result["has_more"])

    def test_filtered_component_does_not_hide_multi_object_transaction(self):
        rows = [raw_row(), raw_row(_feature_id="lokale.2", LOK_ID_LOKALU="garage", LOK_FUNKCJA="garaz")]
        result = RCN.search(args("--function", "mieszkalna"), lambda _: (rows, "date"))
        self.assertEqual(result["matched_in_sample"], 1)
        self.assertEqual(result["summary"]["comparable_transactions"], 0)

    def test_filtered_component_does_not_hide_bulk_deed_across_transaction_ids(self):
        rows = [raw_row(), raw_row(_feature_id="lokale.2", TRAN_LOKALNY_ID_IIP="another-transaction",
                                   LOK_ID_LOKALU="garage", LOK_FUNKCJA="garaz")]
        result = RCN.search(args("--function", "mieszkalna"), lambda _: (rows, "date"))
        self.assertEqual(result["matched_in_sample"], 1)
        self.assertEqual(result["summary"]["comparable_transactions"], 0)
        self.assertEqual(result["records"][0]["deed_number"], "example-deed-1")

    def test_duplicate_page_aborts(self):
        def fetch(params):
            return [raw_row(_feature_id="lokale.%s" % i) for i in range(params["count"])], "date"
        with self.assertRaises(RCN.SkillError) as exc:
            RCN.search(args("--scan-limit", "101"), fetch)
        self.assertEqual(exc.exception.code, 69)

    def test_empty_is_code_two(self):
        with self.assertRaises(RCN.SkillError) as exc:
            RCN.search(args(), lambda _: ([], "date"))
        self.assertEqual(exc.exception.code, 2)

    def test_filters_date_market_area(self):
        result = RCN.search(args("--market", "wtorny", "--min-area", "40", "--max-area", "60"), lambda _: ([raw_row()], "date"))
        self.assertEqual(result["matched_in_sample"], 1)
        with self.assertRaises(RCN.SkillError) as exc:
            RCN.search(args("--market", "pierwotny"), lambda _: ([raw_row()], "date"))
        self.assertEqual(exc.exception.code, 2)

    def test_validation_errors_only_stderr(self):
        for argv in [[], ["unknown"], ["search"], ["search", "--lat", "nan"]]:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = RCN.main(argv)
            self.assertEqual(code, 64)
            self.assertEqual(out.getvalue(), "")
            self.assertIn("error", json.loads(err.getvalue()))

    def test_help_zero(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exc:
            RCN.main(["--help"])
        self.assertEqual(exc.exception.code, 0)

    def test_network_http_and_invalid_xml_errors(self):
        import urllib.error
        for error in [urllib.error.URLError("offline"), urllib.error.HTTPError(RCN.BASE, 429, "limit", {}, io.BytesIO())]:
            with mock.patch.object(RCN.urllib.request, "urlopen", side_effect=error), self.assertRaises(RCN.SkillError) as exc:
                RCN.fetch_page({})
            self.assertEqual(exc.exception.code, 69)
            if isinstance(error, urllib.error.HTTPError):
                error.close()


if __name__ == "__main__":
    unittest.main()
