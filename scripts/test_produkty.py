#!/usr/bin/env python3
"""Offline OFF 3.6 / Search-a-licious behavior and strict CLI contracts."""

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
SPEC = importlib.util.spec_from_file_location("produkty", ROOT / "skills/produkty/scripts/produkty.py")
off = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(off)


def fixture(name):
    return json.loads((ROOT / "skills/produkty/resources" / (name + ".json")).read_text(encoding="utf-8"))


def invoke(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = off.main(args)
    return code, out.getvalue(), err.getvalue()


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.block_network = patch.object(off.urllib.request, "urlopen", side_effect=AssertionError("Unexpected network"))
        self.block_network.start()
        self.addCleanup(self.block_network.stop)

    def assert_error(self, args, expected):
        code, out, err = invoke(args)
        self.assertEqual(code, expected, err)
        self.assertEqual(out, "")
        self.assertIn("error", json.loads(err))
        self.assertIn("type", json.loads(err))

    def test_gtin_lengths_and_checksum(self):
        for valid in ("96385074", "034000470693", "5901432003117", "05901432003117"):
            self.assertEqual(off.gtin(valid), valid)
        for invalid in ("", "00000000", "5901432003118", "５９０１４３２００３１１７", "590 1432003117", "9638507", "123456789"):
            with self.subTest(invalid=invalid):
                self.assert_error(["barcode", invalid], 64)

    def test_invalid_cli_inputs_do_not_fetch(self):
        for args in (["search", ""], ["search", "!!!"], ["search", "mleko", "--limit", "0"], ["search", "mleko", "--page", "0"], ["--staging", "search", "mleko"]):
            with self.subTest(args=args):
                self.assert_error(args, 64)

    def test_polish_name_and_missing_allergens_are_explicit(self):
        with patch.object(off.Client, "fetch", return_value=fixture("product-v3.6")):
            code, out, err = invoke(["barcode", "5901432003117"])
        self.assertEqual((code, err), (0, ""))
        p = json.loads(out)["result"]
        self.assertEqual(p["name"]["text"], "Mleko 3.2%")
        self.assertEqual(p["name"]["language"], "pl")
        self.assertEqual(p["allergens"]["status"], "unknown")
        self.assertFalse(p["allergens"]["absence_confirmed"])
        self.assertFalse(p["traces"]["absence_confirmed"])
        self.assertIsNone(p["nutriscore"]["grade"])
        self.assertIn("ingredients", p["missing_fields"])
        self.assertEqual(p["completeness"], 0.5625)

    def test_nutrition_serving_and_100ml_are_never_mixed(self):
        with patch.object(off.Client, "fetch", return_value=fixture("product-v3.6")):
            p = off.product_lookup(off.Client(), "5901432003117")
        portion = p["nutrition"]["input_sets"][0]
        aggregate = p["nutrition"]["aggregated_set"]
        self.assertEqual((portion["per"], portion["per_quantity"], portion["per_unit"]), ("serving", 250, "ml"))
        self.assertEqual(aggregate["per"], "100ml")
        portion_fat = next(r for r in portion["nutrients"] if r["name"] == "fat")
        aggregate_fat = next(r for r in aggregate["nutrients"] if r["name"] == "fat")
        self.assertEqual((portion_fat["value"], portion_fat["unit"]), (8, "g"))
        self.assertEqual((aggregate_fat["value"], aggregate_fat["unit"]), (3.2, "g"))
        energy = next(r for r in portion["nutrients"] if r["name"] == "energy-kj")
        self.assertIsNone(energy["value"])
        self.assertEqual(energy["value_computed"], 627.5)

    def test_explicit_zero_and_missing_nutrient_are_distinct(self):
        result = off.nutrition_set({"per": "100g", "nutrients": {"sugars": {"value": 0, "unit": "g"}, "salt": {"unit": "g"}, "fat": {"value": 2, "unit": "g", "modifier": "<"}}})
        self.assertEqual(result["nutrients"][0]["value"], 0)
        self.assertIsNone(result["nutrients"][1]["value"])
        self.assertEqual(result["nutrients"][2]["modifier"], "<")

    def test_known_allergens_keep_tags_and_provenance(self):
        p = {"allergens_tags": ["en:milk"], "tags_sources": {"allergens": {"ingredients": {"tags": ["en:milk"]}}}}
        result = off.labels(p, "allergens")
        self.assertEqual(result["status"], "reported")
        self.assertEqual(result["tags"], ["en:milk"])
        self.assertIn("ingredients", result["sources"])
        self.assertFalse(result["absence_confirmed"])

    def test_language_fallback_does_not_claim_polish_translation(self):
        result = off.localized({"product_name": "Milk", "lang": "en"}, "product_name")
        self.assertEqual(result["language"], "en")
        self.assertFalse(result["polish_available"])
        result = off.localized({"product_name": {"pl": "Mleko", "en": "Milk"}}, "product_name")
        self.assertTrue(result["polish_available"])
        self.assertEqual(result["field"], "product_name.pl")

    def test_equivalent_upc_ean_barcode_is_allowed(self):
        data = fixture("product-v3.6")
        data["code"] = data["product"]["code"] = "0034000470693"
        with patch.object(off.Client, "fetch", return_value=data):
            result = off.product_lookup(off.Client(), "034000470693")
        self.assertEqual(result["normalized_barcode"], "0034000470693")
        self.assertEqual(result["barcode"], "0034000470693")

    def test_different_product_is_upstream_error(self):
        with patch.object(off.Client, "fetch", return_value=fixture("product-v3.6")):
            self.assert_error(["barcode", "96385074"], 69)

    def test_wrong_response_code_even_with_matching_product_is_rejected(self):
        data = fixture("product-v3.6")
        data["code"] = "96385074"
        with patch.object(off.Client, "fetch", return_value=data):
            self.assert_error(["barcode", "5901432003117"], 69)

    def test_not_found_is_not_empty_success(self):
        with patch.object(off.Client, "fetch", return_value={"result": {"id": "product_not_found"}}):
            self.assert_error(["barcode", "5901432003117"], 2)

    def test_malformed_nutrition_and_nonfinite_values_fail(self):
        for bad in (True, float("nan"), "8"):
            data = fixture("product-v3.6")
            data["product"]["nutrition"]["input_sets"][0]["nutrients"]["fat"]["value"] = bad
            with self.subTest(value=bad), patch.object(off.Client, "fetch", return_value=data):
                self.assert_error(["barcode", "5901432003117"], 69)

    def test_bad_source_timestamp_is_rejected(self):
        data = fixture("product-v3.6")
        data["product"]["last_modified_t"] = True
        with patch.object(off.Client, "fetch", return_value=data):
            self.assert_error(["barcode", "5901432003117"], 69)

    def test_empty_product_metadata_keeps_unknowns(self):
        data = {"status": "success", "product": {"code": "5901432003117"}}
        with patch.object(off.Client, "fetch", return_value=data):
            result = off.product_lookup(off.Client(), "5901432003117")
        self.assertIsNone(result["ingredients"]["text"])
        self.assertEqual(result["nutrition"]["status"], "missing")
        self.assertIsNone(result["completeness"])

    def test_search_uses_poland_filter_without_country_origin_claim(self):
        with patch.object(off.Client, "fetch", return_value=fixture("search")) as fetch:
            result = off.search(off.Client(), "Mleko", limit=2)
        self.assertEqual(fetch.call_args[0][2]["q"], 'countries_tags:"en:poland" mleko')
        self.assertEqual(result["scope"], "poland")
        self.assertEqual(result["products"][0]["brands"], "Mleczna Dolina")
        self.assertTrue(result["has_more"])
        self.assertIn("nie pochodzenie", result["country_meaning"])

    def test_world_scope_is_explicit_and_still_escapes_query_operators(self):
        with patch.object(off.Client, "fetch", return_value=fixture("search")) as fetch:
            result = off.search(off.Client(), 'Mleko OR countries_tags:"en:france"', scope="world", limit=2)
        q = fetch.call_args[0][2]["q"]
        self.assertNotIn(":", q)
        self.assertNotIn(" OR ", q)
        self.assertIsNone(result["country_filter"])

    def test_search_rejects_country_filter_leak(self):
        data = fixture("search")
        data["hits"][0]["countries_tags"] = ["en:france"]
        with patch.object(off.Client, "fetch", return_value=data):
            self.assert_error(["search", "mleko", "--limit", "2"], 69)

    def test_timed_out_and_malformed_search_are_not_not_found(self):
        for change in ({"timed_out": True}, {"hits": {}}, {"page": 7}, {"page_size": False}, {"errors": [{"title": "unavailable"}]}):
            data = fixture("search")
            data.update(change)
            with self.subTest(change=change), patch.object(off.Client, "fetch", return_value=data):
                self.assert_error(["search", "mleko", "--limit", "2"], 69)

    def test_empty_search_returns_not_found_without_widening_scope(self):
        data = fixture("search")
        data.update(hits=[], count=0, page_count=0)
        with patch.object(off.Client, "fetch", return_value=data) as fetch:
            self.assert_error(["search", "mleko", "--limit", "2"], 2)
        self.assertEqual(fetch.call_count, 1)

    def test_contradictory_search_counts_fail_even_for_approximate_total(self):
        for exact in (True, False):
            data = fixture("search")
            data.update(count=0, page_count=0, is_count_exact=exact)
            with self.subTest(exact=exact), patch.object(off.Client, "fetch", return_value=data):
                self.assert_error(["search", "mleko", "--limit", "2"], 69)

    def test_approximate_count_does_not_require_exact_page_formula(self):
        data = fixture("search")
        data.update(count=10000, page_count=100, is_count_exact=False)
        with patch.object(off.Client, "fetch", return_value=data):
            result = off.search(off.Client(), "mleko", limit=2)
        self.assertFalse(result["count_exact"])

    def test_staging_product_link_matches_environment(self):
        with patch.object(off.Client, "fetch", return_value=fixture("product-v3.6")):
            result = off.product_lookup(off.Client(staging=True), "5901432003117")
        self.assertTrue(result["url"].startswith("https://world.openfoodfacts.net/"))

    def test_nutriscore_is_sourced_not_calculated(self):
        data = fixture("product-v3.6")
        data["product"].update(nutriscore_grade="b", nutriscore_score=2)
        with patch.object(off.Client, "fetch", return_value=data):
            result = off.product_lookup(off.Client(), "5901432003117")
        self.assertEqual(result["nutriscore"]["grade"], "b")
        self.assertFalse(result["nutriscore"]["calculated_by_skill"])


class ClientTests(unittest.TestCase):
    def test_cache_preserves_original_timestamp_and_avoids_network(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(off.Client, "pace"), patch.object(off.urllib.request, "urlopen", return_value=io.BytesIO(b'{"id": 1}')) as fetch:
            with patch.object(off.time, "time", return_value=1000):
                off.Client(directory).fetch("https://world.openfoodfacts.org/test", "product")
            with patch.object(off.time, "time", return_value=2000):
                client = off.Client(directory)
                self.assertEqual(client.fetch("https://world.openfoodfacts.org/test", "product"), {"id": 1})
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(client.requests[0]["fetched_at"], off.stamp(1000))
            self.assertTrue(client.requests[0]["cached"])

    def test_expired_cache_does_not_hide_upstream_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(off.Client, "pace"):
            with patch.object(off.time, "time", return_value=1000), patch.object(off.urllib.request, "urlopen", return_value=io.BytesIO(b'{"id": 1}')):
                off.Client(directory).fetch("https://world.openfoodfacts.org/test", "search")
            with patch.object(off.time, "time", return_value=2000), patch.object(off.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
                with self.assertRaises(off.SkillError) as raised:
                    off.Client(directory).fetch("https://world.openfoodfacts.org/test", "search")
            self.assertEqual(raised.exception.code, 69)

    def test_rate_limit_preserves_cooldown_without_retry(self):
        error = urllib.error.HTTPError("x", 429, "Rate limit", {"Retry-After": "120"}, io.BytesIO())
        with tempfile.TemporaryDirectory() as directory, patch.object(off.Client, "pace"), patch.object(off.urllib.request, "urlopen", side_effect=error) as fetch:
            with self.assertRaises(off.SkillError) as raised:
                off.Client(directory).fetch("https://world.openfoodfacts.org/test", "product")
            self.assertEqual(raised.exception.details["retry_after"], "120")
            self.assertIn("blocked_until", json.loads((Path(directory) / "rate.json").read_text()))
            self.assertEqual(fetch.call_count, 1)

    def test_staging_header_and_custom_user_agent(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(off.Client, "pace"), patch.object(off.urllib.request, "urlopen", return_value=io.BytesIO(b'{}')) as fetch:
            off.Client(directory, no_cache=True, staging=True).fetch("https://world.openfoodfacts.net/test", "product")
        req = fetch.call_args[0][0]
        self.assertIn("PolskieSkille/", req.get_header("User-agent"))
        self.assertTrue(req.get_header("Authorization").startswith("Basic "))

    def test_product_404_and_broken_search_endpoint_are_distinct(self):
        for kind, expected in (("product", 2), ("search", 69)):
            error = urllib.error.HTTPError("x", 404, "Not found", {}, io.BytesIO())
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory, patch.object(off.Client, "pace"), patch.object(off.urllib.request, "urlopen", side_effect=error):
                with self.assertRaises(off.SkillError) as raised:
                    off.Client(directory).fetch("https://world.openfoodfacts.org/test", kind)
                self.assertEqual(raised.exception.code, expected)

    def test_pacing_reservations_survive_new_client(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(off.time, "time", return_value=1000), patch.object(off.time, "sleep") as sleep:
            off.Client(directory).pace("product")
            off.Client(directory).pace("product")
            self.assertAlmostEqual(sleep.call_args[0][0], 4.1)
            off.Client(directory).pace("search")
            off.Client(directory).pace("search")
            self.assertAlmostEqual(sleep.call_args[0][0], 6.1)

    def test_upstream_cooldown_prevents_next_request(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(off.time, "time", return_value=1000), patch.object(off.urllib.request, "urlopen", side_effect=AssertionError("Unexpected network")):
            (Path(directory) / "rate.json").write_text(json.dumps({"blocked_until": 1120}))
            with self.assertRaises(off.SkillError) as raised:
                off.Client(directory).fetch("https://world.openfoodfacts.org/test", "product")
            self.assertEqual(raised.exception.kind, "local_rate_limit")
            self.assertEqual(raised.exception.details["retry_after"], 120)


if __name__ == "__main__":
    unittest.main()
