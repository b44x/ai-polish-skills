#!/usr/bin/env python3
"""Bounded read-only CeZ pharmacy export client, Python 3.8+ stdlib."""
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import http.client
import io
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

SOURCE = 'https://rejestry.ezdrowie.gov.pl/api/ra/filegenerator/getcsv'
HOME = 'https://rejestry.ezdrowie.gov.pl/ra/search/public'
MAX_BYTES = 40 * 1024 * 1024
MAX_ROWS = 100000
PUBLIC_TYPES = ('APTEKA OGÓLNODOSTĘPNA', 'PUNKT APTECZNY')
REQUIRED = ('identyfikator_apteki', 'nazwa_apteki', 'stan_apteki', 'rodzaj_apteki',
            'miejscowosc', 'nazwa_ulicy', 'numer_budynku', 'numer_lokalu', 'kod_pocztowy',
            'wojewodztwo', 'powiat', 'gmina', 'telefon', 'email', 'adres_www', 'numer_zezwolenia',
            'organ_wydajacy', 'data_wydania_zezwolenia', 'data_cofniecia_zezwolenia',
            'data_wygaszenia_zezwolenia', 'data_termin_waznosci')


class SkillError(Exception):
    def __init__(self, message, kind='validation_error', code=64, **details):
        super().__init__(message)
        self.kind, self.code, self.details = kind, code, details


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def normalize(value):
    text = unicodedata.normalize('NFKD', value.casefold().replace('ł', 'l'))
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).split())


def phrase(value):
    value = value.strip()
    if not 2 <= len(value) <= 150 or not normalize(value) or any(ord(c) < 32 for c in value):
        raise argparse.ArgumentTypeError('Use 2..150 characters without control characters.')
    return value


def positive(value):
    if not re.fullmatch(r'[0-9]{1,5}', value) or not 1 <= int(value) <= 10000:
        raise argparse.ArgumentTypeError('Expected 1..10000.')
    return int(value)


def identifier(value):
    if not re.fullmatch(r'[0-9]{1,20}', value):
        raise argparse.ArgumentTypeError('Use the exact pharmacy identifier from search results.')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SkillError('Export redirected; verify the official source before retrying.', 'upstream_redirect', 69)


def load(path=None):
    """Honor no-store: no automatic persistent HTTP cache or query history."""
    if path is not None:
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        filename, retrieved, origin = path.name, None, 'local_file'
    else:
        request = urllib.request.Request(SOURCE, headers={
            'User-Agent': 'ai-polish-skills/apteki-1.0 (+https://github.com/b44x/ai-polish-skills)',
            'Accept': 'text/csv', 'Accept-Encoding': 'identity'})
        start = time.monotonic()
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
                if response.geturl() != SOURCE or response.headers.get('Content-Encoding', 'identity') != 'identity':
                    raise SkillError('Unexpected source or encoding.', 'upstream_format', 69)
                chunks, size = [], 0
                while True:
                    if time.monotonic() - start > 120:
                        raise SkillError('Export exceeded its download budget.', 'network_timeout', 69)
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise SkillError('Export exceeds 40 MiB.', 'response_too_large', 69)
                    chunks.append(chunk)
                raw = b''.join(chunks)
                length = response.headers.get('Content-Length')
                if length is not None and (not length.isdigit() or int(length) != len(raw)):
                    raise SkillError('Incomplete export.', 'upstream_format', 69)
                filename = response.headers.get('Content-Disposition', '')
            retrieved, origin = datetime.now(timezone.utc).isoformat(), 'official_download'
        except urllib.error.HTTPError as exc:
            status, retry = exc.code, exc.headers.get('Retry-After') if exc.headers else None
            exc.close()
            raise SkillError('CeZ HTTP %s.' % status, 'rate_limit' if status == 429 else 'upstream_error',
                             69, retry_after=retry)
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            raise SkillError('Could not download the CeZ export.', 'network_error', 69) from exc
    if len(raw) > MAX_BYTES:
        raise SkillError('Export exceeds 40 MiB.', 'response_too_large', 69)
    match = re.search(r'Rejestr_Aptek_stan_na_dzien_([0-9]{4}-[0-9]{2}-[0-9]{2})\.csv', filename)
    source_date = match.group(1) if match else None
    if source_date:
        date.fromisoformat(source_date)
    meta = dict(source_url=SOURCE if path is None else None, origin=origin,
                source_as_of=source_date, source_date_basis='export_filename' if source_date else None,
                retrieved_at=retrieved, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                local_file_verified=False if path else None)
    return raw, meta


