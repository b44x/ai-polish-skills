#!/usr/bin/env python3
"""Look up Polish cadastral parcel footprints through the official ULDK API."""

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://uldk.gugik.gov.pl/"
DOCS = BASE + "opis.html"
ATTRIBUTION = "Źródło: Główny Urząd Geodezji i Kartografii (GUGiK), Usługa Lokalizacji Działek Katastralnych (ULDK)."
FIELDS = ["id", "parcel", "voivodeship", "county", "commune", "region", "datasource", "geom_wkt"]
ID_RE = re.compile(r"\d{6}_[1-9]\.\d{4}\.(?:AR_\d+\.)?\d+(?:/\d+)?\Z")
TOKEN_RE = re.compile(r"[(),]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
TTL = 300
MAX_RESPONSE = 8 * 1024 * 1024
MAX_RECORDS = 1000
MAX_COORDINATES = 100000


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64):
        super().__init__(message)
        self.kind, self.code = kind, code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def finite_number(value):
    try:
        result = float(value)
        if not math.isfinite(result):
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("Wymagana skończona liczba.")


def parcel_id(value):
    if not ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("Wymagany identyfikator EGiB, np. 022602_1.0003.59 lub 022602_1.0003.AR_1.59/2.")
    return value


def folded(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.lower().replace("ł", "l"))
                   if not unicodedata.combining(c))


def geometry(wkt, crs):
    """Parse only bounded 2D POLYGON/MULTIPOLYGON; keep native WKT as source."""
    if len(wkt) > 4 * 1024 * 1024:
        raise SkillError("Geometria ULDK jest zbyt duża.", "upstream_format", 69)
    header = re.fullmatch(r"(?:SRID=(\d+);)?\s*(POLYGON|MULTIPOLYGON)\s*(\(.*\))\s*", wkt, re.I)
    if not header or (header.group(1) is not None and
                      (len(header.group(1)) > 6 or int(header.group(1)) != crs)):
        raise SkillError("Nieprawidłowy typ lub układ geometrii ULDK.", "upstream_format", 69)
    kind, body = header.group(2).upper(), header.group(3)
    if TOKEN_RE.sub("", body).strip():
        raise SkillError("Nieprawidłowy zapis WKT ULDK.", "upstream_format", 69)
    matches = list(TOKEN_RE.finditer(body))
    tokens = [match.group() for match in matches]
    if len(tokens) > MAX_COORDINATES * 4 + 10000:
        raise SkillError("Zbyt wiele współrzędnych w geometrii ULDK.", "upstream_format", 69)
    index, coordinates = 0, []

    def group(depth=0):
        nonlocal index
        if depth > 3 or index >= len(tokens) or tokens[index] != "(":
            raise ValueError()
        index += 1
        result = []
        while True:
            if index >= len(tokens):
                raise ValueError()
            if tokens[index] == "(":
                result.append(group(depth + 1))
            else:
                if index + 1 >= len(tokens):
                    raise ValueError()
                if not body[matches[index].end():matches[index + 1].start()].isspace():
                    raise ValueError()
                point = [float(tokens[index]), float(tokens[index + 1])]
                if not all(math.isfinite(v) for v in point):
                    raise ValueError()
                if crs == 4326 and not (12 <= point[0] <= 26 and 48 <= point[1] <= 56):
                    raise ValueError()
                if crs == 2180 and not all(10000 <= v <= 1200000 for v in point):
                    raise ValueError()
                index += 2
                coordinates.append(point)
                if len(coordinates) > MAX_COORDINATES:
                    raise ValueError()
                result.append(point)
            if index >= len(tokens):
                raise ValueError()
            separator = tokens[index]
            index += 1
            if separator == ")":
                return result
            if separator != ",":
                raise ValueError()

    try:
        parsed = group()
        if index != len(tokens):
            raise ValueError()
        polygons = [parsed] if kind == "POLYGON" else parsed
        if not polygons:
            raise ValueError()
        for polygon in polygons:
            if not polygon:
                raise ValueError()
            for ring in polygon:
                if len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError()
                if not all(isinstance(point, list) and len(point) == 2
                           and all(isinstance(v, float) for v in point) for point in ring):
                    raise ValueError()
    except (ValueError, TypeError, IndexError, OverflowError):
        raise SkillError("Nieprawidłowe pierścienie lub współrzędne WKT ULDK.", "upstream_format", 69)
    bbox = [min(p[0] for p in coordinates), min(p[1] for p in coordinates),
            max(p[0] for p in coordinates), max(p[1] for p in coordinates)]
    return {"crs": "EPSG:%s" % crs,
            "axis_order": ["longitude", "latitude"] if crs == 4326 else ["easting", "northing"],
            "units": "degrees" if crs == 4326 else "metres", "wkt": wkt, "bbox": bbox,
            "vertex_count": len(coordinates),
            "geojson": {"type": "Polygon" if kind == "POLYGON" else "MultiPolygon", "coordinates": parsed}
            if crs == 4326 else None}


