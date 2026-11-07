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


BASE = "https://api.dane.gov.pl/1.4/"
API_VERSION = "1.4"


def validate_record(record, expected_type):
    if not isinstance(record, dict) or record.get("type") != expected_type:
        malformed()
    if not isinstance(record.get("id"), str) or not record["id"].isdigit():
        malformed()
    if not isinstance(record.get("attributes"), dict) or not isinstance(record["attributes"].get("title"), str):
        malformed()
    return record


def listing(data, args, expected_type):
    rows, meta, links = data.get("data"), data.get("meta"), data.get("links")
    if not isinstance(rows, list) or not isinstance(meta, dict) or not isinstance(links, dict):
        malformed()
    count = meta.get("count")
    if not natural(count) or len(rows) > args.limit or len(rows) > count:
        malformed()
    for row in rows:
        validate_record(row, expected_type)
    if len({r['id'] for r in rows}) != len(rows):
        malformed()
    more = args.page * args.limit < count
    if more and len(rows) != args.limit:
        malformed()
    if not rows:
        raise SkillError("Brak zasobów na tej stronie; sprawdź zapytanie i numer strony.", "not_found", 2)
    return {"data": rows, "total": count, "page": args.page, "per_page": args.limit,
            "has_more": more, "next_page": args.page + 1 if more else None,
            "server_time": meta.get("server_time"), "links": links}


def main(argv=None):
    try:
        parser = Parser(description="Wyszukiwanie zbiorów i metadanych dane.gov.pl.")
        sub = parser.add_subparsers(dest="command", required=True)
        search = sub.add_parser("search", help="Szukaj zbiorów danych.")
        search.add_argument("query", type=phrase)
        resources = sub.add_parser("resources", help="Zasoby wskazanego zbioru.")
        resources.add_argument("id", type=integer(1, 2147483647))
        for p in (search, resources):
            p.add_argument("--page", type=integer(1, 1000000), default=1)
            p.add_argument("--limit", type=integer(1, 100), default=10)
        for command in ("dataset", "resource"):
            p = sub.add_parser(command, help="Pełne metadane pojedynczego obiektu.")
            p.add_argument("id", type=integer(1, 2147483647))
        args = parser.parse_args(argv)
        params = {}
        if args.command in ("search", "resources"):
            path = "datasets" if args.command == "search" else "datasets/%s/resources" % args.id
            params = {"page": args.page, "per_page": args.limit}
            if args.command == "search":
                params["q"] = args.query
        else:
            path = "%ss/%s" % (args.command, args.id)
        url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
        data = fetch(url)
        kind = "dataset" if args.command in ("search", "dataset") else "resource"
        if args.command in ("search", "resources"):
            result = listing(data, args, kind)
        else:
            record = validate_record(data.get("data"), kind)
            if record["id"] != str(args.id):
                malformed()
            result = {"data": record}
        print(json.dumps({"source": "dane.gov.pl", "source_url": url, "fetched_at": stamp(),
                          "result": result}, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        return emit_error(exc)


if __name__ == "__main__":
    sys.exit(main())
