#!/usr/bin/env python3
"""Offline RPL contracts. XML records and names below are synthetic."""
import argparse
from contextlib import closing, redirect_stdout, redirect_stderr
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).resolve().parent.parent / 'skills/leki/scripts/leki.py'
SPEC = importlib.util.spec_from_file_location('leki', str(SCRIPT))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
GTIN = '05900000000015'
LEAFLET = 'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/77/leaflet'


def product(pid='10077', name='Lek Testowy', kind='ludzki', strength='10 mg', deleted='NIE', code=GTIN):
    node = ET.Element(M.NS + 'produktLeczniczy', id=pid, nazwaProduktu=name, rodzajPreparatu=kind,
                      moc=strength, nazwaPostaciFarmaceutycznej='Tabletki', ulotka=LEAFLET,
                      nazwaPowszechnieStosowana='Testinum', waznoscPozwolenia='2020-01-01',
                      numerPozwolenia='000123', podmiotOdpowiedzialny='Testowy wydawca')
    ET.SubElement(ET.SubElement(node, M.NS + 'kodyATC'), M.NS + 'kodATC').text = 'A00AA00'
    ET.SubElement(ET.SubElement(node, M.NS + 'drogiPodania'), M.NS + 'drogaPodania', drogaPodaniaNazwa='doustna')
    ET.SubElement(ET.SubElement(node, M.NS + 'substancjeCzynne'), M.NS + 'substancjaCzynna',
                  nazwaSubstancji='Testinum', iloscSubstancji='10', jednostkaMiaryIlosciSubstancji='mg',
                  iloscPreparatu='', jednostkaMiaryIlosciPreparatu='', innyOpisIlosci='')
    packages = ET.SubElement(node, M.NS + 'opakowania')
    package = ET.SubElement(packages, M.NS + 'opakowanie', id='001', kodGTIN=code,
                            skasowane=deleted, kategoriaDostepnosci='Rp')
    ET.SubElement(ET.SubElement(package, M.NS + 'jednostkiOpakowania'), M.NS + 'jednostkaOpakowania',
                  liczbaOpakowan='2', rodzajOpakowania='blister', pojemnosc='10', jednostkaPojemnosci='tabl.')
    return node