def parse(raw):
    try:
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')), delimiter='|', strict=True)
        fields = reader.fieldnames
        if not fields or len(set(fields)) != len(fields) or not set(REQUIRED).issubset(fields):
            raise ValueError('Unexpected CSV header')
        rows, seen = [], set()
        for row in reader:
            if None in row or any(value is None or len(value) > 50000 for value in row.values()):
                raise ValueError('Malformed CSV row')
            key = row['identyfikator_apteki']
            if not re.fullmatch(r'[0-9]{1,20}', key):
                raise ValueError('Invalid pharmacy ID')
            if key in seen:
                raise ValueError('Duplicate pharmacy ID')
            seen.add(key)
            if not row['stan_apteki'] or not row['rodzaj_apteki']:
                raise ValueError('Missing classification')
            rows.append(row)
            if len(rows) > MAX_ROWS:
                raise ValueError('Too many records')
        if not rows:
            raise ValueError('Empty export')
        return rows
    except (UnicodeError, csv.Error, ValueError) as exc:
        raise SkillError('Unsupported or incomplete CeZ CSV: ' + str(exc), 'upstream_format', 69)


def present(row):
    def value(key):
        return row.get(key, '').strip() or None
    return dict(id=row['identyfikator_apteki'], name=value('nazwa_apteki'),
                registry_status=value('stan_apteki'), pharmacy_type=value('rodzaj_apteki'),
                address={key: value(key) for key in ('wojewodztwo', 'powiat', 'gmina', 'miejscowosc',
                         'typ_ulicy', 'nazwa_ulicy', 'numer_budynku', 'numer_lokalu', 'kod_pocztowy')},
                contact={key: value(key) for key in ('telefon', 'email', 'adres_www')},
                authorization={key: value(key) for key in ('numer_zezwolenia', 'organ_wydajacy',
                    'data_wydania_zezwolenia', 'data_cofniecia_zezwolenia', 'data_wygaszenia_zezwolenia',
                    'data_termin_waznosci')},
                opening_hours_reported={key[len('godziny_otwarcia_'):]: value(key)
                    for key in row if key.startswith('godziny_otwarcia_')},
                open_now_assessed=False, medicine_stock_assessed=False)


def lookup(rows, args):
    if args.command == 'get':
        matches = [row for row in rows if row['identyfikator_apteki'] == args.id]
    else:
        matches = []
        for row in rows:
            if args.status == 'active' and row['stan_apteki'] != 'AKTYWNA':
                continue
            if args.kind == 'public' and row['rodzaj_apteki'] not in PUBLIC_TYPES:
                continue
            if args.city and normalize(row['miejscowosc']) != normalize(args.city):
                continue
            if args.province and normalize(row['wojewodztwo']) != normalize(args.province):
                continue
            if args.street and normalize(args.street) not in normalize(row['nazwa_ulicy']):
                continue
            if args.name and normalize(args.name) not in normalize(row['nazwa_apteki']):
                continue
            matches.append(row)
    matches.sort(key=lambda r: (normalize(r['miejscowosc']), normalize(r['nazwa_ulicy']), r['identyfikator_apteki']))
    offset = (args.page - 1) * args.limit
    selected = matches[offset:offset + args.limit]
    if not selected:
        raise SkillError('No matches on this page in the selected export and scope.', 'not_found', 2)
    return dict(items=[present(row) for row in selected], total=len(matches), page=args.page,
                per_page=args.limit, has_more=offset + args.limit < len(matches),
                next_page=args.page + 1 if offset + args.limit < len(matches) else None)


def main(argv=None):
    try:
        parser = Parser(description='Find pharmacy records in the official CeZ public CSV export.')
        parser.add_argument('--file', type=Path, help='Read a supplied CSV offline; file origin is not authenticated.')
        sub = parser.add_subparsers(dest='command', required=True)
        search = sub.add_parser('search', help='Search active community pharmacies and pharmacy points by default.')
        for key in ('city', 'province', 'street', 'name'):
            search.add_argument('--' + key, type=phrase)
        search.add_argument('--status', choices=('active', 'all'), default='active')
        search.add_argument('--kind', choices=('public', 'all'), default='public')
        get = sub.add_parser('get', help='Read an exact registry ID, including inactive or hospital records.')
        get.add_argument('id', type=identifier)
        for command in (search, get):
            command.add_argument('--page', type=positive, default=1)
            command.add_argument('--limit', type=positive, default=10)
        args = parser.parse_args(argv)
        if args.limit > 50:
            raise SkillError('--limit must be 1..50.')
        if args.command == 'search' and not (args.city or args.name or args.street):
            raise SkillError('Supply --city, --street or --name to bound the search.')
        raw, snapshot = load(args.file)
        rows = parse(raw)
        result = lookup(rows, args)
        if args.command == 'search':
            result['filters'] = {key: getattr(args, key) for key in ('city', 'province', 'street', 'name', 'status', 'kind')}
        print(json.dumps(dict(source='Rejestr Aptek / Centrum e-Zdrowia, WIF', source_homepage=HOME,
                              snapshot=snapshot, result=result,
                              notice='Status rejestru i zgłoszone godziny nie potwierdzają otwarcia teraz, dyżuru ani dostępności leków.'),
                         ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        error, code = dict(error=str(exc), type=exc.kind, **exc.details), exc.code
    except (OSError, ValueError) as exc:
        error, code = dict(error='Could not read the export.', type='source_error', cause=type(exc).__name__), 69
    print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
    return code


if __name__ == '__main__':
    sys.exit(main())