def parse_response(text, method, crs, expected_id=None):
    lines = [line.strip() for line in text.lstrip("\ufeff").splitlines() if line.strip()]
    if not lines:
        raise SkillError("Pusta odpowiedź ULDK.", "upstream_format", 69)
    # ULDK can prefix a technical failure with '-1 brak wyników'. It is not
    # a trustworthy negative lookup if any other diagnostic text follows.
    if lines[0].startswith("-"):
        negative = " ".join(folded(line) for line in lines)
        if negative in ("-1 brak wynikow", "-1 nie znaleziono obiektu"):
            raise SkillError("ULDK nie zwrócił działki; nie oznacza to, że działka nie istnieje.", "not_found", 2)
        raise SkillError("ULDK zgłosił błąd źródła: " + " ".join(lines)[:800], "upstream_error", 69)
    if "limit" in folded(lines[0]) and not lines[0].isdigit():
        raise SkillError("ULDK ograniczył liczbę zapytań; spróbuj później.", "rate_limit", 69)
    if not lines[0].isdigit() or len(lines[0]) > 6:
        raise SkillError("Nieprawidłowy status odpowiedzi ULDK.", "upstream_format", 69)
    status = int(lines[0])
    rows = lines[1:]
    if method == "GetParcelByIdOrNr":
        if status == 0 and not rows:
            raise SkillError("Brak działek w odpowiedzi ULDK dla tego obrębu i numeru.", "not_found", 2)
        if status != len(rows) or not 1 <= status <= MAX_RECORDS:
            raise SkillError("Niespójna liczba wyników wyszukiwania ULDK.", "upstream_format", 69)
    elif status != 0 or not rows or len(rows) > MAX_RECORDS:
        raise SkillError("Nieprawidłowy status lub liczba rekordów ULDK.", "upstream_format", 69)
    result, seen = [], set()
    for line in rows:
        fields = line.split("|")
        if len(fields) != len(FIELDS):
            raise SkillError("Nieprawidłowa liczba pól rekordu ULDK.", "upstream_format", 69)
        item = dict(zip(FIELDS, fields))
        if not ID_RE.fullmatch(item["id"]) or item["id"] in seen:
            raise SkillError("Nieprawidłowy lub powtórzony identyfikator działki ULDK.", "upstream_format", 69)
        if expected_id and item["id"] != expected_id:
            raise SkillError("ULDK zwrócił inną działkę niż wskazany identyfikator.", "upstream_format", 69)
        seen.add(item["id"])
        result.append({"id": item["id"], "parcel_number": item["parcel"] or None,
                       "voivodeship": item["voivodeship"] or None, "county": item["county"] or None,
                       "commune": item["commune"] or None, "district": item["region"] or None,
                       "data_source": item["datasource"] or None, "geometry": geometry(item["geom_wkt"], crs)})
    return result


def fetch(url):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ai-polish-skills-dzialki/1.0.0", "Accept": "text/plain"})
        with urllib.request.urlopen(request, timeout=35) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise SkillError("Odpowiedź ULDK przekracza limit 8 MiB.", "upstream_format", 69)
        return raw.decode("utf-8-sig")
    except urllib.error.HTTPError as exc:
        raise SkillError("ULDK HTTP %s; spróbuj później." % exc.code,
                         "rate_limit" if exc.code == 429 else "upstream_error", 69)
    except (urllib.error.URLError, OSError) as exc:
        raise SkillError("Błąd połączenia z ULDK: " + str(exc), "network_error", 69)
    except UnicodeError:
        raise SkillError("ULDK zwrócił nieprawidłowe kodowanie tekstu.", "upstream_format", 69)


def prune_cache(folder):
    files = []
    try:
        for path in folder.glob("uldk-*.json"):
            if re.fullmatch(r"uldk-[0-9a-f]{64}\.json", path.name) and path.is_file():
                files.append((path.stat().st_mtime, path))
        for _, path in sorted(files, reverse=True)[128:]:
            path.unlink()
    except OSError:
        pass


