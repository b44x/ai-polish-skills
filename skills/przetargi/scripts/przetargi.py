#!/usr/bin/env python3
"""Search public BZP procurement notices using the official e-Zamówienia API."""

import argparse
import datetime as dt
from html.parser import HTMLParser
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"
PROVINCES = {
    "dolnoslaskie": "PL02", "kujawsko-pomorskie": "PL04", "lubelskie": "PL06",
    "lubuskie": "PL08", "lodzkie": "PL10", "malopolskie": "PL12",
    "mazowieckie": "PL14", "opolskie": "PL16", "podkarpackie": "PL18",
    "podlaskie": "PL20", "pomorskie": "PL22", "slaskie": "PL24",
    "swietokrzyskie": "PL26", "warminsko-mazurskie": "PL28",
    "wielkopolskie": "PL30", "zachodniopomorskie": "PL32",
}
NOTE = "Ogłoszenia BZP; termin w ogłoszeniu nie potwierdza, że postępowanie nadal przyjmuje oferty. Województwo dotyczy zamawiającego."


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64):
        super().__init__(message)
        self.kind, self.code = kind, code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


class Client:
    """Space requests within one CLI run below the shared per-IP limit."""
    def __init__(self):
        self.last_request = None

    def fetch(self, params):
        if self.last_request is not None:
            time.sleep(max(0, 2.1 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        request = urllib.request.Request(BASE + "?" + urllib.parse.urlencode(params),
                                         headers={"User-Agent": "ai-polish-skills-przetargi/1.0.0", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                rows = json.load(response)
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                raise ValueError("Expected a list of notices")
            return rows
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429):
                raise SkillError("BZP odrzucił żądanie (HTTP %s); możliwy limit 30 zapytań/min/IP. Spróbuj później." % exc.code,
                                 "access_or_rate_limit", 69)
            # BZP can return 404 for invalid query parameters, not just missing notices.
            raise SkillError("BZP HTTP " + str(exc.code), "upstream_error", 69)
        except (urllib.error.URLError, OSError) as exc:
            raise SkillError("Błąd połączenia z BZP: " + str(exc), "network_error", 69)
        except (ValueError, UnicodeError):
            raise SkillError("Nieprawidłowa odpowiedź JSON BZP.", "upstream_format", 69)


def province(value):
    normalized = "".join(c for c in unicodedata.normalize("NFKD", value.lower().replace("ł", "l"))
                         if not unicodedata.combining(c)).strip()
    if normalized in PROVINCES:
        return PROVINCES[normalized]
    if value.upper() in PROVINCES.values():
        return value.upper()
    raise argparse.ArgumentTypeError("Nieznane województwo. Podaj nazwę lub kod PL02..PL32.")


def date_value(value):
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("date format")
        return dt.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Wymagana prawidłowa data YYYY-MM-DD.")


def uuid_value(value):
    if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value):
        raise argparse.ArgumentTypeError("Kursor musi być identyfikatorem objectId (UUID) ostatniego ogłoszenia.")
    return value


def summarize(row):
    if not row.get("objectId") or not row.get("noticeNumber"):
        raise SkillError("Ogłoszenie BZP nie zawiera identyfikatora.", "upstream_format", 69)
    return {
        "id": row["noticeNumber"], "object_id": row["objectId"],
        "title": row.get("orderObject"), "notice_type": row.get("noticeType"),
        "buyer": row.get("organizationName"), "buyer_city": row.get("organizationCity"),
        "buyer_voivodeship": row.get("organizationProvince"),
        "published_at": row.get("publicationDate"), "offers_due_at": row.get("submittingOffersDate"),
        "cpv": row.get("cpvCode"), "tender_id": row.get("tenderId"),
        "source_url": "https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/id/" + urllib.parse.quote(row["objectId"], safe=""),
    }


def search(client, params, limit):
    rows, seen = [], set()
    params = dict(params)
    while len(rows) < limit:
        size = min(100, limit - len(rows))
        batch = client.fetch(dict(params, PageSize=size))
        if len(batch) > size:
            raise SkillError("BZP zwrócił więcej rekordów niż żądano.", "upstream_format", 69)
        for row in batch:
            result = summarize(row)
            if result["object_id"] in seen:
                raise SkillError("BZP powtórzył rekord podczas stronicowania.", "upstream_pagination", 69)
            seen.add(result["object_id"])
            rows.append(result)
        if len(batch) < size:
            break
        cursor = batch[-1]["objectId"]
        if cursor == params.get("SearchAfter"):
            raise SkillError("BZP nie przesunął kursora wyników.", "upstream_pagination", 69)
        params["SearchAfter"] = cursor
    if not rows:
        raise SkillError("Brak ogłoszeń BZP dla podanych filtrów.", "not_found", 2)
    # An exact page boundary may be the end; do not claim there are more records.
    limited = len(rows) == limit
    return {"notices": rows, "count": len(rows), "limit_reached": limited,
            "has_more": None if limited else False,
            "next_cursor": rows[-1]["object_id"] if limited else None,
            "filters": {k: v for k, v in params.items() if k != "SearchAfter"},
            "order": "upstream", "note": NOTE}


class PlainText(HTMLParser):
    """Keep notice content readable, without scripts, styles or executable HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("br", "p", "h1", "h2", "h3", "div", "tr", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        if tag in ("p", "h1", "h2", "h3", "div", "tr", "li"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self):
        return "\n".join(line for line in (" ".join(s.split()) for s in "".join(self.parts).splitlines()) if line)


def notice(client, identifier):
    # The documented public API supports NoticeNumber, not GET /notice/{UUID}.
    match = re.fullmatch(r"(20\d{2})/BZP (\d{8})/(\d{2})", identifier.strip())
    if not match:
        raise SkillError('Podaj pełny numer z pola id, np. "2026/BZP 00505976/01" (nie UUID).')
    year = int(match.group(1))
    params = {"NoticeType": "ContractNotice", "NoticeNumber": identifier.strip(),
              "PublicationDateFrom": "%04d-01-01T00:00:00Z" % year,
              "PublicationDateTo": "%04d-01-01T00:00:00Z" % (year + 1), "PageSize": 100}
    rows = client.fetch(params)
    row = next((r for r in rows if r.get("noticeNumber") == identifier.strip()), None)
    if row is None:
        raise SkillError("Brak ogłoszenia o zamówieniu o podanym numerze.", "not_found", 2)
    result = summarize(row)
    body = row.get("htmlBody")
    parser = PlainText()
    if body:
        parser.feed(body)
    result.update(content_text=parser.text() if body else None, note=NOTE)
    return {"notice": result}


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True)
        listing = commands.add_parser("search", help="Szukaj ogłoszeń o zamówieniu w BZP")
        listing.add_argument("phrase", nargs="?", help="Fraza w przedmiocie zamówienia; opcjonalna przy --cpv")
        listing.add_argument("--voivodeship", type=province, help="Województwo zamawiającego")
        listing.add_argument("--cpv", help="Kod CPV: 8 cyfr, opcjonalnie myślnik i cyfra kontrolna")
        listing.add_argument("--from", dest="date_from", type=date_value)
        listing.add_argument("--to", dest="date_to", type=date_value)
        listing.add_argument("--limit", type=int, default=20, help="1..500, domyślnie 20")
        listing.add_argument("--after", type=uuid_value, help="next_cursor z poprzedniego wyszukiwania")
        detail = commands.add_parser("notice", help="Szczegóły po pełnym numerze BZP (pole id)")
        detail.add_argument("id")
        args = parser.parse_args(argv)
        client = Client()
        if args.command == "notice":
            result = notice(client, args.id)
        else:
            phrase = args.phrase.strip() if args.phrase is not None else None
            if (phrase is not None and not phrase) or (phrase is None and not args.cpv) or not 1 <= args.limit <= 500:
                raise SkillError("Podaj niepustą frazę lub --cpv oraz limit 1..500.")
            if args.cpv and not re.fullmatch(r"\d{8}(?:-\d)?", args.cpv):
                raise SkillError("Nieprawidłowy kod CPV.")
            end = args.date_to or dt.datetime.now(dt.timezone.utc).date()
            start = args.date_from or end - dt.timedelta(days=6)
            if start > end or end == dt.date.max:
                raise SkillError("Nieprawidłowy zakres dat: data od musi być wcześniejsza lub równa dacie do.")
            params = {"NoticeType": "ContractNotice",
                      "PublicationDateFrom": start.isoformat() + "T00:00:00Z",
                      "PublicationDateTo": end.isoformat() + "T23:59:59.9999999Z"}
            for name, value in (("OrderObject", phrase), ("OrganizationProvince", args.voivodeship), ("CpvCode", args.cpv), ("SearchAfter", args.after)):
                if value:
                    params[name] = value
            result = search(client, params, args.limit)
        result.update(source="Biuletyn Zamówień Publicznych — e-Zamówienia", source_url=BASE,
                      fetched_at=dt.datetime.now(dt.timezone.utc).isoformat())
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        return report(exc)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return report(SkillError("Nieprawidłowa struktura danych BZP: " + str(exc), "upstream_format", 69))


def report(exc):
    print(json.dumps({"error": str(exc), "type": exc.kind}, ensure_ascii=False), file=sys.stderr)
    return exc.code


if __name__ == "__main__":
    sys.exit(main())
