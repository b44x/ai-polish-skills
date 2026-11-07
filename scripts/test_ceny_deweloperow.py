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


if __name__ == '__main__':
    unittest.main()
