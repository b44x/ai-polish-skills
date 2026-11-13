"""Offline pharmacy export contracts; all records are synthetic."""
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

SPEC = importlib.util.spec_from_file_location('apteki', Path(__file__).resolve().parents[1]/'skills/apteki/scripts/apteki.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def record(id='001', **kwargs):
    row = dict.fromkeys(M.REQUIRED, '')
    row.update(identyfikator_apteki=id, stan_apteki='AKTYWNA', rodzaj_apteki='APTEKA OGÓLNODOSTĘPNA',
               miejscowosc='Łódź', wojewodztwo='ŁÓDZKIE', nazwa_ulicy='Długa', nazwa_apteki='Testowa',
               numer_budynku='12', telefon='000-test', godziny_otwarcia_poniedzialek='08:00 - 16:00')
    row.update(kwargs)
    return row


def export(rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), delimiter='|')
    writer.writeheader();writer.writerows(rows)
    return out.getvalue().encode('utf-8-sig')


class LookupTests(unittest.TestCase):
    def run_cli(self, args, rows=None):
        raw = export(rows or [record()])
        out, err = io.StringIO(), io.StringIO()
        with patch.object(M, 'load', return_value=(raw, {'source_as_of': None})), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = M.main(args)
        self.assertEqual(err.getvalue() if code == 0 else out.getvalue(), '')
        return code, json.loads(out.getvalue() if code == 0 else err.getvalue())

    def test_default_filters_exclude_inactive_and_hospital(self):
        rows = [record(), record('2', stan_apteki='NIEAKTYWNA'), record('3', rodzaj_apteki='APTEKA SZPITALNA'),
                record('4', stan_apteki='NOWY STATUS')]
        code, data = self.run_cli(['search','--city','Lodz'], rows)
        self.assertEqual(code, 0)
        self.assertEqual([r['id'] for r in data['result']['items']], ['001'])
        _, data = self.run_cli(['search','--city','Lodz','--kind','all','--status','all'], rows)
        self.assertEqual(data['result']['total'], 4)

    def test_city_exact_street_name_substring_and_filters(self):
        rows = [record(), record('2', miejscowosc='Łódź Nowa'), record('3', wojewodztwo='INNE')]
        _, data = self.run_cli(['search','--city','Lodz','--province','lodzkie','--street','dlug','--name','TEST'], rows)
        self.assertEqual(data['result']['total'], 1)
        self.assertEqual(self.run_cli(['search','--name','%_'], rows)[0], 2)

    def test_exact_get_preserves_inactive_status_and_leading_zeros(self):
        _, data = self.run_cli(['get','001'], [record(stan_apteki='NIEAKTYWNA')])
        self.assertEqual(data['result']['items'][0]['id'], '001')
        self.assertEqual(data['result']['items'][0]['registry_status'], 'NIEAKTYWNA')
        self.assertEqual(self.run_cli(['get','1'])[0], 2)

    def test_hours_are_raw_missing_is_null_no_open_now_or_stock_claim(self):
        row = record(nazwa_apteki='', telefon='', godziny_otwarcia_sobota='')
        _, data = self.run_cli(['get','001'], [row])
        item = data['result']['items'][0]
        self.assertIsNone(item['name']);self.assertIsNone(item['contact']['telefon'])
        self.assertEqual(item['opening_hours_reported']['poniedzialek'], '08:00 - 16:00')
        self.assertIsNone(item['opening_hours_reported']['sobota'])
        self.assertFalse(item['open_now_assessed']);self.assertFalse(item['medicine_stock_assessed'])

    def test_owner_and_manager_fields_are_omitted(self):
        _, data = self.run_cli(['get','001'], [record(wlasciciel_nazwa='PRIVATE OWNER', kierownik_npwz='PRIVATE-ID')])
        self.assertNotIn('PRIVATE', json.dumps(data))

    def test_pagination_and_missing_page(self):
        rows=[record('2'), record('001')]
        _, first=self.run_cli(['search','--city','Lodz','--limit','1'],rows)
        self.assertEqual(first['result']['items'][0]['id'],'001')
        self.assertEqual(first['result']['next_page'],2)
        _, second=self.run_cli(['search','--city','Lodz','--limit','1','--page','2'],rows)
        self.assertFalse(second['result']['has_more'])
        self.assertEqual(self.run_cli(['search','--city','Lodz','--page','3'],rows)[0],2)

    def test_bad_arguments_do_not_download(self):
        cases=[[],['wrong'],['search'],['search','--province','lodzkie'],['search','--city','a'],
               ['search','--city','Łódź','--limit','51'],['get','../1'],['get','1','--page','0']]
        for args in cases:
            with self.subTest(args=args),patch.object(M,'load',side_effect=AssertionError('network')):
                with contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(M.main(args),64)
                self.assertEqual(out.getvalue(),'');self.assertIn('error',json.loads(err.getvalue()))


