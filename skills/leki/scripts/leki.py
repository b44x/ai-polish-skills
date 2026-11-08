#!/usr/bin/env python3
"""Official Polish RPL export lookup. Python 3.8+, standard library only."""
import argparse
import codecs
from contextlib import contextmanager, closing
from datetime import date, datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SOURCE = 'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/public-pl-report/6.0.0/overall.xml'
HOMEPAGE = 'https://rejestry.ezdrowie.gov.pl/rpl/search/public'
NS = '{http://rejestry.ezdrowie.gov.pl/rpl/eksport-danych-v6.0.0}'
CACHE_VERSION = 1
MAX_BYTES = 128 * 1024 * 1024
MAX_PRODUCTS = 100000
MAX_PACKAGES = 1000000
MAX_PRODUCT_BYTES = 2 * 1024 * 1024
MAX_SECONDS = 120
MAX_CACHE_AGE = 24 * 3600
DOC_FIELDS = ('ulotka', 'charakterystyka', 'etykietoUlotka', 'ulotkaImportRownolegly',
              'etykietoUlotkaImportRownolegly', 'oznaczenieOpakowanImportRownolegly')
KINDS = {'human': 'ludzki', 'veterinary': 'weterynaryjny'}


class SkillError(Exception):
    def __init__(self, message, kind='validation_error', code=64, **details):
        super().__init__(message)
        self.kind, self.code, self.details = kind, code, details


def malformed(message):
    raise SkillError(message, 'upstream_format', 69)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def bounded_integer(low, high):
    def parse(value):
        if (len(value) > 10 or not re.fullmatch(r'[0-9]+', value)
                or not low <= int(value) <= high):
            raise argparse.ArgumentTypeError('Expected an integer in %s..%s.' % (low, high))
        return int(value)
    return parse


def identifier(value):
    if not re.fullmatch(r'[0-9]{1,20}', value):
        raise argparse.ArgumentTypeError('Use the exact numeric ID returned by the registry.')
    return value


def query(value):
    value = value.strip()
    if not 2 <= len(value) <= 150 or any(ord(c) < 32 for c in value) or not normalize(value):
        raise argparse.ArgumentTypeError('Use 2..150 characters without control characters.')
    return value


def normalize(value):
    value = unicodedata.normalize('NFKD', value.casefold().replace('ł', 'l'))
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).split())


def gtin(value):
    if not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})', value):
        raise argparse.ArgumentTypeError('GTIN must contain 8, 12, 13 or 14 digits.')
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(value[:-1])))
    if (10 - total % 10) % 10 != int(value[-1]):
        raise argparse.ArgumentTypeError('Invalid GTIN check digit.')
    return value.zfill(14)


def trusted_url(url):
    try:
        p = urllib.parse.urlsplit(url)
        good = (p.scheme == 'https' and p.hostname == 'rejestry.ezdrowie.gov.pl'
                and p.port in (None, 443) and not p.username and not p.password
                and not p.query and not p.fragment and not any(ord(c) < 33 for c in url)
                and p.path.startswith('/api/rpl/medicinal-products/')
                and '..' not in urllib.parse.unquote(p.path).split('/'))
    except (TypeError, ValueError):
        good = False
    if not good:
        raise SkillError('Unsupported source URL or redirect.', 'unsupported_source', 69)
    return url


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        trusted_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(Redirect())


