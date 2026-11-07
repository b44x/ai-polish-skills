#!/usr/bin/env python3
"""Offline contracts. All response fixtures below are explicitly synthetic."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parent.parent


def module(name):
    path = ROOT / 'skills' / name / 'scripts' / (name.replace('-', '_') + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), str(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ADDRESS, JOBS, DATA = [module(n) for n in ('adresy', 'solid-jobs', 'otwarte-dane')]


def invoke(mod, args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = mod.main(args)
    return code, out.getvalue(), err.getvalue()


def address():
    return {'type': 'address', 'returned objects': 1, 'found objects': 15,
            'results': {'1': {'city': 'Test', 'x': '21.1', 'y': '52.3', 'accuracy': '0.4', 'simc': '0000001'}}}


def job(key='test', remote=True, value=22000, period='Month', currency='PLN'):
    return {'jobOfferKey': key, 'title': 'Synthetic role', 'company': 'Test',
            'url': 'https://example.invalid/offer', 'isRemote': remote,
            'salary': {'from': value, 'to': None, 'currency': currency, 'period': period, 'employmentType': 'B2B'}}


def page(rows, index=0, size=1, total=None):
    total = len(rows) if total is None else total
    return {'jobs': rows, 'pageIndex': index, 'pageSize': size, 'totalCount': total,
            'totalPages': (total + size - 1) // size}


def record(identifier='80', kind='dataset'):
    return {'id': identifier, 'type': kind, 'attributes': {'title': 'Synthetic dataset',
            'modified': '2000-01-01', 'license_chosen': None, 'license_condition_custom_description': 'Test attribution'}}


def listing(rows=None, total=3):
    return {'data': [record()] if rows is None else rows, 'meta': {'count': total},
            'links': {'next': 'https://example.invalid/do-not-follow'}}


class NetworkContracts(unittest.TestCase):
    def test_cli_validation_precedes_network(self):
        cases = [(ADDRESS, ['search', '']), (ADDRESS, ['reverse', 'nan', '21']),
                 (ADDRESS, ['reverse', '91', '21']), (ADDRESS, ['reverse', '52', 'inf']),
                 (ADDRESS, []), (JOBS, ['search', '--pages', '6']),
                 (JOBS, ['search', '--limit', '0']), (JOBS, ['search', '--page', '-1']),
                 (JOBS, ['search', '--min-pln-month', '-1']), (JOBS, ['search', '\n']),
                 (JOBS, ['stats', '--division', 'unknown']), (DATA, ['resource', '../etc']),
                 (DATA, ['search', 'test', '--limit', '101']), (DATA, ['resources', '0']),
                 (DATA, ['search', 'test', '--page', '0'])]
        for mod, args in cases:
            with self.subTest(args=args), patch.object(mod.urllib.request, 'urlopen', side_effect=AssertionError('Unexpected network')):
                code, out, err = invoke(mod, args)
                self.assertEqual((code, out), (64, ''))
                self.assertIn('error', json.loads(err))

    def test_http_errors_and_retry_after_without_retries(self):
        for mod in (ADDRESS, JOBS, DATA):
            for status, expected in ((404, 2), (429, 69), (503, 69), (401, 69)):
                error = urllib.error.HTTPError('https://example.invalid', status, 'Test', {'Retry-After': '120'}, io.BytesIO())
                self.addCleanup(error.close)
                with self.subTest(module=mod, status=status), patch.object(mod.urllib.request, 'urlopen', side_effect=error) as request:
                    with self.assertRaises(mod.SkillError) as raised:
                        mod.fetch('https://example.invalid')
                    self.assertEqual(raised.exception.code, expected)
                    self.assertEqual(raised.exception.details['retry_after'], '120')
                    self.assertEqual(request.call_count, 1)

    def test_timeout_network_and_truncated_response(self):
        import http.client
        for mod in (ADDRESS, JOBS, DATA):
            for error in (TimeoutError(), urllib.error.URLError('offline'), http.client.IncompleteRead(b'')):
                with self.subTest(module=mod, error=error), patch.object(mod.urllib.request, 'urlopen', side_effect=error):
                    with self.assertRaises(mod.SkillError) as raised:
                        mod.fetch('https://example.invalid')
                    self.assertEqual(raised.exception.code, 69)

    def test_bad_json_unicode_and_oversized_payload(self):
        for mod in (ADDRESS, JOBS, DATA):
            for body in (b'<html>error</html>', b'\xff', b'[]', b'{"value":NaN}', b'{"value":1e999}', b'{}' + b' ' * mod.MAX_RESPONSE):
                with self.subTest(module=mod, length=len(body)), patch.object(mod.urllib.request, 'urlopen', return_value=io.BytesIO(body)):
                    with self.assertRaises(mod.SkillError) as raised:
                        mod.fetch('https://example.invalid')
                    self.assertEqual(raised.exception.code, 69)

    def test_headers_and_bounded_timeout(self):
        for mod in (ADDRESS, JOBS, DATA):
            with patch.object(mod.urllib.request, 'urlopen', return_value=io.BytesIO(b'{}')) as request:
                self.assertEqual(mod.fetch('https://example.invalid'), {})
            self.assertEqual(request.call_args.kwargs['timeout'], 20)
            self.assertEqual(request.call_args.args[0].get_header('X-api-version'), mod.API_VERSION)

    def test_cli_upstream_error_is_json_stderr(self):
        for mod, args in ((ADDRESS, ['search', 'Test']), (JOBS, ['search']), (DATA, ['search', 'Test'])):
            with patch.object(mod, 'fetch', side_effect=mod.SkillError('offline', 'network_error', 69)):
                code, out, err = invoke(mod, args)
            self.assertEqual((code, out), (69, ''))
            self.assertEqual(json.loads(err)['type'], 'network_error')

    def test_subprocess_help_and_invalid_command(self):
        for name in ('adresy', 'solid-jobs', 'otwarte-dane'):
            script = ROOT / 'skills' / name / 'scripts' / (name.replace('-', '_') + '.py')
            for flag in ('--help', '-h'):
                res = subprocess.run([sys.executable, str(script), flag], capture_output=True, text=True)
                self.assertEqual((res.returncode, res.stderr), (0, ''))
                self.assertTrue(res.stdout)
            res = subprocess.run([sys.executable, str(script), 'bad-command'], capture_output=True, text=True)
            self.assertEqual((res.returncode, res.stdout), (64, ''))
            self.assertIn('error', json.loads(res.stderr))


class AddressBehavior(unittest.TestCase):
    def test_search_requests_gps_and_preserves_uncertainty(self):
        with patch.object(ADDRESS, 'fetch', return_value=address()) as fetch:
            code, out, err = invoke(ADDRESS, ['search', 'Marki, Andersa 1'])
        self.assertEqual((code, err), (0, ''))
        self.assertIn('srid=4326', fetch.call_args.args[0])
        result = json.loads(out)['result']
        self.assertEqual(result['results'][0]['latitude'], 52.3)
        self.assertEqual(result['results'][0]['longitude'], 21.1)
        self.assertIsNone(result['complete'])
        self.assertEqual(result['upstream_metadata']['found objects'], 15)

    def test_reverse_does_not_swap_latitude_and_longitude(self):
        from urllib.parse import parse_qs, urlsplit
        with patch.object(ADDRESS, 'fetch', return_value=address()) as fetch:
            code, _, _ = invoke(ADDRESS, ['reverse', '52.3', '21.1'])
        self.assertEqual(code, 0)
        self.assertEqual(parse_qs(urlsplit(fetch.call_args.args[0]).query)['location'], ['POINT(21.1 52.3)'])

    def test_homonymous_places_remain_ambiguous(self):
        payload = address()
        payload['type'] = 'city'
        del payload['returned objects']
        payload['results']['2'] = dict(payload['results']['1'], simc='0000002')
        result = ADDRESS.normalize(payload)
        self.assertTrue(result['ambiguous'])
        self.assertEqual(len(result['results']), 2)

    def test_zero_results_is_not_found(self):
        with patch.object(ADDRESS, 'fetch', return_value={'type': 'address', 'results': None, 'returned objects': 0}):
            code, out, err = invoke(ADDRESS, ['search', 'missing'])
        self.assertEqual((code, out), (2, ''))
        self.assertEqual(json.loads(err)['type'], 'not_found')

    def test_projected_or_nonfinite_coordinates_are_not_gps(self):
        for value in ('644234.29', 'NaN', 'Infinity', None, {}, True):
            payload = address()
            payload['results']['1']['x'] = value
            with self.subTest(value=value):
                with self.assertRaises(ADDRESS.SkillError):
                    ADDRESS.normalize(payload)

    def test_malformed_counts_and_null_without_zero(self):
        for payload in ({}, {'type': 'address', 'results': None}, dict(address(), **{'returned objects': 2}),
                        dict(address(), results=[])):
            with self.assertRaises(ADDRESS.SkillError) as raised:
                ADDRESS.normalize(payload)
            self.assertEqual(raised.exception.code, 69)


class JobsBehavior(unittest.TestCase):
    def test_empty_local_page_does_not_claim_no_jobs(self):
        with patch.object(JOBS, 'fetch', return_value=page([job(remote=False)], total=2)):
            code, out, err = invoke(JOBS, ['search', '--remote', '--limit', '1'])
        self.assertEqual((code, err), (0, ''))
        result = json.loads(out)['result']
        self.assertEqual(result['jobs'], [])
        self.assertTrue(result['has_more'])
        self.assertEqual(result['next_page'], 1)

    def test_bounded_scan_returns_remote_jobs_with_correct_next_page(self):
        pages = [page([job('1', False)], total=3), page([job('2')], index=1, total=3)]
        with patch.object(JOBS, 'fetch', side_effect=pages) as fetch, patch.object(JOBS.time, 'sleep'):
            code, out, err = invoke(JOBS, ['search', 'Python', '--remote', '--pages', '2', '--limit', '1'])
        self.assertEqual((code, err), (0, ''))
        result = json.loads(out)['result']
        self.assertEqual(result['scanned_offers'], 2)
        self.assertEqual(result['next_page'], 2)
        self.assertEqual(result['jobs'][0]['jobOfferKey'], '2')
        self.assertIn('search.searchTerm=Python', fetch.call_args_list[0].args[0])
        self.assertEqual(fetch.call_count, 2)

    def test_salary_filter_preserves_contracts_and_rejects_other_units(self):
        for row in (job(value=None), job(period='Hour'), job(currency='EUR'), job(value=10000)):
            self.assertFalse(JOBS.salary_match(row, 20000))
        row = job(value=10000)
        row['secondarySalary'] = dict(row['salary'], **{'from': 25000, 'employmentType': 'UoP'})
        self.assertTrue(JOBS.salary_match(row, 20000))
        self.assertEqual(row['salary']['from'], 10000)

    def test_second_page_failure_emits_no_partial_success(self):
        with patch.object(JOBS, 'fetch', side_effect=[page([job()], total=2), JOBS.SkillError('offline', 'network_error', 69)]), patch.object(JOBS.time, 'sleep'):
            code, out, err = invoke(JOBS, ['search', '--pages', '2', '--limit', '1'])
        self.assertEqual((code, out), (69, ''))
        self.assertIn('error', json.loads(err))

    def test_repeated_offer_between_pages_is_deduplicated(self):
        pages = [page([job()], total=2), page([job()], index=1, total=2)]
        with patch.object(JOBS, 'fetch', side_effect=pages), patch.object(JOBS.time, 'sleep'):
            code, out, _ = invoke(JOBS, ['search', '--pages', '2', '--limit', '1'])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)['result']['jobs']), 1)

    def test_no_upstream_jobs_is_not_found(self):
        with patch.object(JOBS, 'fetch', return_value=page([], size=20, total=0)):
            code, out, err = invoke(JOBS, ['search'])
        self.assertEqual((code, out), (2, ''))
        self.assertEqual(json.loads(err)['type'], 'not_found')

    def test_malformed_pagination_fails(self):
        for payload in (dict(page([job()]), totalPages=9), dict(page([job()]), pageIndex=9),
                        dict(page([job()]), jobs='bad'), dict(page([job()]), totalCount=True)):
            with self.assertRaises(JOBS.SkillError):
                JOBS.valid_page(payload, 0, 1)

    def test_negative_or_nonfinite_salary_fails(self):
        for value in (-1, True, float('inf'), '22000'):
            with self.assertRaises(JOBS.SkillError):
                JOBS.valid_page(page([job(value=value)]), 0, 1)

    def test_stats_preserves_generated_time_and_contract_groups(self):
        payload = {'scopeKind': 'division', 'scopeKey': 'IT', 'generatedAt': '2000-01-01',
                   'demand': {'activeOffers': 1}, 'salary': {'b2b': {'median': 20000}, 'permanent': {'median': 15000}}}
        with patch.object(JOBS, 'fetch', return_value=payload):
            code, out, err = invoke(JOBS, ['stats'])
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(out)['result'], payload)

    def test_wrong_stats_scope_fails(self):
        with patch.object(JOBS, 'fetch', return_value={'scopeKind': 'city'}):
            code, out, _ = invoke(JOBS, ['stats'])
        self.assertEqual((code, out), (69, ''))


class DataBehavior(unittest.TestCase):
    def test_pagination_and_license_are_preserved_without_following_links(self):
        with patch.object(DATA, 'fetch', return_value=listing()) as fetch:
            code, out, err = invoke(DATA, ['search', 'transport', '--limit', '1'])
        self.assertEqual((code, err), (0, ''))
        result = json.loads(out)['result']
        self.assertEqual(result['next_page'], 2)
        self.assertIsNone(result['data'][0]['attributes']['license_chosen'])
        self.assertEqual(result['data'][0]['attributes']['modified'], '2000-01-01')
        self.assertEqual(fetch.call_count, 1)
        self.assertTrue(fetch.call_args.args[0].startswith(DATA.BASE))

    def test_resource_detail_retains_download_metadata_only(self):
        row = record('1800', 'resource')
        row['attributes']['file_url'] = 'http://127.0.0.1/private'
        with patch.object(DATA, 'fetch', return_value={'data': row}) as fetch:
            code, out, err = invoke(DATA, ['resource', '1800'])
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(out)['result']['data'], row)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(fetch.call_args.args[0], DATA.BASE + 'resources/1800')

    def test_dataset_and_resources_route_differently(self):
        for args, payload, suffix in ((['dataset', '80'], {'data': record()}, 'datasets/80'),
                                      (['resources', '80'], listing([record('1800', 'resource')], 1), 'datasets/80/resources?page=1&per_page=10')):
            with patch.object(DATA, 'fetch', return_value=payload) as fetch:
                code, _, err = invoke(DATA, args)
            self.assertEqual((code, err), (0, ''))
            self.assertEqual(fetch.call_args.args[0], DATA.BASE + suffix)

    def test_wrong_record_identity_is_not_success(self):
        for row in (record('81'), record('80', 'resource')):
            with patch.object(DATA, 'fetch', return_value={'data': row}):
                code, out, _ = invoke(DATA, ['dataset', '80'])
            self.assertEqual((code, out), (69, ''))

    def test_missing_or_truncated_metadata_is_not_no_results(self):
        for payload in ({}, listing(total=True), listing(total=0), listing([], 3), listing([record(), record()], 3)):
            with patch.object(DATA, 'fetch', return_value=payload):
                code, out, _ = invoke(DATA, ['search', 'test', '--limit', '1'])
            self.assertEqual((code, out), (69, ''))

    def test_empty_search_is_not_found(self):
        with patch.object(DATA, 'fetch', return_value=listing([], 0)):
            code, out, err = invoke(DATA, ['search', 'missing'])
        self.assertEqual((code, out), (2, ''))
        self.assertEqual(json.loads(err)['type'], 'not_found')


class RegistryRegression(unittest.TestCase):
    def test_stale_minified_registry_fails_check(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            for name in ('registry.json', 'registry.min.json'):
                (path / name).write_bytes((ROOT / 'registry' / name).read_bytes())
            (path / 'registry.min.json').write_text('{}\n')
            res = subprocess.run([sys.executable, str(ROOT / 'scripts/build_registry.py'), '--check', '--output-dir', folder], capture_output=True, text=True)
            self.assertEqual(res.returncode, 1)
            self.assertIn('registry.min.json', res.stderr)


if __name__ == '__main__':
    unittest.main()
