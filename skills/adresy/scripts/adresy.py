#!/usr/bin/env python3
"""Read-only official API client; Python 3.8+, standard library only."""

import argparse
from datetime import datetime, timezone
import http.client
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request

MAX_RESPONSE = 4 * 1024 * 1024


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64, **details):
        super().__init__(message)
        self.kind, self.code, self.details = kind, code, details


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def integer(low, high):
    def parse(value):
        try:
            number = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError("Oczekiwano liczby całkowitej.")
        if not low <= number <= high:
            raise argparse.ArgumentTypeError("Zakres: %s..%s." % (low, high))
        return number
    return parse


def phrase(value):
    value = value.strip()
    if not 2 <= len(value) <= 200 or any(ord(c) < 32 for c in value):
        raise argparse.ArgumentTypeError("Podaj 2..200 znaków bez znaków sterujących.")
    return value


def malformed():
    raise SkillError("Nieprawidłowy format odpowiedzi API.", "upstream_format", 69)


def reject_constant(value):
    raise ValueError("Non-finite JSON number")


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite JSON number")
    return result


def fetch(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "ai-polish-skills/1.0 (+https://github.com/b44x/ai-polish-skills)",
        "Accept": "application/json", "Accept-Language": "pl", "X-Api-Version": API_VERSION})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            malformed()
        data = json.loads(raw, parse_constant=reject_constant, parse_float=finite_float)
        if not isinstance(data, dict):
            malformed()
        return data
    except urllib.error.HTTPError as exc:
        code = 2 if exc.code == 404 else 69
        kind = "not_found" if code == 2 else "rate_limit" if exc.code == 429 else "upstream_error"
        raise SkillError("API HTTP %s." % exc.code, kind, code,
                         http_status=exc.code, retry_after=exc.headers.get("Retry-After"))
    except (urllib.error.URLError, OSError, http.client.HTTPException):
        raise SkillError("Nie udało się pobrać danych z API; spróbuj później.", "network_error", 69)
    except (ValueError, UnicodeError, RecursionError):
        malformed()


def emit_error(exc):
    print(json.dumps(dict(error=str(exc), type=exc.kind, **exc.details), ensure_ascii=False), file=sys.stderr)
    return exc.code


def stamp():
    return datetime.now(timezone.utc).isoformat()


def natural(value):
    return type(value) is int and value >= 0


BASE = "https://services.gugik.gov.pl/uug/"
API_VERSION = "1.0"


def coordinate(value):
    try:
        result = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Nieprawidłowa współrzędna.")
    if not math.isfinite(result):
        raise argparse.ArgumentTypeError("Współrzędna musi być skończona.")
    return result


def normalize(data):
    kind = data.get("type")
    if kind not in ("address", "street", "city") or "results" not in data:
        malformed()
    rows = data["results"]
    if rows is None:
        if data.get("returned objects") != 0:
            malformed()
        rows = {}
    if not isinstance(rows, dict):
        malformed()
    returned = data.get("returned objects", len(rows))
    if not natural(returned) or returned != len(rows):
        malformed()
    results = []
    for row in rows.values():
        if not isinstance(row, dict) or not isinstance(row.get("city"), str):
            malformed()
        if type(row.get("x")) not in (str, int, float) or type(row.get("y")) not in (str, int, float):
            malformed()
        try:
            lon, lat = float(row["x"]), float(row["y"])
        except (KeyError, TypeError, ValueError, OverflowError):
            malformed()
        # srid=4326 is always sent. Reject projected metres or corrupt coordinates.
        if not math.isfinite(lon) or not math.isfinite(lat) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
            malformed()
        results.append(dict(row, longitude=lon, latitude=lat))
    if not results:
        raise SkillError("Brak dopasowania adresu; doprecyzuj miejscowość i ulicę.", "not_found", 2)
    return {"object_type": kind, "crs": "EPSG:4326", "results": results,
            "returned": len(results), "ambiguous": len(results) > 1,
            "upstream_metadata": {k: v for k, v in data.items() if k != "results"},
            "pagination_supported": False, "complete": None,
            "note": "Wyniki mogą być przybliżone lub ograniczone przez UUG. Doprecyzuj adres; found objects nie jest liczbą wszystkich zgodnych adresów."}


def main(argv=None):
    try:
        parser = Parser(description="Adresy i współrzędne z oficjalnej usługi GUGiK UUG.")
        sub = parser.add_subparsers(dest="command", required=True)
        search = sub.add_parser("search", help="Znajdź adres, ulicę lub miejscowość.")
        search.add_argument("address", type=phrase)
        reverse = sub.add_parser("reverse", help="Najbliższy punkt adresowy dla GPS.")
        reverse.add_argument("latitude", type=coordinate)
        reverse.add_argument("longitude", type=coordinate)
        args = parser.parse_args(argv)
        if args.command == "search":
            params = {"request": "GetAddress", "address": args.address, "srid": 4326}
        else:
            if not (-90 <= args.latitude <= 90 and -180 <= args.longitude <= 180):
                raise SkillError("GPS poza zakresem: latitude -90..90, longitude -180..180.")
            params = {"request": "GetAddressReverse", "location": "POINT(%s %s)" % (args.longitude, args.latitude), "srid": 4326}
        url = BASE + "?" + urllib.parse.urlencode(params)
        result = normalize(fetch(url))
        print(json.dumps({"source": "GUGiK — UUG", "source_url": url,
                          "fetched_at": stamp(), "result": result}, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        return emit_error(exc)


if __name__ == "__main__":
    sys.exit(main())
