#!/usr/bin/env python3
"""Developer asking-price observations from dane.gov.pl; Python 3.8+, no pip."""
import argparse
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import http.client
import io
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://api.dane.gov.pl/1.4/"
MAX_METADATA = 2 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_OBSERVATIONS = 200000
SS = "{urn:schemas-microsoft-com:office:spreadsheet}"


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64, **details):
        super().__init__(message)
        self.kind, self.code, self.details = kind, code, details


def malformed(message="Nieobsługiwany lub nieprawidłowy format danych."):
    raise SkillError(message, "upstream_format", 69)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def integer(low, high):
    def parse(value):
        if not re.fullmatch(r"[0-9]+", value) or not low <= int(value) <= high:
            raise argparse.ArgumentTypeError("Podaj liczbę z zakresu %s..%s." % (low, high))
        return int(value)
    return parse


def phrase(value):
    value = value.strip()
    if not 1 <= len(value) <= 300 or any(ord(c) < 32 for c in value):
        raise argparse.ArgumentTypeError("Podaj 1..300 znaków bez znaków sterujących.")
    return value


def trusted_url(url):
    try:
        parts = urllib.parse.urlsplit(url)
        decoded_path = urllib.parse.unquote(parts.path)
        valid = (parts.scheme == "https" and parts.hostname == "api.dane.gov.pl"
                 and parts.port in (None, 443) and not parts.username and not parts.password
                 and not parts.fragment and not any(ord(c) < 32 for c in url)
                 and ".." not in decoded_path.split("/")
                 and parts.path.startswith(("/1.4/", "/media/resources/")))
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise SkillError("Plik lub przekierowanie poza obsługiwanym hostem dane.gov.pl.",
                         "unsupported_source", 69)
    return url


class TrustedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        trusted_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(TrustedRedirect())


def fetch_bytes(url, limit):
    trusted_url(url)
    request = urllib.request.Request(url, headers={
        "User-Agent": "ai-polish-skills/1.0 (+https://github.com/b44x/ai-polish-skills)",
        "Accept": "application/json,text/csv,application/xml", "Accept-Encoding": "identity"})
    try:
        with OPENER.open(request, timeout=20) as response:
            trusted_url(response.geturl())
            raw = response.read(limit + 1)
        if len(raw) > limit:
            raise SkillError("Odpowiedź przekracza limit rozmiaru.", "response_too_large", 69)
        return raw
    except urllib.error.HTTPError as exc:
        status = exc.code
        retry = exc.headers.get("Retry-After") if exc.headers else None
        exc.close()
        raise SkillError("Źródło zwróciło HTTP %s." % status,
                         "not_found" if status == 404 else "rate_limit" if status == 429 else "upstream_error",
                         2 if status == 404 else 69, http_status=status, retry_after=retry)
    except (urllib.error.URLError, OSError, http.client.HTTPException):
        raise SkillError("Nie udało się pobrać danych; spróbuj później.", "network_error", 69)


def reject_constant(value):
    raise ValueError("Non-finite JSON")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def decode_json(raw):
    try:
        return json.loads(raw.decode("utf-8-sig"), parse_float=Decimal,
                          parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, RecursionError, InvalidOperation):
        malformed()


def fetch_json(url):
    return decode_json(fetch_bytes(url, MAX_METADATA))


def validate_record(value, kind, identifier=None):
    if (not isinstance(value, dict) or value.get("type") != kind
            or not isinstance(value.get("id"), str) or not value["id"].isdigit()
            or not isinstance(value.get("attributes"), dict)
            or not isinstance(value["attributes"].get("title"), str)):
        malformed()
    if identifier is not None and value["id"] != str(identifier):
        malformed("API zwróciło inny identyfikator zasobu.")
    return value


def get_record(kind, identifier):
    data = fetch_json(BASE + kind + "s/" + str(identifier))
    if not isinstance(data, dict):
        malformed()
    return validate_record(data.get("data"), kind, identifier)


def related_id(record, relation):
    relationships = record.get("relationships")
    if not isinstance(relationships, dict) or not isinstance(relationships.get(relation), dict):
        malformed("Brak relacji zbioru lub wydawcy.")
    value = relationships[relation].get("data")
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) or not value["id"].isdigit():
        malformed("Brak tożsamości zbioru lub wydawcy.")
    return value["id"]


def brief(record):
    a = record["attributes"]
    return dict(id=record["id"], title=a["title"], format=a.get("format"),
                catalog_data_date=a.get("data_date"), file_url=a.get("file_url"),
                publisher_url=a.get("link"), modified=a.get("modified"))