def load(url, method, crs, expected_id, folder=None, no_cache=False):
    folder = Path(folder or os.path.join(os.path.expanduser("~"), ".cache", "ai-polish-skills", "dzialki"))
    path = folder / ("uldk-" + hashlib.sha256(url.encode()).hexdigest() + ".json")
    now = time.time()
    if not no_cache:
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            stamp = saved["fetched_at"]
            if (saved["url"] == url and isinstance(stamp, (int, float)) and math.isfinite(stamp)
                    and 0 <= now - stamp < TTL and isinstance(saved["response"], str)
                    and len(saved["response"]) <= MAX_RESPONSE):
                return parse_response(saved["response"], method, crs, expected_id), stamp, True
        except (OSError, ValueError, KeyError, TypeError, OverflowError, SkillError):
            pass
    raw = fetch(url)
    result = parse_response(raw, method, crs, expected_id)
    if not no_cache:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(".%s.tmp" % os.getpid())
            temp.write_text(json.dumps({"url": url, "fetched_at": now, "response": raw}, ensure_ascii=False), encoding="utf-8")
            temp.replace(path)
            prune_cache(folder)
        except OSError:
            pass
    return result, now, False


def run(args):
    if not 1 <= args.limit <= 100:
        raise SkillError("--limit musi wynosić 1–100.")
    if args.command == "id":
        method, query, expected_id = "GetParcelById", {"id": args.identifier}, args.identifier
    elif args.command == "search":
        district = " ".join(args.district.split())
        if not 1 <= len(district) <= 100 or any(c in district for c in "|,;<>\r\n"):
            raise SkillError("Podaj nazwę obrębu długości 1–100 znaków.")
        if not re.fullmatch(r"\d+(?:/\d+)?", args.parcel):
            raise SkillError("Numer działki: cyfry lub cyfry/cyfry, np. 134 lub 134/2.")
        method, query, expected_id = "GetParcelByIdOrNr", {"id": district + " " + args.parcel}, None
    else:
        if not (49 <= args.lat <= 54.9 and 14 <= args.lon <= 24.3):
            raise SkillError("Punkt musi wskazywać Polskę: lat 49–54,9, lon 14–24,3.")
        method, query, expected_id = "GetParcelByXY", {"xy": "%.8f,%.8f,4326" % (args.lon, args.lat)}, None
    params = dict(query, request=method, result=",".join(FIELDS), srid=args.crs)
    url = BASE + "?" + urllib.parse.urlencode(params)
    records, fetched_at, cached = load(url, method, args.crs, expected_id, args.cache_dir, args.no_cache)
    return {"source": "GUGiK — ULDK", "source_url": url, "documentation": DOCS,
            "attribution": ATTRIBUTION, "operation": method, "query": query,
            "lookup_semantics": "parcel_containing_point" if args.command == "point" else "parcel_identifier_or_district_number",
            "fetched_at": dt.datetime.fromtimestamp(fetched_at, dt.timezone.utc).isoformat(),
            "cached": cached, "cache_ttl_seconds": TTL, "total_matches": len(records),
            "returned_records": min(len(records), args.limit), "ambiguous": len(records) > 1,
            "display_limit_reached": len(records) > args.limit, "records": records[:args.limit],
            "notes": ["Źródło może pochodzić z powiatowego WFS, bazy zbiorczej lub LPIS; sprawdź data_source.",
                      "Brak wyniku nie dowodzi, że działka nie istnieje; pokrycie powiatów może być niepełne.",
                      "Geometria lokalizuje działkę; nie potwierdza własności, księgi wieczystej ani możliwości zabudowy."]}


def build_parser():
    parser = Parser(description="Działki ewidencyjne: identyfikator, obręb/numer lub działka zawierająca punkt — oficjalne ULDK.")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("id", help="Działka po pełnym identyfikatorze EGiB.")
    p.add_argument("identifier", type=parcel_id)
    p = commands.add_parser("search", help="Działki po nazwie obrębu i numerze; nazwy mogą być niejednoznaczne.")
    p.add_argument("district", help="Nazwa obrębu, np. Krzewina.")
    p.add_argument("parcel", help="Numer działki, np. 134 lub 134/2.")
    p = commands.add_parser("point", help="Działka zawierająca punkt WGS84; nie wyszukiwanie najbliższej działki.")
    p.add_argument("--lat", required=True, type=finite_number)
    p.add_argument("--lon", required=True, type=finite_number)
    for command in commands.choices.values():
        command.add_argument("--crs", type=int, choices=[4326, 2180], default=4326, help="EPSG geometrii wynikowej; domyślnie 4326.")
        command.add_argument("--limit", type=int, default=20, help="1–100 wyświetlanych działek; domyślnie 20.")
        command.add_argument("--cache-dir", help="Opcjonalny katalog lokalnego cache (do 128 odpowiedzi, TTL 5 minut).")
        command.add_argument("--no-cache", action="store_true", help="Wyłącz odczyt i zapis cache.")
    return parser


def main(argv=None):
    try:
        result = run(build_parser().parse_args(argv))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except SkillError as exc:
        print(json.dumps({"error": str(exc), "type": exc.kind}, ensure_ascii=False), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