def network_io(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except urllib.error.HTTPError as exc:
        status = exc.code
        retry = exc.headers.get('Retry-After') if exc.headers else None
        exc.close()
        raise SkillError('RPL returned HTTP %s.' % status, 'rate_limit' if status == 429 else 'upstream_error',
                         69, http_status=status, retry_after=retry)
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        raise SkillError('Could not retrieve RPL; retry later or explicitly use --offline.', 'network_error', 69) from exc


def download(target):
    """One bounded GET; no user query, retry, cookies or document downloads."""
    request = urllib.request.Request(SOURCE, headers={
        'User-Agent': 'ai-polish-skills/leki-1.0 (+https://github.com/b44x/ai-polish-skills)',
        'Accept': 'application/xml', 'Accept-Encoding': 'identity'})
    start, size, digest = time.monotonic(), 0, hashlib.sha256()
    with target.open('wb') as output:
        with network_io(OPENER.open, request, timeout=30) as response:
            trusted_url(response.geturl())
            if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                malformed('Compressed HTTP response is unsupported.')
            length = response.headers.get('Content-Length')
            if length is not None and (not re.fullmatch(r'[0-9]{1,12}', length) or int(length) > MAX_BYTES):
                raise SkillError('Export exceeds the download limit.', 'response_too_large', 69)
            while True:
                if time.monotonic() - start > MAX_SECONDS:
                    raise SkillError('Export download exceeded its time budget.', 'network_timeout', 69)
                chunk = network_io(response.read, 65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise SkillError('Export exceeds the download limit.', 'response_too_large', 69)
                output.write(chunk)
                digest.update(chunk)
            if length is not None and size != int(length):
                malformed('Incomplete export download.')
    return {'source_url': SOURCE, 'sha256': digest.hexdigest(), 'download_bytes': size,
            'retrieved_at': datetime.now(timezone.utc).isoformat()}


class CheckedXML:
    """Streaming UTF-8 and DTD checks before bytes reach ElementTree."""
    def __init__(self, stream):
        self.stream, self.tail, self.size = stream, '', 0
        self.decoder = codecs.getincrementaldecoder('utf-8-sig')('strict')

    def read(self, size=-1):
        raw = self.stream.read(65536 if size < 0 else min(size, 65536))
        self.size += len(raw)
        if self.size > MAX_BYTES:
            raise SkillError('Export exceeds the parser limit.', 'response_too_large', 69)
        decoded = self.decoder.decode(raw, final=not raw)
        text = self.tail + decoded
        if '\x00' in text or re.search(r'<!DOCTYPE|<!ENTITY', text, re.I):
            malformed('Only UTF-8 XML without DTD/entity declarations is supported.')
        self.tail = text[-16:]
        return raw


def field(value, required=False):
    if value is None or not value.strip():
        if required:
            malformed('Required registry field is missing.')
        return None
    value = value.strip()
    if len(value) > 10000 or any(ord(c) < 32 and c not in '\t\n\r' for c in value):
        malformed('Invalid registry field.')
    return value


def source_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,20}', value):
        malformed('Invalid registry identifier.')
    return value


def parse_product(node):
    for container in ('substancjeCzynne', 'opakowania', 'kodyATC', 'drogiPodania'):
        if len(node.findall(NS + container)) != 1:
            malformed('Missing or duplicate product section: ' + container)
    a = node.attrib
    product_id = source_id(a.get('id'))
    kind = field(a.get('rodzajPreparatu'), True)
    if kind not in KINDS.values():
        malformed('Unknown human/veterinary classification.')
    documents = {}
    for key in DOC_FIELDS:
        value = field(a.get(key))
        documents[key] = trusted_url(value) if value else None
    substances = []
    for item in node.findall(NS + 'substancjeCzynne/' + NS + 'substancjaCzynna'):
        substances.append(dict(name=field(item.get('nazwaSubstancji'), True),
                               amount=field(item.get('iloscSubstancji')),
                               amount_unit=field(item.get('jednostkaMiaryIlosciSubstancji')),
                               preparation_amount=field(item.get('iloscPreparatu')),
                               preparation_unit=field(item.get('jednostkaMiaryIlosciPreparatu')),
                               other_description=field(item.get('innyOpisIlosci'))))
    packages = []
    for item in node.findall(NS + 'opakowania/' + NS + 'opakowanie'):
        raw_gtin = field(item.get('kodGTIN'))
        try:
            canonical = gtin(raw_gtin) if raw_gtin else None
        except argparse.ArgumentTypeError:
            canonical = None
        deleted = field(item.get('skasowane'))
        if deleted not in ('TAK', 'NIE', None):
            malformed('Unknown package deletion marker.')
        package = dict(package_id=source_id(item.get('id')), gtin=raw_gtin, gtin14=canonical,
                       gtin_valid=bool(canonical) if raw_gtin else None,
                       deleted={'TAK': True, 'NIE': False, None: None}[deleted],
                       availability_category=field(item.get('kategoriaDostepnosci')),
                       eu_number=field(item.get('numerEu')),
                       parallel_importer=field(item.get('dystrybutorRownolegly')),
                       units=[{key: field(value) for key, value in unit.attrib.items()}
                              for unit in item.findall(NS + 'jednostkiOpakowania/' + NS + 'jednostkaOpakowania')])
        packages.append(package)
    if len(packages) > 2000 or len(substances) > 200:
        malformed('Excessive product component count.')
    product = dict(id=product_id, name=field(a.get('nazwaProduktu'), True), kind=kind,
                   common_name=field(a.get('nazwaPowszechnieStosowana')),
                   strength=field(a.get('moc')), form=field(a.get('nazwaPostaciFarmaceutycznej')),
                   authorization_holder=field(a.get('podmiotOdpowiedzialny')),
                   authorization_number=field(a.get('numerPozwolenia')),
                   authorization_valid_until=field(a.get('waznoscPozwolenia')),
                   procedure=field(a.get('typProcedury')),
                   atc_codes=[field(e.text, True) for e in node.findall(NS + 'kodyATC/' + NS + 'kodATC')],
                   routes=[field(e.get('drogaPodaniaNazwa'), True) for e in node.findall(NS + 'drogiPodania/' + NS + 'drogaPodania')],
                   substances=substances, documents=documents,
                   package_counts=dict(total=len(packages), not_deleted=sum(p['deleted'] is False for p in packages),
                                       deleted=sum(p['deleted'] is True for p in packages),
                                       unknown=sum(p['deleted'] is None for p in packages)))
    return product, packages


def build_index(xml_path, db_path, metadata):
    counts = dict(products=0, human=0, veterinary=0, packages=0, invalid_gtins=0)
    with closing(sqlite3.connect(str(db_path))) as db:
        db.executescript('''
            CREATE TABLE products (id TEXT PRIMARY KEY, name_key TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE substances (product_id TEXT NOT NULL, name_key TEXT NOT NULL);
            CREATE TABLE packages (product_id TEXT NOT NULL, id TEXT NOT NULL, gtin14 TEXT, deleted INTEGER, data TEXT NOT NULL,
                                   PRIMARY KEY (product_id, id));
            CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
        ''')
        try:
            with xml_path.open('rb') as stream:
                parser = ET.iterparse(CheckedXML(stream), events=('start', 'end'), parser=ET.XMLParser(encoding='utf-8'))
                event, root = next(parser)
                if root.tag != NS + 'produktyLecznicze':
                    malformed('Unsupported RPL XML namespace or root.')
                as_of = root.get('stanNaDzien', '')
                if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', as_of):
                    malformed('Missing registry date.')
                source_day = date.fromisoformat(as_of)
                if (source_day - datetime.now(timezone.utc).date()).days > 1:
                    malformed('Registry date is unexpectedly in the future.')
                depth = 1
                for event, node in parser:
                    if event == 'start':
                        depth += 1
                        if depth > 32:
                            malformed('Excessive XML nesting.')
                        if depth == 2 and node.tag != NS + 'produktLeczniczy':
                            malformed('Unrecognized top-level registry record.')
                        continue
                    if depth == 2:
                        if len(ET.tostring(node, encoding='utf-8')) > MAX_PRODUCT_BYTES:
                            malformed('Product record exceeds its size limit.')
                        product, packages = parse_product(node)
                        counts['products'] += 1
                        counts['human' if product['kind'] == 'ludzki' else 'veterinary'] += 1
                        counts['packages'] += len(packages)
                        counts['invalid_gtins'] += sum(p['gtin_valid'] is False for p in packages)
                        if counts['products'] > MAX_PRODUCTS or counts['packages'] > MAX_PACKAGES:
                            malformed('Registry record limit exceeded.')
                        db.execute('INSERT INTO products VALUES (?,?,?,?)',
                                   (product['id'], normalize(product['name']), product['kind'], json.dumps(product, ensure_ascii=False)))
                        db.executemany('INSERT INTO substances VALUES (?,?)',
                                       [(product['id'], normalize(s['name'])) for s in product['substances']])
                        db.executemany('INSERT INTO packages VALUES (?,?,?,?,?)',
                                       [(product['id'], p['package_id'], p['gtin14'], p['deleted'], json.dumps(p, ensure_ascii=False)) for p in packages])
                        root.clear()
                    depth -= 1
            if not counts['products']:
                malformed('Empty registry export; previous index retained.')
        except (ET.ParseError, UnicodeError, ValueError, StopIteration, RecursionError, sqlite3.IntegrityError) as exc:
            malformed('Malformed, incomplete or duplicate RPL records: %s.' % type(exc).__name__)
        meta = dict(metadata, cache_version=CACHE_VERSION, source_as_of=as_of, counts=counts)
        db.executescript('''
            CREATE INDEX package_gtin ON packages(gtin14);
            CREATE INDEX substance_product ON substances(product_id);
            CREATE INDEX product_name ON products(name_key, id);
        ''')
        db.execute('INSERT INTO metadata VALUES (1,?)', (json.dumps(meta),))
        db.commit()
    return meta


@contextmanager
def read_db(path):
    if not path.is_file():
        raise SkillError('No local registry index. Run refresh while online.', 'cache_missing', 69)
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        yield db


def read_metadata(db):
    try:
        row = db.execute('SELECT data FROM metadata WHERE id=1').fetchone()
        meta = json.loads(row[0])
        if meta['cache_version'] != CACHE_VERSION or meta['source_url'] != SOURCE:
            raise ValueError('version/source')
        date.fromisoformat(meta['source_as_of'])
        fetched = datetime.fromisoformat(meta['retrieved_at'])
        if fetched.tzinfo is None or not re.fullmatch(r'[a-f0-9]{64}', meta['sha256']):
            raise ValueError('provenance')
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        if age < -300:
            raise ValueError('future retrieval time')
        return dict(meta, cache_age_seconds=max(0, int(age)), cache_expired=age >= MAX_CACHE_AGE,
                    source_age_days=(datetime.now(timezone.utc).date() - date.fromisoformat(meta['source_as_of'])).days)
    except (TypeError, KeyError, ValueError, IndexError) as exc:
        raise SkillError('Invalid local index metadata; run refresh.', 'cache_error', 69) from exc


@contextmanager
def update_lock(directory):
    lock = directory / 'refresh.lock'
    try:
        descriptor = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SkillError('Another refresh holds the cache lock; retry after it finishes.', 'cache_busy', 69)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def refresh(directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'registry-v1.sqlite3'
    with update_lock(directory):
        old = None
        if path.exists():
            try:
                with read_db(path) as db:
                    old = read_metadata(db)
            except (SkillError, sqlite3.DatabaseError):
                pass  # Explicit refresh also repairs a corrupt index.
        with tempfile.TemporaryDirectory(prefix='refresh-', dir=str(directory)) as temp:
            xml_path, db_path = Path(temp) / 'rpl.xml', Path(temp) / 'index.sqlite3'
            metadata = download(xml_path)
            new = build_index(xml_path, db_path, metadata)
            if old and new['source_as_of'] < old['source_as_of']:
                raise SkillError('Source date went backwards; previous index retained.', 'source_regression', 69)
            os.replace(str(db_path), str(path))
    return path


def ensure_index(directory, offline):
    path = directory / 'registry-v1.sqlite3'
    if path.exists():
        with read_db(path) as db:
            meta = read_metadata(db)
        if offline or not meta['cache_expired']:
            return path
    if offline:
        raise SkillError('No local index is available offline. Run refresh online.', 'cache_missing', 69)
    return refresh(directory)


def get_product(db, product_id):
    row = db.execute('SELECT data FROM products WHERE id=?', (product_id,)).fetchone()
    if row is None:
        raise SkillError('Product ID not found in this registry snapshot.', 'not_found', 2)
    return json.loads(row[0])


def page_result(items, total, args):
    if not items:
        raise SkillError('No matching entries on this page of the registry snapshot.', 'not_found', 2)
    more = args.page * args.limit < total
    return dict(items=items, total=total, page=args.page, per_page=args.limit,
                has_more=more, next_page=args.page + 1 if more else None)


def lookup(db, args):
    if args.command == 'product':
        return get_product(db, args.id)
    offset = (args.page - 1) * args.limit
    if args.command == 'search':
        value = normalize(args.query)
        if not value:
            raise SkillError('Search query has no searchable characters.')
        column = 'p.name_key' if args.field == 'name' else 's.name_key'
        condition = column + '=?' if args.exact else 'instr(%s,?)>0' % column
        if args.field == 'substance':
            condition = 'EXISTS (SELECT 1 FROM substances s WHERE s.product_id=p.id AND %s)' % condition
        values = [value]
        if args.kind != 'all':
            condition += ' AND p.kind=?'
            values.append(KINDS[args.kind])
        total = db.execute('SELECT COUNT(*) FROM products p WHERE ' + condition, values).fetchone()[0]
        rows = db.execute('SELECT p.data FROM products p WHERE ' + condition + ' ORDER BY p.name_key,p.id LIMIT ? OFFSET ?',
                          values + [args.limit, offset])
        result = page_result([json.loads(row[0]) for row in rows], total, args)
        return dict(result, field=args.field, match='exact' if args.exact else 'substring', kind=args.kind,
                    therapeutic_equivalence_assessed=False)
    if args.command == 'packages':
        product = get_product(db, args.id)
        condition, values = 'p.product_id=?', [args.id]
        if not args.include_deleted:
            condition += ' AND p.deleted=0'
        total = db.execute('SELECT COUNT(*) FROM packages p WHERE ' + condition, values).fetchone()[0]
        rows = db.execute('SELECT p.data FROM packages p WHERE ' + condition + ' ORDER BY p.id LIMIT ? OFFSET ?',
                          values + [args.limit, offset])
        return dict(page_result([json.loads(row[0]) for row in rows], total, args),
                    product=product, includes_deleted=args.include_deleted)
    condition, values = 'p.gtin14=?', [args.code]
    if args.kind != 'all':
        condition += ' AND d.kind=?'
        values.append(KINDS[args.kind])
    joined = ' FROM packages p JOIN products d ON d.id=p.product_id WHERE ' + condition
    total = db.execute('SELECT COUNT(*)' + joined, values).fetchone()[0]
    rows = db.execute('SELECT d.data,p.data' + joined + ' ORDER BY d.name_key,d.id,p.id LIMIT ? OFFSET ?',
                      values + [args.limit, offset])
    items = [dict(product=json.loads(row[0]), package=json.loads(row[1])) for row in rows]
    return dict(page_result(items, total, args), gtin14=args.code, kind=args.kind,
                includes_deleted=True, authenticity_verified=False)


def arguments(argv):
    parser = Parser(description='Find Polish RPL medicines, package codes and official document links.')
    parser.add_argument('--cache-dir', type=Path, default=Path(os.environ.get('LEKI_CACHE_DIR', str(Path.home() / '.cache/ai-polish-skills/leki'))))
    parser.add_argument('--offline', action='store_true', help='Use the existing index without a network request, even when expired.')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('refresh', help='Download the full official export and atomically rebuild the local index.')
    sub.add_parser('status', help='Read local index dates and counts; never access the network.')
    search = sub.add_parser('search', help='Find products by name or declared active substance.')
    search.add_argument('query', type=query)
    search.add_argument('--field', choices=('name', 'substance'), default='name')
    search.add_argument('--exact', action='store_true')
    product = sub.add_parser('product', help='Read one export product ID and its official document links.')
    product.add_argument('id', type=identifier)
    packages = sub.add_parser('packages', help='List packages for an exact product ID.')
    packages.add_argument('id', type=identifier)
    packages.add_argument('--include-deleted', action='store_true', help='Include deleted and unknown-status package records.')
    barcode = sub.add_parser('barcode', help='Match a GTIN/EAN; preserve deleted entries and ambiguous matches.')
    barcode.add_argument('code', type=gtin)
    for command in (search, barcode):
        command.add_argument('--kind', choices=('human', 'veterinary', 'all'), default='human')
    for command in (search, packages, barcode):
        command.add_argument('--page', type=bounded_integer(1, 100000), default=1)
        command.add_argument('--limit', type=bounded_integer(1, 50), default=10)
    args = parser.parse_args(argv)
    if args.offline and args.command == 'refresh':
        raise SkillError('--offline cannot be combined with refresh.')
    return args


def main(argv=None):
    try:
        args = arguments(argv)
        if args.command == 'refresh':
            path = refresh(args.cache_dir)
        elif args.command == 'status':
            path = args.cache_dir / 'registry-v1.sqlite3'
        else:
            path = ensure_index(args.cache_dir, args.offline)
        with read_db(path) as db:
            metadata = read_metadata(db)
            result = {'index_ready': True} if args.command in ('refresh', 'status') else lookup(db, args)
        print(json.dumps(dict(source='Rejestr Produktów Leczniczych / URPL, Centrum e-Zdrowia',
                              source_homepage=HOMEPAGE, snapshot=metadata, offline_requested=args.offline,
                              result=result), ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        error = dict(error=str(exc), type=exc.kind, **exc.details)
        code = exc.code
    except (sqlite3.DatabaseError, OSError, ValueError, TypeError) as exc:
        error = dict(error='Local index or filesystem error; check the cache directory and run refresh.',
                     type='cache_error', cause=type(exc).__name__)
        code = 69
    print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
    return code


if __name__ == '__main__':
    sys.exit(main())