def catalogue(command, args):
    path = "datasets" if command == "search" else "datasets/%s/resources" % args.id
    params = {"page": args.page, "per_page": args.limit}
    params.update({"q": args.query} if command == "search" else {"sort": "-data_date"})
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    body = fetch_json(url)
    if not isinstance(body, dict):
        malformed()
    rows, meta = body.get("data"), body.get("meta")
    if not isinstance(rows, list) or not isinstance(meta, dict):
        malformed()
    total = meta.get("count")
    if type(total) is not int or total < 0 or len(rows) > args.limit or len(rows) > total:
        malformed()
    kind = "dataset" if command == "search" else "resource"
    rows = [brief(validate_record(row, kind)) for row in rows]
    if len({row['id'] for row in rows}) != len(rows):
        malformed()
    more = args.page * args.limit < total
    if more and len(rows) != args.limit:
        malformed()
    if not rows:
        raise SkillError("Brak wyników na tej stronie.", "not_found", 2)
    return dict(items=rows, total=total, page=args.page, per_page=args.limit,
                next_page=args.page + 1 if more else None, has_more=more,
                source_url=url, candidates_only=True)


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}[-.]\d{2}[-.]\d{2}", value):
        malformed("Nieprawidłowa data obserwacji.")
    try:
        return date.fromisoformat(value.replace(".", "-")).isoformat()
    except ValueError:
        malformed("Nieprawidłowa data obserwacji.")


def number(value, positive=False):
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        malformed("Nieprawidłowa liczba w cenniku.")
    try:
        if isinstance(value, str) and not re.fullmatch(r"\d+(?:[.,]\d+)?", value.strip()):
            malformed("Niejednoznaczny zapis liczby w cenniku.")
        result = Decimal(str(value).strip().replace(",", "."))
        if not result.is_finite() or result < 0 or result > Decimal("1000000000000") or (positive and result == 0):
            malformed("Liczba poza dopuszczalnym zakresem.")
        if result.as_tuple().exponent < -8:
            malformed("Nadmierna precyzja liczby w cenniku.")
        return result
    except InvalidOperation:
        malformed("Nieprawidłowa liczba w cenniku.")


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 1000 or any(ord(c) < 32 for c in value):
        malformed("Nieprawidłowy identyfikator lub opis lokalu.")
    return value.strip()


def compound(*parts):
    parts = [text(part) for part in parts]
    if any("::" in part for part in parts):
        malformed("Niejednoznaczne oznaczenie lokalu.")
    return "::".join(parts)


def observation(unit, observed, basis, total, sqm, area=None, status=None, **extra):
    total, sqm = number(total), number(sqm)
    return dict(unit_id=text(unit), observed_on=day(observed), date_basis=basis,
                price_total_pln=total if total else None, price_sqm_pln=sqm if sqm else None,
                zero_price_reported=total == 0 or sqm == 0, area_m2=number(area, positive=True),
                status=status, **extra)


def dated_json(raw, metadata):
    data = decode_json(raw)
    if not isinstance(data, dict) or not data:
        malformed()
    observations, dates = [], set()
    for date_key, units in data.items():
        observed = day(date_key)
        if observed in dates or not isinstance(units, dict):
            malformed()
        dates.add(observed)
        for code, row in units.items():
            if not isinstance(row, dict) or not {"Symbol", "Nazwa", "PowU", "Brutto", "CenaM2"} <= row.keys():
                malformed("Nieobsługiwany schemat JSON cennika.")
            if code != row["Symbol"]:
                malformed("Symbol lokalu nie odpowiada kluczowi JSON.")
            observations.append(observation(code, observed, "file_snapshot_date", row["Brutto"],
                                            row["CenaM2"], row["PowU"], kind=text(row["Nazwa"])))
            if len(observations) > MAX_OBSERVATIONS:
                malformed("Za dużo obserwacji w pliku.")
    return "dated-json", observations, dates


