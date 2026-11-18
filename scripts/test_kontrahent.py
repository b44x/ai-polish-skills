"""Verify contractor reports against synthetic MF and KRS responses."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/kontrahent/scripts/kontrahent.py"
SPEC = importlib.util.spec_from_file_location("kontrahent", SCRIPT)
skill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skill)
NIP = "7342867148"
NUMBER = "0000006865"
DAY = "2026-11-18"
RECEIPT = {"requestId": "fixture", "requestDateTime": "2026-11-18 15:00:00"}


class ContractorTests(unittest.TestCase):
    def test_mismatched_nip_and_negative_bank_check_stay_separate(self):
        vat = {"result": dict(RECEIPT, subject={"nip": NIP, "statusVat": "Czynny", "krs": NUMBER})}
        extract = {"odpis": {
            "naglowekA": {"numerKRS": NUMBER, "dataCzasOdpisu": "18.11.2026 15:00:00"},
            "dane": {"dzial1": {"danePodmiotu": {"identyfikatory": {"nip": "5260250274"}}}},
        }}
        account = "61109010140000071219812874"
        with patch.object(skill, "fetch", side_effect=[vat, extract, {"result": dict(RECEIPT, accountAssigned="NIE")}]) as fetch:
            result = skill.report(NIP, DAY, NUMBER, None, account)
        self.assertTrue(result["comparison"]["vat_krs_number_matches_input"])
        self.assertFalse(result["comparison"]["current_krs_nip_matches_input"])
        self.assertEqual(result["bank"]["accountAssigned"], "NIE")
        self.assertIn("/bank-account/" + account, fetch.call_args.args[0])
        self.assertNotIn(account, str(result))

    def test_missing_account_status_and_krs_outage_are_not_negative_results(self):
        vat = {"result": dict(RECEIPT, subject={"nip": NIP, "statusVat": "Czynny", "krs": NUMBER})}
        with patch.object(skill, "fetch", side_effect=[vat, skill.SourceError("network_error"), {"result": RECEIPT}]) as fetch:
            result = skill.report(NIP, DAY, None, None, "61109010140000071219812874")
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(result["bank"]["status"], "unavailable")
        self.assertEqual(result["krs"]["status"], "unavailable")
        self.assertIsNone(result["comparison"]["current_krs_nip_matches_input"])

    def test_krs_falls_back_only_after_not_found(self):
        with patch.object(skill, "fetch", side_effect=[None, None]) as fetch:
            result = skill.current_extract(NUMBER, None)
        self.assertEqual(result["status"], "not_found")
        self.assertIn("rejestr=P", fetch.call_args_list[0].args[0])
        self.assertIn("rejestr=S", fetch.call_args_list[1].args[0])

    def test_explicit_mf_no_match_is_not_unregistered_status(self):
        with patch.object(skill, "fetch", return_value={"result": dict(RECEIPT, subject=None)}):
            result = skill.report(NIP, DAY, None, None, None)
        self.assertEqual(result["vat"]["status"], "not_found")
        self.assertNotIn("statusVat", result["vat"])
        self.assertEqual(result["krs"]["status"], "no_krs_number")
