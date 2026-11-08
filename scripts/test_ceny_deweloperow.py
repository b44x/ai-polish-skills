#!/usr/bin/env python3
"""Offline behavior and CLI contracts; all fixtures are synthetic."""
import contextlib
import copy
from decimal import Decimal
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'skills/ceny-deweloperow/scripts/ceny_deweloperow.py'
SPEC = importlib.util.spec_from_file_location('ceny_deweloperow', str(SCRIPT))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def invoke(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = M.main(args)
    return code, out.getvalue(), err.getvalue()


def quote(total='100000.01', area='40', code='A/1', sqm='2500'):
    return dict(Symbol=code, Nazwa='lokal mieszkalny', PowU=area, Brutto=total, CenaM2=sqm)


def dated(days=None):
    return json.dumps(days or {'2020.01.01': {'A/1': quote()}}).encode()


def entry(observed='2020-01-01', total='100000.01', area='40', **extra):
    return M.observation('A/1', observed, 'file_snapshot_date', total, '2500', area,
                         kind='lokal mieszkalny', **extra)


def loaded(rows, dates=None, resource='1', dataset='10', institution='20', profile='dated-json'):
    meta = dict(id=resource, dataset_id=dataset, institution_id=institution, profile=profile,
                last_snapshot=max(dates or [r['observed_on'] for r in rows]))
    return meta, rows, set(dates or [r['observed_on'] for r in rows])


def record(kind='resource', identifier='1'):
    return dict(id=identifier, type=kind, attributes=dict(title='Synthetic price source', format='json',
                file_url='https://api.dane.gov.pl/media/resources/test.json', data_date='2026-01-01',
                license_name='test attribution'), relationships=dict(
                dataset=dict(data=dict(id='10')), institution=dict(data=dict(id='20'))))


def snapshot_csv(rows=None):
    import csv
    headers = ['nazwa_inwestycji', 'budynek', 'numer_lokalu', 'typ_obiektu', 'area_usable_m2',
               'price_sqm_gross_pln', 'price_total_gross_pln', 'currency', 'snapshot_date', 'status_norm']
    data = rows or [['Test', 'A', '1', 'mieszkanie', '40', '2500', '100000.01', 'PLN', '2020-01-01', 'dostępne']]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(data)
    return output.getvalue().encode('utf-8-sig')


def xml(cells=None):
    headers = ['Inwestycja', 'Numer', 'Typ', 'Powierzchnia rozliczeniowa', 'Cena ofertowa brutto', 'cena brutto m2']
    values = cells or ['Test', '1', 'Dom', '40', '100000.01', '2500']
    def row(items):
        return '<Row>' + ''.join('<Cell><Data>%s</Data></Cell>' % i for i in items) + '</Row>'
    return ('<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet><Table>'
            + row(headers) + row(values) + '</Table></Worksheet></Workbook>').encode()


class Response(io.BytesIO):
    def geturl(self):
        return 'https://api.dane.gov.pl/media/resources/test.json'


class TransportContracts(unittest.TestCase):
    def test_network_timeout_and_http_errors(self):
        for error in [TimeoutError(), urllib.error.URLError('offline')]:
            with self.subTest(error=error), patch.object(M.OPENER, 'open', side_effect=error):
                with self.assertRaises(M.SkillError) as raised:
                    M.fetch_bytes(M.BASE + 'resources/1', 10)
                self.assertEqual(raised.exception.code, 69)
        for status in [404, 429, 503]:
            error = urllib.error.HTTPError(M.BASE, status, 'test', {'Retry-After': '60'}, io.BytesIO())
            with patch.object(M.OPENER, 'open', side_effect=error) as op:
                with self.assertRaises(M.SkillError) as raised:
                    M.fetch_bytes(M.BASE + 'resources/1', 10)
                self.assertEqual(raised.exception.code, 2 if status == 404 else 69)
                self.assertEqual(raised.exception.details['retry_after'], '60')
                self.assertEqual(op.call_count, 1)

    def test_response_size_and_timeout_are_bounded(self):
        with patch.object(M.OPENER, 'open', return_value=Response(b'12345')) as op:
            self.assertEqual(M.fetch_bytes(M.BASE + 'resources/1', 5), b'12345')
            self.assertEqual(op.call_args.kwargs['timeout'], 20)
        with patch.object(M.OPENER, 'open', return_value=Response(b'123456')):
            with self.assertRaises(M.SkillError) as raised:
                M.fetch_bytes(M.BASE + 'resources/1', 5)
            self.assertEqual(raised.exception.kind, 'response_too_large')

    def test_urls_cannot_target_publishers_or_local_network(self):
        for url in ['http://api.dane.gov.pl/media/resources/file', 'https://127.0.0.1/file',
                    'https://api.dane.gov.pl.evil.invalid/media/resources/file',
                    'https://user:pass@api.dane.gov.pl/media/resources/file',
                    'https://api.dane.gov.pl:444/media/resources/file',
                    'https://api.dane.gov.pl/media/resources/%2e%2e/private',
                    'https://api.dane.gov.pl/other/file']:
            with self.subTest(url=url), patch.object(M.OPENER, 'open') as op:
                with self.assertRaises(M.SkillError):
                    M.fetch_bytes(url, 10)
                op.assert_not_called()

    def test_redirect_is_rejected_before_external_request(self):
        with self.assertRaises(M.SkillError):
            M.TrustedRedirect().redirect_request(None, None, 302, '', {}, 'https://localhost/private')

    def test_json_rejects_duplicates_nonfinite_and_bad_encoding(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'\xff', b'<html>bad</html>']:
            with self.subTest(raw=raw), self.assertRaises(M.SkillError):
                M.decode_json(raw)

    def test_resource_does_not_download_external_file(self):
        resource = record()
        resource['attributes']['file_url'] = 'https://example.invalid/private.csv'
        with patch.object(M, 'get_record', side_effect=[resource, record('dataset', '10')]), patch.object(M, 'fetch_bytes') as fetch:
            with self.assertRaises(M.SkillError) as raised:
                M.load_resource(1)
            self.assertEqual(raised.exception.kind, 'unsupported_source')
            fetch.assert_not_called()

    def test_resource_fetches_rights_and_checks_its_identifier(self):
        dataset = record('dataset', '10')
        with patch.object(M, 'get_record', side_effect=[record(), dataset]), patch.object(M, 'fetch_bytes', return_value=dated()):
            metadata, rows, dates = M.load_resource(1)
        self.assertEqual(metadata['reuse_conditions']['license_name'], 'test attribution')
        self.assertEqual(metadata['profile'], 'dated-json')
        self.assertEqual(dates, {'2020-01-01'})
        self.assertEqual(len(metadata['sha256']), 64)
        self.assertEqual(len(rows), 1)
        with patch.object(M, 'fetch_json', return_value={'data': record(identifier='2')}):
            with self.assertRaises(M.SkillError):
                M.get_record('resource', 1)

    def test_invalid_relationship_is_structured_upstream_error(self):
        for relationships in [None, [], {'dataset': None}, {'dataset': {'data': None}}]:
            item = record()
            item['relationships'] = relationships
            with self.subTest(relationships=relationships), self.assertRaises(M.SkillError):
                M.related_id(item, 'dataset')


class FileFormats(unittest.TestCase):
    def test_dated_json_preserves_dates_and_exact_decimal_prices(self):
        profile, rows, dates = M.dated_json(dated(), {})
        self.assertEqual(profile, 'dated-json')
        self.assertEqual(rows[0]['price_total_pln'], Decimal('100000.01'))
        self.assertEqual(dates, {'2020-01-01'})

    def test_bad_schema_dates_numbers_and_duplicate_normalized_dates(self):
        for raw in [b'[]', b'{}', dated({'bad': {'A/1': quote()}}),
                    dated({'2020.02.30': {'A/1': quote()}}),
                    dated({'2020.01.01': {'wrong': quote()}}),
                    dated({'2020.01.01': {'A/1': quote()}, '2020-01-01': {'A/1': quote()}})]:
            with self.subTest(raw=raw), self.assertRaises(M.SkillError):
                M.dated_json(raw, {})
        for value in [True, '-1', 'NaN', '1 000,00', '1.000,00', {}, '0.000000001', '1000000000001']:
            with self.subTest(value=value), self.assertRaises(M.SkillError):
                M.number(value)

    def test_observation_cap(self):
        raw = dated({'2020.01.01': {'A/1': quote()}, '2020.01.02': {'A/1': quote()}})
        with patch.object(M, 'MAX_OBSERVATIONS', 1), self.assertRaises(M.SkillError):
            M.dated_json(raw, {})

    def test_file_snapshot_date_overrides_fresh_catalog_metadata(self):
        metadata = {'catalog_data_date': '2026-01-01'}
        profile, rows, dates = M.parse_csv(snapshot_csv(), metadata)
        self.assertEqual((profile, dates), ('snapshot-csv', {'2020-01-01'}))
        self.assertEqual(rows[0]['date_basis'], 'file_snapshot_date')
        self.assertEqual(metadata['catalog_data_date'], '2026-01-01')

    def test_same_flat_number_in_different_buildings_is_not_merged(self):
        values = [['Test', b, '1', 'mieszkanie', '40', '2500', '100000', 'PLN', '2020-01-01', 'wolne'] for b in ['A', 'B']]
        _, rows, _ = M.parse_csv(snapshot_csv(values), {})
        self.assertEqual({r['unit_id'] for r in rows}, {'Test::A::mieszkanie::1', 'Test::B::mieszkanie::1'})

    def test_apartment_and_parking_with_same_number_have_distinct_identity(self):
        values = [['Test', 'A', '1', kind, '40', '2500', '100000', 'PLN', '2020-01-01', 'wolne']
                  for kind in ['mieszkanie', 'miejsce postojowe']]
        _, rows, _ = M.parse_csv(snapshot_csv(values), {})
        self.assertEqual(len({row['unit_id'] for row in rows}), 2)
        self.assertEqual(rows[0]['unit_id'], 'Test::A::mieszkanie::1')

    def test_zero_price_remains_unknown_not_free(self):
        row = entry(total='0')
        self.assertIsNone(row['price_total_pln'])
        self.assertTrue(row['zero_price_reported'])
        result = M.history([loaded([row])], 'A/1')
        self.assertIsNone(result['first_to_last_change'])
        self.assertIsNone(result['lowest_observed_pln'])

    def test_csv_unknown_schema_currency_and_truncated_rows(self):
        values = [['Test', 'A', '1', 'mieszkanie', '40', '2500', '100000', 'EUR', '2020-01-01', 'wolne']]
        for raw in [b'unknown,columns\nx,y\n', snapshot_csv(values), snapshot_csv() + b'bad,row\n', b'a,a\n1,2\n']:
            with self.subTest(raw=raw[:40]), self.assertRaises(M.SkillError):
                M.parse_csv(raw, {'catalog_data_date': '2020-01-01'})

    def test_disclosure_csv_preserves_base_price_and_effective_date(self):
        import csv
        headers = ['Nr lokalu lub domu jednorodzinnego nadany przez dewelopera',
                   'Miejscowość lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego',
                   'Ulica lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego',
                   'Nr nieruchomości lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego',
                   'Rodzaj nieruchomości: lokal mieszkalny, dom jednorodzinny',
                   'Cena m 2 powierzchni użytkowej',
                   'Cena lokalu mieszkalnego lub domu jednorodzinnego będących przedmiotem umowy',
                   'Data od której cena obowiązuje cena lokalu mieszkalnego lub domu jednorodzinnego',
                   'Cena lokalu mieszkalnego lub domu jednorodzinnego uwzględniająca inne składniki']
        out = io.StringIO()
        writer = csv.writer(out, delimiter=';')
        writer.writerow(headers)
        writer.writerow(['1', 'Test', 'Testowa', '1A', 'Lokal mieszkalny', '2500,00', '100000,01', '2019-12-01', '120000,01'])
        writer.writerow(['', 'Test', 'Testowa', '1A', 'X', '', '', '', '5000'])
        meta = {'catalog_data_date': '2020-01-01'}
        profile, rows, dates = M.parse_csv(out.getvalue().encode(), meta)
        self.assertEqual(profile, 'disclosure-csv')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['price_total_pln'], Decimal('100000.01'))
        self.assertEqual(rows[0]['price_effective_from'], '2019-12-01')
        self.assertEqual(rows[0]['observed_on'], '2020-01-01')
        self.assertIsNone(rows[0]['area_m2'])
        self.assertEqual(meta['excluded_rows_without_residential_identifier'], 1)

    def test_extreme_json_exponent_has_structured_format_error(self):
        with self.assertRaises(M.SkillError):
            M.decode_json(b'{"price":1e99999999999999999999999999999}')

    def test_spreadsheet_xml_explicitly_uses_catalog_date(self):
        profile, rows, dates = M.spreadsheet_xml(xml(), {'catalog_data_date': '2020-01-01'})
        self.assertEqual(profile, 'spreadsheet-xml')
        self.assertEqual(rows[0]['unit_id'], 'Test::1')
        self.assertEqual(rows[0]['date_basis'], 'catalog_data_date')
        self.assertEqual(dates, {'2020-01-01'})

    def test_xml_rejects_entities_utf16_and_unrecognized_tables(self):
        for raw in [b'<!DOCTYPE x [<!ENTITY x "test">]><x/>', b'<other/>',
                    xml().decode().encode('utf-16'), xml().replace(b'Cena ofertowa brutto', b'wrong column')]:
            with self.subTest(raw=raw[:40]), self.assertRaises(M.SkillError):
                M.spreadsheet_xml(raw, {'catalog_data_date': '2020-01-01'})

    def test_sparse_xml_cells_preserve_column_positions(self):
        raw = xml().replace(b'<Cell><Data>100000.01</Data></Cell>', b'<Cell xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet" ss:Index="5"><Data>100000.01</Data></Cell>')
        _, rows, _ = M.spreadsheet_xml(raw, {'catalog_data_date': '2020-01-01'})
        self.assertEqual(rows[0]['price_total_pln'], Decimal('100000.01'))

    def test_duplicate_unit_per_day_is_rejected_before_success(self):
        parsed = ('snapshot-csv', [entry(), entry()], {'2020-01-01'})
        resource = record()
        resource['attributes']['format'] = 'csv'
        with patch.object(M, 'get_record', side_effect=[resource, record('dataset', '10')]), patch.object(M, 'fetch_bytes', return_value=b''), patch.object(M, 'parse_csv', return_value=parsed):
            with self.assertRaises(M.SkillError):
                M.load_resource(1)