def normalize_header(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def csv_rows(raw):
    try:
        content = raw.decode("utf-8-sig")
        dialect = csv.Sniffer().sniff(content[:12000], delimiters=",;")
        reader = csv.DictReader(io.StringIO(content), dialect=dialect)
        headers = reader.fieldnames
        if not headers or len(set(headers)) != len(headers):
            malformed("Brak lub powtórzone nagłówki CSV.")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                malformed("Niezgodna liczba kolumn CSV.")
            rows.append(row)
            if len(rows) > MAX_OBSERVATIONS:
                malformed("Za dużo wierszy CSV.")
        return headers, rows
    except (UnicodeError, csv.Error):
        malformed("Nieprawidłowy plik CSV UTF-8.")


def parse_csv(raw, metadata):
    headers, rows = csv_rows(raw)
    required = {"nazwa_inwestycji", "budynek", "numer_lokalu", "typ_obiektu", "area_usable_m2",
                "price_sqm_gross_pln", "price_total_gross_pln", "currency", "snapshot_date"}
    observations, dates = [], set()
    if required <= set(headers):
        for row in rows:
            if row["currency"] != "PLN":
                malformed("CSV zawiera walutę inną niż PLN.")
            unit = compound(row['nazwa_inwestycji'], row['budynek'], row['typ_obiektu'], row['numer_lokalu'])
            observed = day(row['snapshot_date'])
            dates.add(observed)
            observations.append(observation(unit, observed, "file_snapshot_date", row['price_total_gross_pln'],
                                            row['price_sqm_gross_pln'], row['area_usable_m2'],
                                            row.get('status_norm') or row.get('status_name'),
                                            kind=text(row['typ_obiektu'])))
        return "snapshot-csv", observations, dates
    prefixes = {
        "unit": "Nr lokalu lub domu jednorodzinnego nadany przez dewelopera",
        "locality": "Miejscowość lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego",
        "street": "Ulica lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego",
        "building": "Nr nieruchomości lokalizacji przedsięwzięcia deweloperskiego lub zadania inwestycyjnego",
        "kind": "Rodzaj nieruchomości:", "sqm": "Cena m 2 powierzchni użytkowej",
        "total": "Cena lokalu mieszkalnego lub domu jednorodzinnego będących",
        "effective": "Data od której cena obowiązuje cena lokalu mieszkalnego lub",
    }
    columns = {}
    for key, prefix in prefixes.items():
        matches = [h for h in headers if normalize_header(h).startswith(normalize_header(prefix))]
        if len(matches) != 1:
            malformed("Nieobsługiwany schemat kolumn CSV.")
        columns[key] = matches[0]
    observed = day(metadata['catalog_data_date'])
    dates.add(observed)
    metadata['excluded_rows_without_residential_identifier'] = 0
    for row in rows:
        if not row[columns['unit']].strip() and normalize_header(row[columns['kind']]) in ('x', ''):
            metadata['excluded_rows_without_residential_identifier'] += 1
            continue
        unit = compound(row[columns['locality']], row[columns['street']] or '(bez ulicy)',
                        row[columns['building']], row[columns['unit']])
        effective = row[columns['effective']].strip()
        observations.append(observation(unit, observed, 'catalog_data_date', row[columns['total']],
                                        row[columns['sqm']], kind=text(row[columns['kind']]),
                                        price_effective_from=day(effective) if effective else None))
    return "disclosure-csv", observations, dates


def spreadsheet_xml(raw, metadata):
    try:
        content = raw.decode('utf-8-sig')
        if re.search(r'<!\s*(?:DOCTYPE|ENTITY)', content, re.I):
            malformed("Deklaracje DTD i encji XML nie są obsługiwane.")
        root = ET.fromstring(content)
    except (UnicodeError, ET.ParseError, RecursionError):
        malformed("Nieprawidłowy XML UTF-8.")
    sheets = root.findall(SS + 'Worksheet')
    if root.tag != SS + 'Workbook' or len(sheets) != 1:
        malformed("Obsługiwany XML to jeden arkusz SpreadsheetML z kolumnami cen.")
    table = sheets[0].find(SS + 'Table')
    if table is None:
        malformed()
    rows = []
    for row in table.findall(SS + 'Row'):
        values = []
        for cell in row.findall(SS + 'Cell'):
            index = cell.get(SS + 'Index')
            if index is not None:
                if not index.isdigit() or not len(values) < int(index) <= 100:
                    malformed()
                values.extend([''] * (int(index) - len(values) - 1))
            data = cell.find(SS + 'Data')
            values.append(data.text or '' if data is not None else '')
        while values and not values[-1]:
            values.pop()
        if values:
            rows.append(values)
        if len(rows) > MAX_OBSERVATIONS + 1:
            malformed()
    expected = ['Inwestycja', 'Numer', 'Typ', 'Powierzchnia rozliczeniowa',
                'Cena ofertowa brutto', 'cena brutto m2']
    if not rows or rows[0] != expected:
        malformed("Nieobsługiwane kolumny arkusza XML.")
    observed = day(metadata['catalog_data_date'])
    observations = []
    for row in rows[1:]:
        if not 4 <= len(row) <= 6:
            malformed()
        row += [''] * (6 - len(row))
        observations.append(observation(compound(row[0], row[1]), observed, 'catalog_data_date',
                                        row[4], row[5], row[3], kind=text(row[2])))
    return 'spreadsheet-xml', observations, {observed}


def load_resource(identifier):
    resource = get_record('resource', identifier)
    dataset_id, institution_id = related_id(resource, 'dataset'), related_id(resource, 'institution')
    dataset = get_record('dataset', dataset_id)
    meta = dict(brief(resource), dataset_id=dataset_id, institution_id=institution_id,
                dataset_title=dataset['attributes']['title'],
                source_url=BASE + 'resources/' + str(identifier),
                reuse_conditions={key: value for key, value in dataset['attributes'].items()
                                  if key.startswith('license') or key == 'terms'})
    url = meta['file_url']
    if not isinstance(url, str) or not url:
        raise SkillError('Brak kopii pliku na api.dane.gov.pl; zewnętrznych stron nie pobieramy.',
                         'unsupported_source', 69)
    trusted_url(url)
    if not urllib.parse.urlsplit(url).path.startswith('/media/resources/'):
        raise SkillError('Zasób nie wskazuje kopii pliku w katalogu.', 'unsupported_source', 69)
    parser = {'json': dated_json, 'csv': parse_csv, 'xml': spreadsheet_xml}.get(str(meta['format']).lower())
    if parser is None:
        raise SkillError('Obsługiwane pliki: rozpoznane schematy JSON, CSV i SpreadsheetML XML.',
                         'unsupported_format', 69)
    raw = fetch_bytes(url, MAX_FILE)
    profile, rows, dates = parser(raw, meta)
    if not rows:
        raise SkillError('Cennik nie zawiera obserwacji.', 'not_found', 2)
    seen = set()
    for row in rows:
        identity = (row['unit_id'], row['observed_on'])
        if identity in seen:
            malformed('Powtórzone oznaczenie lokalu w tym samym dniu.')
        seen.add(identity)
    meta.update(profile=profile, sha256=hashlib.sha256(raw).hexdigest(),
                first_snapshot=min(dates), last_snapshot=max(dates), snapshot_count=len(dates),
                observation_count=len(rows))
    return meta, rows, dates


def units(meta, rows, args):
    selected = [row for row in rows if row['observed_on'] == meta['last_snapshot']]
    if args.query:
        selected = [row for row in selected if args.query.casefold() in row['unit_id'].casefold()]
    selected.sort(key=lambda row: row['unit_id'])
    start = (args.page - 1) * args.limit
    page = selected[start:start + args.limit]
    if not page:
        raise SkillError('Brak lokali na tej stronie ostatniego snapshotu.', 'not_found', 2)
    more = start + len(page) < len(selected)
    return dict(items=page, total=len(selected), page=args.page, per_page=args.limit,
                has_more=more, next_page=args.page + 1 if more else None, observed_on=meta['last_snapshot'])


def delta(old, new):
    if old is None or new is None or old == 0:
        return None
    return dict(pln=(new - old).quantize(Decimal('.01'), rounding=ROUND_HALF_UP),
                percent=((new - old) * 100 / old).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def history(loaded, unit):
    metas = [part[0] for part in loaded]
    if len({(m['dataset_id'], m['institution_id'], m['profile']) for m in metas}) != 1:
        raise SkillError('Łącz tylko zasoby tego samego zbioru, wydawcy i schematu.', 'incomparable_sources', 64)
    by_date, all_dates = {}, set()
    for meta, rows, dates in loaded:
        all_dates.update(dates)
        for row in rows:
            if row['unit_id'] != unit:
                continue
            observed = row['observed_on']
            if observed in by_date and by_date[observed]['value'] != row:
                malformed('Sprzeczne obserwacje tego lokalu z tego samego dnia.')
            entry = by_date.setdefault(observed, {'value': row, 'resource_ids': []})
            entry['resource_ids'].append(meta['id'])
    if not by_date:
        raise SkillError('Nie znaleziono dokładnego oznaczenia lokalu; użyj units.', 'not_found', 2)
    ordered = [by_date[key] for key in sorted(by_date)]
    areas = {entry['value']['area_m2'] for entry in ordered if entry['value']['area_m2'] is not None}
    consistent_area = len(areas) <= 1
    area_known = all(entry['value']['area_m2'] is not None for entry in ordered)
    same_kind = len({entry['value']['kind'] for entry in ordered}) == 1
    comparable = consistent_area and same_kind
    points, gaps = [], []
    previous, signature = None, None
    fields = ['price_total_pln', 'price_sqm_pln', 'area_m2', 'status', 'kind', 'zero_price_reported', 'date_basis', 'price_effective_from']
    for entry in ordered:
        row = entry['value']
        current = tuple(row.get(key) for key in fields)
        observed = row['observed_on']
        gap = (date.fromisoformat(observed) - date.fromisoformat(previous['observed_on'])).days if previous else 0
        if gap > 1:
            gaps.append(dict(after=previous['observed_on'], before=observed, unobserved_days=gap - 1))
        if current != signature:
            point = {key: row[key] for key in fields if key in row}
            point.update(first_observed=observed, last_observed=observed, samples=1,
                         resource_ids=list(entry['resource_ids']),
                         change_from_previous=delta(previous['price_total_pln'], row['price_total_pln'])
                         if previous and comparable else None)
            points.append(point)
            signature = current
        else:
            points[-1]['last_observed'] = observed
            points[-1]['samples'] += 1
            points[-1]['resource_ids'] = sorted(set(points[-1]['resource_ids'] + entry['resource_ids']))
        previous = row
    first, last = ordered[0]['value'], ordered[-1]['value']
    prices = [entry['value']['price_total_pln'] for entry in ordered if entry['value']['price_total_pln'] is not None]
    return dict(unit_id=unit, currency='PLN', observations=len(ordered), price_points=points,
                first_observed=first['observed_on'], last_observed=last['observed_on'],
                present_in_latest_snapshot=last['observed_on'] == max(all_dates),
                absent_on_snapshot_dates=len(all_dates - set(by_date)), calendar_gaps=gaps,
                last_date_basis=last['date_basis'],
                age_of_reported_date_days=(datetime.now(timezone.utc).date() - date.fromisoformat(last['observed_on'])).days,
                area_consistent=False if not consistent_area else True if area_known else None,
                kind_consistent=same_kind,
                first_to_last_change=delta(first['price_total_pln'], last['price_total_pln']) if comparable and len(ordered) > 1 else None,
                lowest_observed_pln=min(prices) if prices and comparable else None,
                highest_observed_pln=max(prices) if prices and comparable else None,
                complete_history=None, asking_prices_only=True, total_includes_additional_costs=None)


def decimal_json(value):
    if isinstance(value, Decimal):
        return format(value, 'f')
    raise TypeError(type(value).__name__)


def main(argv=None):
    try:
        parser = Parser(description='Historia cen ofertowych deweloperów z plików dane.gov.pl.')
        sub = parser.add_subparsers(dest='command', required=True)
        search = sub.add_parser('search', help='Znajdź kandydatów na zbiory po nazwie inwestycji lub wydawcy.')
        search.add_argument('query', type=phrase)
        resources = sub.add_parser('resources', help='Wyświetl jedną stronę zasobów zbioru.')
        resources.add_argument('id', type=integer(1, 2147483647))
        items = sub.add_parser('units', help='Oznaczenia i ceny lokali w ostatnim snapshotcie pliku.')
        items.add_argument('id', type=integer(1, 2147483647))
        items.add_argument('--query', type=phrase)
        for command in (search, resources, items):
            command.add_argument('--page', type=integer(1, 1000000), default=1)
            command.add_argument('--limit', type=integer(1, 100), default=10)
        hist = sub.add_parser('history', help='Historia jednego oznaczenia lokalu; opcjonalnie połącz do trzech zasobów.')
        hist.add_argument('id', type=integer(1, 2147483647))
        hist.add_argument('unit', type=phrase)
        hist.add_argument('--with-resource', type=integer(1, 2147483647), action='append', default=[])
        args = parser.parse_args(argv)
        if args.command in ('search', 'resources'):
            sources, result = [], catalogue(args.command, args)
        else:
            identifiers = [args.id] + (args.with_resource if args.command == 'history' else [])
            if len(identifiers) > 3 or len(set(identifiers)) != len(identifiers):
                raise SkillError('Podaj najwyżej trzy różne zasoby.')
            loaded = [load_resource(identifier) for identifier in identifiers]
            sources = [part[0] for part in loaded]
            result = units(*loaded[0][:2], args) if args.command == 'units' else history(loaded, args.unit)
        print(json.dumps(dict(source='dane.gov.pl / dane wydawców',
                              fetched_at=datetime.now(timezone.utc).isoformat(), sources=sources, result=result),
                         ensure_ascii=False, allow_nan=False, default=decimal_json))
        return 0
    except SkillError as exc:
        print(json.dumps(dict(error=str(exc), type=exc.kind, **exc.details), ensure_ascii=False), file=sys.stderr)
        return exc.code


if __name__ == '__main__':
    sys.exit(main())