class FormatTests(unittest.TestCase):
    def test_pipe_quotes_newlines_and_unicode_are_preserved(self):
        raw=export([record(nazwa_apteki='Apteka | "Test"\nDruga linia')])
        self.assertEqual(M.parse(raw)[0]['nazwa_apteki'],'Apteka | "Test"\nDruga linia')

    def test_malformed_headers_rows_ids_and_duplicates_fail(self):
        good=export([record()])
        cases=[b'<html/>',b'\xff',good.replace(b'identyfikator_apteki',b'other'),
               export([record(),record()]),export([record(id='x')]),export([record(stan_apteki='')]),
               good+b'123|incomplete\n',good.rstrip()+b'|extra\n',good.splitlines()[0]+b'\n']
        for raw in cases:
            with self.subTest(raw=raw[:20]),self.assertRaises(M.SkillError) as error:M.parse(raw)
            self.assertEqual(error.exception.code,69)

    def test_record_limit(self):
        with patch.object(M,'MAX_ROWS',0),self.assertRaises(M.SkillError):M.parse(export([record()]))

    def test_local_file_date_is_only_a_label_and_retrieval_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'Rejestr_Aptek_stan_na_dzien_2020-01-01.csv';path.write_bytes(export([record()]))
            with patch.object(M.urllib.request,'build_opener',side_effect=AssertionError('network')):
                raw,meta=M.load(path)
            self.assertEqual(meta['source_as_of'],'2020-01-01')
            self.assertIsNone(meta['retrieved_at']);self.assertIsNone(meta['source_url'])
            self.assertFalse(meta['local_file_verified'])
            path=path.rename(path.with_name('unknown.csv'))
            self.assertIsNone(M.load(path)[1]['source_as_of'])

    def test_local_size_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'x.csv';path.write_bytes(b'1234')
            with patch.object(M,'MAX_BYTES',3),self.assertRaises(M.SkillError):M.load(path)


class Response(io.BytesIO):
    def __init__(self, raw, headers=None):super().__init__(raw);self.headers=headers or {}
    def geturl(self):return M.SOURCE


class NetworkTests(unittest.TestCase):
    def load(self,response):
        opener=type('Opener',(),{'open':lambda *args,**kwargs:response})()
        with patch.object(M.urllib.request,'build_opener',return_value=opener):return M.load()

    def test_success_date_and_digest_without_disk_cache(self):
        raw=export([record()]);_,meta=self.load(Response(raw,{'Content-Disposition':'attachment;filename=Rejestr_Aptek_stan_na_dzien_2026-11-13.csv','Content-Length':str(len(raw))}))
        self.assertEqual(meta['source_as_of'],'2026-11-13');self.assertIsNotNone(meta['retrieved_at'])
        self.assertEqual(meta['bytes'],len(raw));self.assertEqual(len(meta['sha256']),64)

    def test_partial_compressed_and_oversized_responses_fail(self):
        for headers in ({'Content-Length':'999'},{'Content-Encoding':'gzip'}):
            with self.subTest(headers=headers),self.assertRaises(M.SkillError):self.load(Response(b'123',headers))
        with patch.object(M,'MAX_BYTES',2),self.assertRaises(M.SkillError):self.load(Response(b'123'))

    def test_redirect_is_not_followed(self):
        with self.assertRaises(M.SkillError):M.NoRedirect().redirect_request(None,None,302,'',{},'https://example.com')

    def test_http_rate_limit_and_network_errors(self):
        for exc,kind in [(urllib.error.HTTPError(M.SOURCE,429,'limit',{'Retry-After':'60'},None),'rate_limit'),
                         (urllib.error.URLError('offline'),'network_error')]:
            opener=type('Opener',(),{})()
            with patch.object(M.urllib.request,'build_opener',return_value=opener):
                with patch.object(opener,'open',create=True,side_effect=exc),self.assertRaises(M.SkillError) as error:M.load()
            self.assertEqual(error.exception.kind,kind)
            if kind=='rate_limit':self.assertEqual(error.exception.details['retry_after'],'60')


if __name__=='__main__':unittest.main()