def export(nodes=None, as_of='2026-01-01'):
    root = ET.Element(M.NS + 'produktyLecznicze', stanNaDzien=as_of)
    root.extend([product()] if nodes is None else nodes)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def metadata(raw, age=0):
    return dict(source_url=M.SOURCE, sha256=hashlib.sha256(raw).hexdigest(), download_bytes=len(raw),
                retrieved_at=(datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat())


class IndexFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = self.directory / 'registry-v1.sqlite3'

    def build(self, nodes=None, age=0, raw=None, as_of='2026-01-01'):
        raw = export(nodes, as_of) if raw is None else raw
        source = self.directory / 'test.xml'
        source.write_bytes(raw)
        return M.build_index(source, self.db, metadata(raw, age))

    def cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = M.main(['--cache-dir', str(self.directory)] + args)
        if code == 0:
            self.assertEqual(err.getvalue(), '')
            return code, json.loads(out.getvalue())
        self.assertEqual(out.getvalue(), '')
        return code, json.loads(err.getvalue())


class LocalIndex(IndexFixture, unittest.TestCase):
    def test_name_variants_remain_separate_and_human_is_default(self):
        self.build([product(), product('10078', strength='20 mg'), product('10079', kind='weterynaryjny')])
        with patch.object(M, 'download', side_effect=AssertionError('unexpected network')):
            code, result = self.cli(['search', 'lek testowy', '--exact'])
        self.assertEqual(code, 0)
        self.assertEqual(result['result']['total'], 2)
        self.assertEqual({i['strength'] for i in result['result']['items']}, {'10 mg', '20 mg'})
        self.assertFalse(result['result']['therapeutic_equivalence_assessed'])
        code, result = self.cli(['search', 'lek', '--kind', 'veterinary'])
        self.assertEqual(result['result']['items'][0]['id'], '10079')

    def test_substance_search_does_not_search_brand_or_recommend_substitution(self):
        self.build()
        code, result = self.cli(['search', 'Testinum', '--field', 'substance', '--exact'])
        self.assertEqual(code, 0)
        self.assertEqual(result['result']['total'], 1)
        self.assertEqual(self.cli(['search', 'Testinum'])[0], 2)
        self.assertEqual(self.cli(['search', 'Lek', '--field', 'substance'])[0], 2)

    def test_diacritics_case_and_literal_sql_metacharacters(self):
        self.build([product(name='Żółty Lek 10%')])
        self.assertEqual(self.cli(['search', 'ZOLTY'])[0], 0)
        self.assertEqual(self.cli(['search', '10%'])[0], 0)
        self.assertEqual(self.cli(['search', '%_'])[0], 2)
        self.assertEqual(self.cli(['search', "' OR 1=1 --"])[0], 2)

    def test_pagination_is_stable_and_explicit(self):
        self.build([product('2', name='Lek B'), product('1', name='Lek A')])
        _, first = self.cli(['search', 'lek', '--limit', '1'])
        _, second = self.cli(['search', 'lek', '--limit', '1', '--page', '2'])
        self.assertEqual(first['result']['items'][0]['id'], '1')
        self.assertEqual(first['result']['next_page'], 2)
        self.assertFalse(second['result']['has_more'])
        self.assertEqual(second['result']['items'][0]['id'], '2')
        self.assertEqual(self.cli(['search', 'lek', '--page', '3'])[0], 2)

    def test_exact_export_id_and_published_document_url_are_not_interchanged(self):
        self.build()
        _, result = self.cli(['product', '10077'])
        item = result['result']
        self.assertEqual(item['documents']['ulotka'], LEAFLET)
        self.assertIsNone(item['documents']['charakterystyka'])
        self.assertEqual(item['authorization_number'], '000123')
        self.assertEqual(item['authorization_valid_until'], '2020-01-01')
        self.assertIsNone(item['substances'][0]['preparation_amount'])
        self.assertEqual(self.cli(['product', '77'])[0], 2)

    def test_parallel_import_documents_are_kept_separate_and_missing_stays_null(self):
        node = product()
        del node.attrib['ulotka']
        url = 'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/77/parallel-import-files/LEAFLET/public'
        node.set('ulotkaImportRownolegly', url)
        self.build([node])
        _, result = self.cli(['product', '10077'])
        self.assertIsNone(result['result']['documents']['ulotka'])
        self.assertEqual(result['result']['documents']['ulotkaImportRownolegly'], url)

    def test_deleted_and_unknown_packages_are_not_presented_as_current(self):
        a = product(); b = product('10078', deleted='TAK'); c = product('10079', deleted='')
        self.build([a, b, c])
        _, packages = self.cli(['packages', '10077'])
        self.assertFalse(packages['result']['items'][0]['deleted'])
        self.assertEqual(self.cli(['packages', '10078'])[0], 2)
        self.assertEqual(self.cli(['packages', '10079'])[0], 2)
        _, deleted = self.cli(['packages', '10078', '--include-deleted'])
        self.assertTrue(deleted['result']['items'][0]['deleted'])
        _, matches = self.cli(['barcode', GTIN[1:]])
        self.assertEqual(matches['result']['total'], 3)
        self.assertFalse(matches['result']['authenticity_verified'])
        self.assertEqual([i['package']['deleted'] for i in matches['result']['items']], [False, True, None])

    def test_barcode_preserves_package_units_and_leading_zeros(self):
        self.build()
        _, result = self.cli(['barcode', GTIN[1:]])
        match = result['result']['items'][0]
        self.assertEqual(result['result']['gtin14'], GTIN)
        self.assertEqual(match['package']['package_id'], '001')
        self.assertEqual(match['package']['units'][0]['pojemnosc'], '10')
        self.assertEqual(match['package']['units'][0]['liczbaOpakowan'], '2')
        self.assertEqual(match['package']['availability_category'], 'Rp')

    def test_invalid_upstream_gtin_is_disclosed_without_inventing_a_correction(self):
        meta = self.build([product(code=GTIN[:-1] + '0')])
        self.assertEqual(meta['counts']['invalid_gtins'], 1)
        _, result = self.cli(['packages', '10077'])
        self.assertFalse(result['result']['items'][0]['gtin_valid'])
        self.assertIsNone(result['result']['items'][0]['gtin14'])
        self.assertEqual(self.cli(['barcode', GTIN])[0], 2)

    def test_invalid_cli_never_accesses_network_or_creates_cache(self):
        cases = [[], ['bogus'], ['search', 'a'], ['search', '\u0301\u0301'], ['search', 'a\nb'],
                 ['search', 'lek', '--limit', '51'], ['search', 'lek', '--page', '0'],
                 ['product', '../etc'], ['barcode', GTIN[:-1]+'0'], ['barcode', 'x'*13],
                 ['--offline', 'refresh'], ['search', 'lek', '--page', '9'*5000]]
        with patch.object(M, 'download', side_effect=AssertionError('unexpected network')):
            for args in cases:
                with self.subTest(args=str(args)[:80]):
                    code, error = self.cli(args)
                    self.assertEqual(code, 64)
                    self.assertEqual(error['type'], 'validation_error')
        self.assertFalse(self.db.exists())

    def test_offline_and_status_do_not_create_or_download_missing_index(self):
        with patch.object(M, 'download', side_effect=AssertionError('unexpected network')):
            for args in [['--offline', 'search', 'lek'], ['status']]:
                code, error = self.cli(args)
                self.assertEqual((code, error['type']), (69, 'cache_missing'))
        self.assertFalse(self.db.exists())

    def test_stale_cache_requires_explicit_offline_on_network_failure(self):
        self.build(age=M.MAX_CACHE_AGE + 10)
        old = self.db.read_bytes()
        with patch.object(M, 'download', side_effect=M.SkillError('offline', 'network_error', 69)):
            code, error = self.cli(['search', 'lek'])
            self.assertEqual((code, error['type']), (69, 'network_error'))
            code, result = self.cli(['--offline', 'search', 'lek'])
        self.assertEqual(code, 0)
        self.assertTrue(result['snapshot']['cache_expired'])
        self.assertTrue(result['offline_requested'])
        self.assertEqual(self.db.read_bytes(), old)
        self.assertFalse((self.directory/'refresh.lock').exists())

    def test_fresh_download_can_still_have_old_source_date(self):
        self.build(as_of='2020-01-01')
        _, result = self.cli(['status'])
        self.assertFalse(result['snapshot']['cache_expired'])
        self.assertGreater(result['snapshot']['source_age_days'], 365)
        self.assertEqual(result['snapshot']['source_as_of'], '2020-01-01')

    def fake_download(self, raw):
        def run(target):
            target.write_bytes(raw)
            return metadata(raw)
        return run

    def test_first_query_builds_index_once_and_later_queries_do_not_download(self):
        with patch.object(M, 'download', side_effect=self.fake_download(export())) as fetch:
            self.assertEqual(self.cli(['search', 'lek'])[0], 0)
            self.assertEqual(self.cli(['product', '10077'])[0], 0)
            self.assertEqual(fetch.call_count, 1)

    def test_refresh_replaces_complete_index_and_removes_old_products(self):
        self.build()
        raw = export([product('200', name='Nowy Lek')], as_of='2026-01-02')
        with patch.object(M, 'download', side_effect=self.fake_download(raw)):
            self.assertEqual(self.cli(['refresh'])[0], 0)
        self.assertEqual(self.cli(['product', '10077'])[0], 2)
        self.assertEqual(self.cli(['product', '200'])[0], 0)
        self.assertEqual(list(self.directory.glob('refresh-*')), [])

    def test_failed_refresh_keeps_previous_index_and_cleans_temporary_files(self):
        self.build()
        old = self.db.read_bytes()
        for raw in [b'<broken', export([]), export([product(), product()]), export(as_of='2025-01-01')]:
            with self.subTest(raw=raw[:40]), patch.object(M, 'download', side_effect=self.fake_download(raw)):
                code, _ = self.cli(['refresh'])
            self.assertEqual(code, 69)
            self.assertEqual(self.db.read_bytes(), old)
            self.assertFalse((self.directory/'refresh.lock').exists())
            self.assertEqual(list(self.directory.glob('refresh-*')), [])

    def test_refresh_lock_prevents_parallel_download_and_is_not_stolen(self):
        with M.update_lock(self.directory):
            with patch.object(M, 'download', side_effect=AssertionError('unexpected network')):
                code, error = self.cli(['refresh'])
            self.assertEqual((code, error['type']), (69, 'cache_busy'))
            self.assertTrue((self.directory/'refresh.lock').exists())
        self.assertFalse((self.directory/'refresh.lock').exists())

    def test_corrupt_index_can_be_repaired_explicitly(self):
        self.db.write_bytes(b'not sqlite')
        self.assertEqual(self.cli(['status'])[0], 69)
        with patch.object(M, 'download', side_effect=self.fake_download(export())):
            self.assertEqual(self.cli(['refresh'])[0], 0)
        self.assertEqual(self.cli(['product', '10077'])[0], 0)

    def test_cache_metadata_version_and_invalid_dates_fail_closed(self):
        self.build()
        for key, value in [('cache_version', 999), ('retrieved_at', 'bad'), ('source_url', 'https://example.invalid')]:
            with closing(sqlite3.connect(str(self.db))) as db, db:
                raw = json.loads(db.execute('SELECT data FROM metadata').fetchone()[0])
                raw[key] = value
                db.execute('UPDATE metadata SET data=?', (json.dumps(raw),))
            code, error = self.cli(['status'])
            self.assertEqual((code, error['type']), (69, 'cache_error'))

    def test_file_system_errors_keep_stdout_clean(self):
        with patch.object(M, 'ensure_index', side_effect=PermissionError()):
            code, error = self.cli(['search', 'lek'])
        self.assertEqual((code, error['type']), (69, 'cache_error'))


class XMLContracts(IndexFixture, unittest.TestCase):
    def test_unsupported_or_incomplete_xml_fails(self):
        bad_section = product(); bad_section.remove(bad_section.find(M.NS+'substancjeCzynne'))
        bad_kind = product(kind='unknown')
        bad_id = product(); del bad_id.attrib['id']
        duplicate_pack = product(); packs = duplicate_pack.find(M.NS+'opakowania'); packs.append(packs[0])
        bad_link = product(); bad_link.set('ulotka', 'https://127.0.0.1/private')
        cases = [b'<html/>', export().replace(b'v6.0.0', b'v7.0.0'), export(as_of='2026-02-30'),
                 export(as_of='9999-01-01'), export()[:-20], export([bad_kind]), export([bad_id]),
                 export([bad_section]), export([duplicate_pack]), export([bad_link])]
        for raw in cases:
            with self.subTest(raw=raw[:50]):
                if self.db.exists(): self.db.unlink()
                with self.assertRaises(M.SkillError): self.build(raw=raw)

    def test_dtd_entities_and_utf16_fail_before_expansion(self):
        raw = export().split(b'?>', 1)[1]
        for data in [b'<!DOCTYPE x [<!ENTITY x "bad">]>'+raw, raw.decode().encode('utf-16')]:
            with self.subTest(data=data[:50]):
                if self.db.exists(): self.db.unlink()
                with self.assertRaises(M.SkillError): self.build(raw=data)
        reader = M.CheckedXML(io.BytesIO(b'<!DOCTYPE x>'))
        with self.assertRaises(M.SkillError):
            while reader.read(1): pass

    def test_export_and_record_limits(self):
        for name in ['MAX_BYTES', 'MAX_PRODUCTS', 'MAX_PACKAGES', 'MAX_PRODUCT_BYTES']:
            with self.subTest(name=name):
                if self.db.exists(): self.db.unlink()
                with patch.object(M, name, 0), self.assertRaises(M.SkillError):
                    self.build()


class Response(io.BytesIO):
    def __init__(self, data, headers=None, url=M.SOURCE):
        super().__init__(data)
        self.headers = headers or {}
        self.url = url
    def geturl(self):
        return self.url


class NetworkContracts(unittest.TestCase):
    def test_timeout_network_and_http_errors_have_structured_types(self):
        for exception in [TimeoutError(), ConnectionResetError(), urllib.error.URLError('offline')]:
            with patch.object(M.OPENER, 'open', side_effect=exception), tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(M.SkillError) as caught:
                    M.download(Path(temp)/'export.xml')
                self.assertEqual((caught.exception.code, caught.exception.kind), (69, 'network_error'))
        for status in [404, 429, 503]:
            exception = urllib.error.HTTPError(M.SOURCE, status, 'test', {'Retry-After':'30'}, io.BytesIO())
            with patch.object(M.OPENER, 'open', side_effect=exception) as op, tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(M.SkillError) as caught:
                    M.download(Path(temp)/'export.xml')
                self.assertEqual(caught.exception.details['retry_after'], '30')
                self.assertEqual(caught.exception.code, 69)
                self.assertEqual(op.call_count, 1)

    def test_network_read_failure_does_not_become_a_success_or_cache_error(self):
        response = Response(b'')
        with patch.object(response, 'read', side_effect=ConnectionResetError()), patch.object(M.OPENER, 'open', return_value=response), tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(M.SkillError) as caught:
                M.download(Path(temp)/'export.xml')
        self.assertEqual(caught.exception.kind, 'network_error')

    def test_streaming_size_length_encoding_and_time_limits(self):
        cases = [(Response(b'1234'), 'MAX_BYTES', 3, 'response_too_large'),
                 (Response(b'12', {'Content-Length':'4'}), 'MAX_BYTES', 4, 'upstream_format'),
                 (Response(b'12', {'Content-Length':'100'}), 'MAX_BYTES', 4, 'response_too_large'),
                 (Response(b'12', {'Content-Encoding':'gzip'}), 'MAX_BYTES', 4, 'upstream_format'),
                 (Response(b'12'), 'MAX_SECONDS', -1, 'network_timeout')]
        for response, setting, limit, kind in cases:
            with self.subTest(kind=kind), patch.object(M, setting, limit), patch.object(M.OPENER, 'open', return_value=response), tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(M.SkillError) as caught:
                    M.download(Path(temp)/'export.xml')
                self.assertEqual(caught.exception.kind, kind)

    def test_success_preserves_digest_and_uses_timeout_without_query_data(self):
        with patch.object(M.OPENER, 'open', return_value=Response(b'abc', {'Content-Length':'3'})) as op, tempfile.TemporaryDirectory() as temp:
            result = M.download(Path(temp)/'export.xml')
        self.assertEqual(result['sha256'], hashlib.sha256(b'abc').hexdigest())
        self.assertEqual(op.call_args.kwargs['timeout'], 30)
        self.assertEqual(op.call_args.args[0].full_url, M.SOURCE)

    def test_redirects_and_document_urls_cannot_escape_official_source(self):
        for url in ['https://localhost/x', 'https://rejestry.ezdrowie.gov.pl.evil.invalid/api/rpl/medicinal-products/1',
                    'http://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/1',
                    'https://user@rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/1',
                    'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/%2e%2e/private']:
            with self.subTest(url=url), self.assertRaises(M.SkillError):
                M.Redirect().redirect_request(None, None, 302, '', {}, url)

    def test_help_and_invalid_usage_as_real_subprocess(self):
        for args, expected in [(['--help'], 0), (['search','--help'], 0), (['invalid-command'], 64), (['barcode','123'], 64)]:
            result = subprocess.run([sys.executable, str(SCRIPT)] + args, text=True, capture_output=True)
            self.assertEqual(result.returncode, expected)
            if expected:
                self.assertEqual(result.stdout, '')
                self.assertIn('error', json.loads(result.stderr))
            else:
                self.assertEqual(result.stderr, '')
                self.assertIn('usage:', result.stdout)


if __name__ == '__main__':
    unittest.main()