class HistoryBehavior(unittest.TestCase):
    def test_sorts_observations_and_compresses_equal_prices(self):
        rows = [entry('2020-01-03', '95000.00'), entry('2020-01-01', '100000.01'), entry('2020-01-02', '100000.01')]
        result = M.history([loaded(rows)], 'A/1')
        self.assertEqual(result['observations'], 3)
        self.assertEqual(len(result['price_points']), 2)
        self.assertEqual(result['price_points'][0]['samples'], 2)
        self.assertEqual(result['first_to_last_change'], {'pln': Decimal('-5000.01'), 'percent': Decimal('-5.00')})
        self.assertEqual(result['price_points'][1]['change_from_previous'], result['first_to_last_change'])

    def test_one_snapshot_is_insufficient_to_claim_unchanged_price(self):
        result = M.history([loaded([entry()])], 'A/1')
        self.assertIsNone(result['first_to_last_change'])
        self.assertEqual(result['observations'], 1)
        self.assertEqual(result['lowest_observed_pln'], Decimal('100000.01'))

    def test_gaps_and_absence_do_not_imply_sales(self):
        rows = [entry('2020-01-01'), entry('2020-01-03')]
        result = M.history([loaded(rows, {'2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04'})], 'A/1')
        self.assertFalse(result['present_in_latest_snapshot'])
        self.assertEqual(result['absent_on_snapshot_dates'], 2)
        self.assertEqual(result['calendar_gaps'][0]['unobserved_days'], 1)
        self.assertIsNone(result['price_points'][-1]['status'])
        self.assertIsNone(result['complete_history'])

    def test_conflicting_same_day_snapshots_fail(self):
        a, b = loaded([entry()]), loaded([entry(total='100001')], resource='2')
        with self.assertRaises(M.SkillError) as raised:
            M.history([a, b], 'A/1')
        self.assertEqual(raised.exception.code, 69)

    def test_duplicate_same_day_snapshots_are_deduplicated_with_provenance(self):
        result = M.history([loaded([entry()]), loaded([entry()], resource='2')], 'A/1')
        self.assertEqual(result['observations'], 1)
        self.assertEqual(result['price_points'][0]['resource_ids'], ['1', '2'])

    def test_changed_area_or_kind_suppresses_price_comparisons(self):
        for changed in [entry('2020-01-02', '200000', area='80'), dict(entry('2020-01-02'), kind='parking')]:
            result = M.history([loaded([entry(), changed])], 'A/1')
            self.assertIsNone(result['first_to_last_change'])
            self.assertIsNone(result['price_points'][-1]['change_from_previous'])
            self.assertIsNone(result['lowest_observed_pln'])

    def test_missing_area_is_disclosed(self):
        result = M.history([loaded([entry(area=None)])], 'A/1')
        self.assertIsNone(result['area_consistent'])

    def test_different_dataset_publisher_or_profile_cannot_be_combined(self):
        for kwargs in [dict(dataset='11'), dict(institution='21'), dict(profile='spreadsheet-xml')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(M.SkillError) as raised:
                M.history([loaded([entry()]), loaded([entry()], **kwargs)], 'A/1')
            self.assertEqual(raised.exception.kind, 'incomparable_sources')

    def test_missing_unit_is_not_found(self):
        with self.assertRaises(M.SkillError) as raised:
            M.history([loaded([entry()])], 'A')
        self.assertEqual(raised.exception.code, 2)

    def test_unknown_price_breaks_change_calculation(self):
        result = M.history([loaded([entry(), entry('2020-01-02', None), entry('2020-01-03', '200000')])], 'A/1')
        self.assertIsNone(result['price_points'][-1]['change_from_previous'])


class CLIContracts(unittest.TestCase):
    def test_help_and_bad_command_as_subprocess(self):
        for args, expected in [(['--help'], 0), (['history', '--help'], 0), (['bad-command'], 64)]:
            response = subprocess.run([sys.executable, str(SCRIPT)] + args, capture_output=True, text=True)
            self.assertEqual(response.returncode, expected)
            if expected == 64:
                self.assertEqual(response.stdout, '')
                self.assertIn('error', json.loads(response.stderr))
            else:
                self.assertEqual(response.stderr, '')

    def test_validation_is_offline(self):
        cases = [[], ['units', '0'], ['units', '1', '--limit', '101'], ['search', '\n'],
                 ['history', '1', 'A/1', '--with-resource', '1'],
                 ['history', '1', 'A/1', '--with-resource', '2', '--with-resource', '3', '--with-resource', '4']]
        with patch.object(M, 'load_resource', side_effect=AssertionError('network')), patch.object(M, 'fetch_json', side_effect=AssertionError('network')):
            for args in cases:
                with self.subTest(args=args):
                    code, out, err = invoke(args)
                    self.assertEqual((code, out), (64, ''))
                    self.assertIn('error', json.loads(err))

    def test_all_or_nothing_when_a_later_resource_fails(self):
        with patch.object(M, 'load_resource', side_effect=[loaded([entry()]), M.SkillError('offline', 'network_error', 69)]):
            code, out, err = invoke(['history', '1', 'A/1', '--with-resource', '2'])
        self.assertEqual((code, out), (69, ''))
        self.assertEqual(json.loads(err)['type'], 'network_error')

    def test_history_stdout_is_json_with_decimal_strings(self):
        with patch.object(M, 'load_resource', return_value=loaded([entry()])):
            code, out, err = invoke(['history', '1', 'A/1'])
        self.assertEqual((code, err), (0, ''))
        result = json.loads(out)['result']
        self.assertEqual(result['lowest_observed_pln'], '100000.01')
        self.assertTrue(result['asking_prices_only'])
        self.assertIsNone(result['total_includes_additional_costs'])

    def test_catalogue_pagination_ignores_upstream_links(self):
        data = dict(data=[record('dataset')], meta=dict(count=2), links=dict(next='https://localhost/ignored'))
        with patch.object(M, 'fetch_json', return_value=data) as fetch:
            code, out, err = invoke(['search', 'Test', '--limit', '1'])
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(json.loads(out)['result']['next_page'], 2)
        self.assertTrue(json.loads(out)['result']['candidates_only'])

    def test_units_paginate_only_the_latest_snapshot(self):
        rows = [entry('2020-01-01'), entry('2020-01-02'), dict(entry('2020-01-02'), unit_id='B/1')]
        with patch.object(M, 'load_resource', return_value=loaded(rows)):
            code, out, err = invoke(['units', '1', '--page', '2', '--limit', '1'])
        self.assertEqual((code, err), (0, ''))
        result = json.loads(out)['result']
        self.assertEqual(result['items'][0]['unit_id'], 'B/1')
        self.assertEqual(result['total'], 2)
        self.assertFalse(result['has_more'])

    def test_empty_catalogue_or_unit_page_returns_not_found(self):
        with patch.object(M, 'fetch_json', return_value={'data': [], 'meta': {'count': 0}}):
            code, out, err = invoke(['search', 'missing'])
        self.assertEqual((code, out), (2, ''))
        self.assertEqual(json.loads(err)['type'], 'not_found')
        with patch.object(M, 'load_resource', return_value=loaded([entry()])):
            code, out, _ = invoke(['units', '1', '--page', '2'])
        self.assertEqual((code, out), (2, ''))

# Additional synthetic OOXML exports model the verified table schemas, not live prices.
DISCLOSURE_HEADERS = [
    'Nr lokalu lub domu jednorodzinnego nadany przez dewelopera',
    'Miejscowość lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego',
    'Ulica lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego',
    'Nr nieruchomości lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego',
    'Rodzaj nieruchomości: lokal mieszkalny, dom jednorodzinny',
    'Cena m2 powierzchni użytkowej lokalu mieszkalnego / domu jednorodzinnego zł',
    'Cena lokalu mieszkalnego lub domu jednorodzinnego będących przedmiotem umowy',
    'Data od której obowiązuje cena lokalu miesz. lub domu jedn. będących przedmiotem umowy',
]


def xlsx(rows, *, headers=None, shared=False, formula=False, external=False):
    import zipfile
    from xml.sax.saxutils import escape
    headers = headers or DISCLOSURE_HEADERS
    output = io.BytesIO()
    main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    strings, xml_rows = [], []
    def column(index):
        result = ''
        while index:
            index, char = divmod(index - 1, 26)
            result = chr(65 + char) + result
        return result
    for number, values in enumerate([headers] + rows, 1):
        cells = []
        for index, value in enumerate(values, 1):
            if value is None:
                continue
            address = column(index) + str(number)
            if shared:
                strings.append(str(value))
                data = '<v>%s</v>' % (len(strings) - 1)
                kind = 's'
            else:
                data = '<is><t>%s</t></is>' % escape(str(value))
                kind = 'inlineStr'
            if formula and number == 2 and index == 7:
                data = '<f>1+1</f><v>2</v>'
                kind = 'n'
            cells.append('<c r="%s" t="%s">%s</c>' % (address, kind, data))
        xml_rows.append('<row r="%s">%s</row>' % (number, ''.join(cells)))
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('xl/workbook.xml', '<workbook xmlns="%s" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Dane" sheetId="2" r:id="rId2"/></sheets></workbook>' % main)
        mode = ' TargetMode="External"' if external else ''
        target = 'https://localhost/private' if external else 'worksheets/sheet1.xml'
        archive.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId2" Target="%s"%s/></Relationships>' % (target, mode))
        archive.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>' % (main, ''.join(xml_rows)))
        if shared:
            archive.writestr('xl/sharedStrings.xml', '<sst xmlns="%s">%s</sst>' % (main, ''.join('<si><r><t>%s</t></r></si>' % escape(value) for value in strings)))
    return output.getvalue()


def disclosure_value(unit='0001', total='100000.01', effective='2020-01-01 10:00:00'):
    return [unit, 'Test', 'Testowa', '1', 'Lokal mieszkalny', '2500', total, effective]


class ExpandedSourceContracts(unittest.TestCase):
    def test_search_uses_exact_title_phrase_instead_of_fuzzy_full_text(self):
        from urllib.parse import parse_qs, urlsplit
        with patch.object(M, 'fetch_json', return_value={'data': [record('dataset')], 'meta': {'count': 1}}) as fetch:
            code, out, err = invoke(['search', 'Dom Development'])
        self.assertEqual((code, err), (0, ''))
        params = parse_qs(urlsplit(fetch.call_args.args[0]).query)
        self.assertEqual(params['title[phrase]'], ['Dom Development'])
        self.assertNotIn('q', params)
        self.assertEqual(params['sort'], ['-modified'])
        self.assertEqual(json.loads(out)['result']['total'], 1)

    def test_resource_listing_distinguishes_download_eligibility_from_schema_support(self):
        mirrored, external, unsupported = record(), record(identifier='2'), record(identifier='3')
        external['attributes']['file_url'] = 'https://example.invalid/file.csv'
        unsupported['attributes']['format'] = 'pdf'
        payload = dict(data=[mirrored, external, unsupported], meta=dict(count=3))
        with patch.object(M, 'fetch_json', return_value=payload):
            code, out, err = invoke(['resources', '10'])
        self.assertEqual((code, err), (0, ''))
        items = json.loads(out)['result']['items']
        self.assertTrue(items[0]['download_eligible'])
        self.assertEqual(items[0]['schema_support'], 'unverified_until_read')
        self.assertFalse(items[1]['download_eligible'])
        self.assertEqual(items[2]['download_blocker'], 'unsupported_format')

    def test_catalog_hosted_link_is_usable_when_file_url_is_missing(self):
        item = record()
        item['attributes']['file_url'] = ''
        item['attributes']['link'] = 'https://api.dane.gov.pl/media/resources/copy.json'
        with patch.object(M, 'get_record', side_effect=[item, record('dataset', '10')]), patch.object(M, 'fetch_bytes', return_value=dated()) as fetch:
            meta, _, _ = M.load_resource(1)
        self.assertEqual(fetch.call_args.args[0], item['attributes']['link'])
        self.assertEqual(meta['download_url'], item['attributes']['link'])

    def test_effective_timestamps_preserve_time_and_unknown_markers(self):
        self.assertEqual(M.effective_time('2026-05-07 13:41:17'), ('2026-05-07', '2026-05-07T13:41:17'))
        self.assertEqual(M.effective_time('29-09-2025 12:10'), ('2025-09-29', '2025-09-29T12:10:00'))
        self.assertEqual(M.effective_time('X'), (None, None))
        for value in ['2025-02-30 12:00', 'not a date']:
            with self.subTest(value=value), self.assertRaises(M.SkillError):
                M.effective_time(value)

    def test_xlsx_reads_shared_and_inline_strings_without_losing_leading_zeros(self):
        for shared in [False, True]:
            with self.subTest(shared=shared):
                meta = {'catalog_data_date': '2026-01-01'}
                profile, rows, dates = M.parse_xlsx(xlsx([disclosure_value()], shared=shared), meta)
                self.assertEqual(profile, 'disclosure-xlsx')
                self.assertEqual(rows[0]['unit_id'], 'Test::Testowa::1::0001')
                self.assertEqual(rows[0]['price_total_pln'], Decimal('100000.01'))
                self.assertEqual(dates, {'2026-01-01'})
                self.assertEqual(rows[0]['price_effective_at'], '2020-01-01T10:00:00')

    def test_sparse_xlsx_preserves_empty_cells_and_excludes_components(self):
        component = [None, 'Test', 'Testowa', '1', None, None, None, None]
        meta = {'catalog_data_date': '2026-01-01'}
        _, rows, _ = M.parse_xlsx(xlsx([component, disclosure_value()]), meta)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['price_total_pln'], Decimal('100000.01'))
        self.assertEqual(meta['excluded_rows_without_residential_identifier'], 1)

    def test_xlsx_declared_history_preserves_intraday_changes_and_presence(self):
        meta = {'id': '1', 'dataset_id': '10', 'institution_id': '20', 'catalog_data_date': '2026-01-01', 'last_snapshot': '2026-01-01'}
        values = [disclosure_value(), disclosure_value(total='110000.01', effective='2020-01-01 11:00:00'),
                  disclosure_value(unit='0002', effective='2025-12-31 12:00:00')]
        profile, rows, dates = M.parse_xlsx(xlsx(values), meta)
        self.assertEqual(profile, 'disclosure-xlsx-history')
        meta['profile'] = profile
        result = M.history([(meta, rows, dates)], 'Test::Testowa::1::0001')
        self.assertEqual(result['observations'], 2)
        self.assertEqual(result['first_to_last_change']['pln'], Decimal('10000.00'))
        self.assertEqual(result['price_points'][1]['price_effective_at'], '2020-01-01T11:00:00')
        self.assertEqual(result['timeline_type'], 'published_price_effective_dates')
        self.assertIsNone(result['calendar_gaps'])
        self.assertIsNone(result['absent_on_snapshot_dates'])
        self.assertTrue(result['present_in_latest_snapshot'])

    def test_xlsx_units_select_last_declared_price_for_each_unit(self):
        values = [disclosure_value(), disclosure_value(total='110000.01', effective='2020-01-02 10:00:00')]
        meta = {'catalog_data_date': '2026-01-01', 'last_snapshot': '2026-01-01'}
        _, rows, _ = M.parse_xlsx(xlsx(values), meta)
        args = type('Args', (), dict(query=None, page=1, limit=10))()
        result = M.units(meta, rows, args)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['price_total_pln'], Decimal('110000.01'))
        self.assertEqual(result['observed_on'], '2026-01-01')
        self.assertEqual(result['items'][0]['date_basis'], 'file_price_effective_date')

    def test_repeated_xlsx_units_without_effective_dates_fail(self):
        values = [disclosure_value(), disclosure_value(effective='X')]
        with self.assertRaises(M.SkillError):
            M.parse_xlsx(xlsx(values), {'catalog_data_date': '2026-01-01'})

    def test_declared_history_rejects_unknown_intraday_order(self):
        values = [disclosure_value(effective='2020-01-01'), disclosure_value(total='110000', effective='2020-01-01 10:00:00')]
        meta = {'id': '1', 'dataset_id': '10', 'institution_id': '20', 'catalog_data_date': '2026-01-01', 'last_snapshot': '2026-01-01'}
        profile, rows, dates = M.parse_xlsx(xlsx(values), meta)
        meta['profile'] = profile
        with self.assertRaises(M.SkillError):
            M.history([(meta, rows, dates)], rows[0]['unit_id'])

    def test_xlsx_formulas_external_relationships_and_broken_archives_fail(self):
        for raw in [xlsx([disclosure_value()], formula=True), xlsx([disclosure_value()], external=True), b'not zip']:
            with self.subTest(length=len(raw)), self.assertRaises(M.SkillError):
                M.parse_xlsx(raw, {'catalog_data_date': '2026-01-01'})

    def test_xlsx_uncompressed_size_limits_are_enforced(self):
        helper = sys.modules['housing_xlsx']
        raw = xlsx([disclosure_value()])
        for bound in ['MAX_PART', 'MAX_TOTAL']:
            with self.subTest(bound=bound), patch.object(helper, bound, 64), self.assertRaises(M.SkillError) as raised:
                M.parse_xlsx(raw, {'catalog_data_date': '2026-01-01'})
            self.assertEqual(raised.exception.kind, 'response_too_large')


    def test_publisher_product_code_stays_stable_when_location_is_completed(self):
        headers = DISCLOSURE_HEADERS + ['kod_produktu', 'Budynek', 'Rodzaj']
        raw_code = 'PROJECT_A_MK_0001'
        missing = disclosure_value(unit=raw_code) + [raw_code, 'PROJECT_A', 'Mieszkanie']
        missing[1:4] = ['', '', '']
        complete = disclosure_value(unit=raw_code) + [raw_code, 'PROJECT_A', 'Mieszkanie']
        ids = []
        for values, expected_missing in [(missing, True), (complete, False)]:
            meta = {'catalog_data_date': '2026-01-01'}
            profile, rows, _ = M.parse_xlsx(xlsx([values], headers=headers), meta)
            self.assertEqual(profile, 'disclosure-xlsx-coded')
            self.assertEqual(meta['unit_identity'], 'publisher_product_code')
            self.assertEqual(rows[0]['location_incomplete'], expected_missing)
            ids.append(rows[0]['unit_id'])
        self.assertEqual(ids, [raw_code, raw_code])

    def test_mismatched_publisher_product_code_is_rejected(self):
        headers = DISCLOSURE_HEADERS + ['kod_produktu', 'Budynek', 'Rodzaj']
        values = disclosure_value() + ['different', 'A', 'Mieszkanie']
        with self.assertRaises(M.SkillError):
            M.parse_xlsx(xlsx([values], headers=headers), {'catalog_data_date': '2026-01-01'})

    def test_xlsx_unknown_prices_are_preserved_as_unknown(self):
        values = disclosure_value(total='X', effective='X')
        values[5] = 'brak'
        _, rows, _ = M.parse_xlsx(xlsx([values]), {'catalog_data_date': '2026-01-01'})
        self.assertIsNone(rows[0]['price_total_pln'])
        self.assertIsNone(rows[0]['price_sqm_pln'])
        self.assertIsNone(rows[0]['price_effective_from'])

    def test_xlsx_duplicate_members_and_dtd_are_rejected(self):
        import zipfile
        import warnings
        raw = xlsx([disclosure_value()])
        for change in ['duplicate', 'dtd']:
            output = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(output, 'w') as target:
                for name in source.namelist():
                    data = source.read(name)
                    if change == 'dtd' and name == 'xl/workbook.xml':
                        data = b'<!DOCTYPE workbook [<!ENTITY x "test">]>' + data
                    target.writestr(name, data)
                if change == 'duplicate':
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore', UserWarning)
                        target.writestr('xl/workbook.xml', source.read('xl/workbook.xml'))
            with self.subTest(change=change), self.assertRaises(M.SkillError):
                M.parse_xlsx(output.getvalue(), {'catalog_data_date': '2026-01-01'})


if __name__ == '__main__':
    unittest.main()
