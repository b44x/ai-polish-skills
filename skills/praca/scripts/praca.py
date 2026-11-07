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


import time

BASE = "https://solid.jobs/public-api/"
API_VERSION = "1.0"
DIVISIONS = ("IT", "Engineering", "Marketing", "Sales", "HR", "Logistics", "Finances", "Other")


def valid_page(data, page, limit):
    for key in ("pageIndex", "pageSize", "totalCount", "totalPages"):
        if not natural(data.get(key)):
            malformed()
    if data["pageIndex"] != page or data["pageSize"] != limit:
        malformed()
    total = data["totalCount"]
    if data["totalPages"] != (total + limit - 1) // limit:
        malformed()
    rows = data.get("jobs")
    if not isinstance(rows, list) or len(rows) != min(limit, max(0, total - page * limit)):
        malformed()
    for row in rows:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k] for k in ("jobOfferKey", "title", "company", "url")):
            malformed()
        for field in ("salary", "secondarySalary"):
            salary = row.get(field)
            if salary is not None:
                if not isinstance(salary, dict):
                    malformed()
                for name in ("from", "to"):
                    value = salary.get(name)
                    if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                        malformed()
        if type(row.get("isRemote")) is not bool:
            malformed()
    if len({r["jobOfferKey"] for r in rows}) != len(rows):
        malformed()
    return rows


def salary_match(row, minimum):
    if minimum is None:
        return True
    for key in ("salary", "secondarySalary"):
        pay = row.get(key) or {}
        value = pay.get("from")
        if pay.get("currency") == "PLN" and pay.get("period") == "Month" and value is not None and value >= minimum:
            return True
    return False


def search(args):
    results, requests, seen = [], [], set()
    totals, scanned, last_page = [], 0, args.page
    for page in range(args.page, args.page + args.pages):
        params = {"campaign": "ai-polish-skills", "pageIndex": page, "pageSize": args.limit,
                  "sortActive": "validFrom", "sortDirection": "desc"}
        for key, value in (("search.searchTerm", args.query), ("search.cities", args.city), ("search.experiences", args.experience)):
            if value:
                params[key] = value
        url = BASE + "offers/" + args.division + "?" + urllib.parse.urlencode(params)
        if requests:
            time.sleep(0.25)
        data = fetch(url)
        rows = valid_page(data, page, args.limit)
        requests.append({"url": url, "fetched_at": stamp()})
        totals.append(data["totalCount"])
        scanned += len(rows)
        for row in rows:
            if row["jobOfferKey"] in seen:
                continue
            seen.add(row["jobOfferKey"])
            if args.remote and not row["isRemote"]:
                continue
            if not salary_match(row, args.min_pln_month):
                continue
            results.append({k: v for k, v in row.items() if k not in ("description", "companyLogoUrl")})
        last_page = page
        more = page + 1 < data["totalPages"]
        if not more:
            break
    if not results and not more:
        raise SkillError("Brak dopasowań w sprawdzonym zakresie stron.", "not_found", 2,
                         pages_scanned=len(requests), start_page=args.page)
    return {"source": "SOLID.Jobs", "requests": requests, "fetched_at": stamp(),
            "result": {"jobs": results, "matched_on_scanned_pages": len(results),
                       "scanned_offers": scanned, "pages_scanned": len(requests),
                       "start_page": args.page, "last_page": last_page,
                       "upstream_total": totals[-1], "upstream_total_changed": len(set(totals)) > 1,
                       "has_more": more, "next_page": last_page + 1 if more else None,
                       "local_filters": {"remote": args.remote, "min_pln_month": args.min_pln_month},
                       "note": "Filtry remote i min_pln_month dotyczą tylko pobranych stron. B2B i UoP zachowują odrębne kwoty; to oferty jednego portalu, nie cały rynek pracy."}}


def main(argv=None):
    try:
        parser = Parser(description="Oferty pracy i statystyki z oficjalnego API SOLID.Jobs.")
        sub = parser.add_subparsers(dest="command", required=True)
        p = sub.add_parser("search", help="Wyszukaj oferty; jawne strony, filtry lokalne.")
        p.add_argument("query", nargs="?", type=phrase)
        p.add_argument("--division", choices=DIVISIONS, default="IT")
        p.add_argument("--city", type=phrase)
        p.add_argument("--experience", choices=("Intern", "Junior", "Regular", "Senior"))
        p.add_argument("--page", type=integer(0, 1000000), default=0)
        p.add_argument("--pages", type=integer(1, 5), default=1)
        p.add_argument("--limit", type=integer(1, 100), default=20, help="Rozmiar strony 1..100.")
        p.add_argument("--remote", action="store_true", help="Lokalny filtr pracy całkowicie zdalnej.")
        p.add_argument("--min-pln-month", type=integer(1, 1000000), help="Lokalny filtr dolnej stawki PLN/Month (B2B lub UoP).")
        p = sub.add_parser("stats", help="Agregaty ofert danego działu, nie wynagrodzenia całej Polski.")
        p.add_argument("--division", choices=DIVISIONS, default="IT")
        args = parser.parse_args(argv)
        if args.command == "search":
            result = search(args)
        else:
            url = BASE + "market-statistics/division/" + args.division + "?campaign=ai-polish-skills"
            data = fetch(url)
            if data.get("scopeKind") != "division" or data.get("scopeKey") != args.division or not isinstance(data.get("generatedAt"), str):
                malformed()
            if not isinstance(data.get("demand"), dict) or not natural(data["demand"].get("activeOffers")):
                malformed()
            result = {"source": "SOLID.Jobs", "source_url": url, "fetched_at": stamp(), "result": data,
                      "note": "Agregaty dostawcy, tylko SOLID.Jobs. overall miesza formy umowy; porównuj osobno b2b/permanent. Bieżący kwartał może być niepełny."}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        return emit_error(exc)


if __name__ == "__main__":
    sys.exit(main())
