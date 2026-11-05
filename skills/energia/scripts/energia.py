#!/usr/bin/env python3
"""Rynkowe ceny energii PSE: Python 3.8+, standard library only."""

import argparse
import calendar
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.raporty.pse.pl/api/rce-pln"
UTC = dt.timezone.utc
TTL = 300
NOTE = "RCE to cena rynkowa PSE, nie koszt rachunku. Przeliczenie PLN/kWh nie obejmuje VAT, dystrybucji, marży ani pozostałych składników umowy."


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64):
        super().__init__(message)
        self.kind, self.code = kind, code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def last_sunday(year, month):
    last = dt.date(year, month, calendar.monthrange(year, month)[1])
    return last - dt.timedelta(days=(last.weekday() + 1) % 7)


def warsaw(value):
    """EU DST since 2004; input UTC. Fixed-offset ISO output disambiguates folds."""
    value = value.astimezone(UTC)
    start = dt.datetime.combine(last_sunday(value.year, 3), dt.time(1), UTC)
    end = dt.datetime.combine(last_sunday(value.year, 10), dt.time(1), UTC)
    return value.astimezone(dt.timezone(dt.timedelta(hours=2 if start <= value < end else 1)))


def midnight(day):
    # At local midnight the March change has not happened; October still has DST.
    summer = last_sunday(day.year, 3) < day <= last_sunday(day.year, 10)
    return dt.datetime.combine(day, dt.time(), UTC) - dt.timedelta(hours=2 if summer else 1)


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def date_arg(value):
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError()
        result = dt.date.fromisoformat(value)
        if result.year < 2024:
            raise ValueError()
        return result
    except ValueError:
        raise SkillError("Data musi mieć format YYYY-MM-DD i rok co najmniej 2024.")


def positive_kwh(value):
    try:
        n = float(value)
        if not math.isfinite(n) or n <= 0 or n > 1000000:
            raise ValueError()
        return n
    except ValueError:
        raise SkillError("--kwh musi być dodatnią liczbą, maksymalnie 1000000.")


def fetch_page(url):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ai-polish-skills-energia/1.0.0", "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError()
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("value"), list):
            raise ValueError()
        return data
    except urllib.error.HTTPError as exc:
        raise SkillError("PSE HTTP " + str(exc.code), "upstream_error", 69)
    except (urllib.error.URLError, OSError) as exc:
        raise SkillError("Błąd połączenia z PSE: " + str(exc), "network_error", 69)
    except (ValueError, UnicodeError):
        raise SkillError("Nieprawidłowa odpowiedź JSON PSE.", "upstream_format", 69)


def get_rows(start, end, cache_dir=None, no_cache=False):
    condition = "business_date ge '{}' and business_date le '{}'".format(start, end)
    url = BASE + "?" + urllib.parse.urlencode({"$filter": condition, "$first": 1000})
    cache = Path(cache_dir or os.path.join(os.path.expanduser("~"), ".cache", "ai-polish-skills", "energia"))
    path = cache / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    now = time.time()
    if not no_cache:
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved["source"] == url and 0 <= now - saved["fetched_at"] < TTL and isinstance(saved["rows"], list):
                return saved["rows"], saved["fetched_at"], True
        except (OSError, ValueError, KeyError, TypeError):
            pass
    rows, seen = [], set()
    next_url = url
    for _ in range(8):
        parts = urllib.parse.urlsplit(next_url)
        if parts.scheme != "https" or parts.netloc != "api.raporty.pse.pl" or parts.path != "/api/rce-pln" or next_url in seen:
            raise SkillError("Nieprawidłowy odnośnik paginacji PSE.", "upstream_format", 69)
        seen.add(next_url)
        page = fetch_page(next_url)
        rows.extend(page["value"])
        if len(rows) > 4000:
            raise SkillError("Przekroczony limit danych PSE.", "upstream_format", 69)
        next_url = page.get("nextLink")
        if not next_url:
            break
        if not isinstance(next_url, str):
            raise SkillError("Nieprawidłowa paginacja PSE.", "upstream_format", 69)
    else:
        raise SkillError("Przekroczony limit stron PSE.", "upstream_format", 69)
    if not no_cache:
        try:
            cache.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(".{}.tmp".format(os.getpid()))
            temp.write_text(json.dumps({"source": url, "fetched_at": now, "rows": rows}), encoding="utf-8")
            temp.replace(path)
        except OSError:
            pass
    return rows, now, False


def parse_timestamp(value):
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)


def normalize(rows, first, last):
    intervals = {}
    try:
        for row in rows:
            day = dt.date.fromisoformat(row["business_date"])
            if not first <= day <= last:
                raise ValueError()
            price = row["rce_pln"]
            if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price):
                raise ValueError()
            end = parse_timestamp(row["dtime_utc"])
            clocks = re.fullmatch(r"(\d{2}):(\d{2}) - (\d{2}):(\d{2})", row["period_utc"])
            if not clocks:
                raise ValueError()
            h1, m1, h2, m2 = map(int, clocks.groups())
            if h1 > 23 or h2 > 24 or m1 > 59 or m2 > 59 or (h2 == 24 and m2 != 0):
                raise ValueError()
            minutes = ((h2 * 60 + m2) - (h1 * 60 + m1)) % 1440
            if minutes not in (15, 60) or end.second or end.microsecond or end.hour != h2 % 24 or end.minute != m2:
                raise ValueError()
            start = end - dt.timedelta(minutes=minutes)
            if start < midnight(day) or end > midnight(day + dt.timedelta(days=1)):
                raise ValueError()
            publication = parse_timestamp(row["publication_ts_utc"])
            item = {"business_date": str(day), "start_utc": iso(start), "end_utc": iso(end),
                    "start_local": warsaw(start).isoformat(), "end_local": warsaw(end).isoformat(),
                    "minutes": minutes, "rce_pln_mwh": price, "rce_pln_kwh": round(price / 1000, 8),
                    "published_at": iso(publication)}
            previous = intervals.get(item["end_utc"])
            if previous and previous["published_at"] == item["published_at"] and previous != item:
                raise ValueError()
            if previous is None or publication > parse_timestamp(previous["published_at"]):
                intervals[item["end_utc"]] = item
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise SkillError("Nieprawidłowy przedział, cena lub znacznik czasu PSE.", "upstream_format", 69)
    result = sorted(intervals.values(), key=lambda item: item["start_utc"])
    if any(a["end_utc"] > b["start_utc"] for a, b in zip(result, result[1:])):
        raise SkillError("Nakładające się przedziały PSE.", "upstream_format", 69)
    return result


def weighted_mean(rows):
    covered = sum(row["minutes"] for row in rows)
    if not covered:
        return None
    # Normalize weights before multiplying, so a finite price such as 1e308
    # does not overflow merely because its interval is 15 or 60 minutes long.
    value = math.fsum(row["rce_pln_mwh"] * (row["minutes"] / covered) for row in rows)
    if not math.isfinite(value):
        raise SkillError("Średnia cen PSE wykracza poza zakres liczbowy.", "upstream_format", 69)
    return value


def day_report(day, intervals):
    rows = [i for i in intervals if i["business_date"] == str(day)]
    start, end = midnight(day), midnight(day + dt.timedelta(days=1))
    expected = int((end - start).total_seconds() / 60)
    cursor, complete = iso(start), bool(rows)
    covered = 0
    for row in rows:
        if row["start_utc"] != cursor:
            complete = False
        cursor = row["end_utc"]
        covered += row["minutes"]
    complete = complete and cursor == iso(end) and covered == expected
    return {"date": str(day), "complete": complete, "interval_count": len(rows),
            "expected_quarter_hours": expected // 15, "expected_minutes": expected,
            "available_minutes": covered,
            "mean_available_pln_mwh": round(weighted_mean(rows), 6) if covered else None,
            "min_pln_mwh": min((i["rce_pln_mwh"] for i in rows), default=None),
            "max_pln_mwh": max((i["rce_pln_mwh"] for i in rows), default=None)}


def cheapest(rows, minutes, kwh=None):
    candidates = []
    for index, first in enumerate(rows):
        subset, covered, cursor = [], 0, first["start_utc"]
        for row in rows[index:]:
            if row["start_utc"] != cursor:
                break
            take = min(row["minutes"], minutes - covered)
            end = parse_timestamp(row["start_utc"]) + dt.timedelta(minutes=take)
            subset.append(dict(row, minutes=take, end_utc=iso(end), end_local=warsaw(end).isoformat()))
            covered += take
            cursor = iso(end)
            if covered == minutes:
                candidates.append((weighted_mean(subset), subset))
                break
    if not candidates:
        raise SkillError("Brak ciągłego okna o podanej długości w wybranej dobie.", "not_found", 2)
    mean, selected = min(candidates, key=lambda pair: (pair[0], pair[1][0]["start_utc"]))
    result = {"minutes": minutes, "start_utc": selected[0]["start_utc"], "end_utc": selected[-1]["end_utc"],
              "start_local": selected[0]["start_local"], "end_local": selected[-1]["end_local"],
              "mean_pln_mwh": round(mean, 6), "mean_pln_kwh": round(mean / 1000, 8),
              "assumption": "Stała moc poboru przez całe okno; start na granicy przedziału PSE, ostatni przedział rozliczany proporcjonalnie do wykorzystanych minut."}
    if kwh is not None:
        result.update(energy_kwh=kwh, rce_component_pln=round(mean / 1000 * kwh, 6))
    return result


def main(argv=None):
    parser = Parser(description="Ceny rynkowe RCE z oficjalnego API PSE; nie taryfa detaliczna.")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    for name, help_text in (("day", "Przedziały i kompletność doby"), ("cheapest", "Najtańsze ciągłe okno w pełnej dobie"),
                            ("summary", "Podsumowanie zakresu do 31 dni")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--cache-dir")
        command.add_argument("--no-cache", action="store_true")
        if name == "summary":
            command.add_argument("--from", dest="first", required=True, type=date_arg)
            command.add_argument("--to", dest="last", required=True, type=date_arg)
        else:
            command.add_argument("date", nargs="?", type=date_arg,
                                 default=str(warsaw(dt.datetime.now(UTC)).date()), help="YYYY-MM-DD; domyślnie dziś w Polsce")
        if name == "cheapest":
            command.add_argument("--minutes", type=int, default=120, help="Wielokrotność 15 od 15 do 1500")
            command.add_argument("--kwh", type=positive_kwh, help="Energia zużyta przy stałej mocy w całym oknie")
    try:
        args = parser.parse_args(argv)
        first = args.first if args.command == "summary" else args.date
        last = args.last if args.command == "summary" else args.date
        if first > last or (last - first).days >= 31:
            raise SkillError("Zakres musi być rosnący i obejmować maksymalnie 31 dni.")
        if args.command == "cheapest" and (not 15 <= args.minutes <= 1500 or args.minutes % 15):
            raise SkillError("--minutes musi być wielokrotnością 15 od 15 do 1500.")
        raw, fetched, cached = get_rows(first, last, args.cache_dir, args.no_cache)
        rows = normalize(raw, first, last)
        if not rows:
            raise SkillError("PSE nie opublikowało danych RCE dla wskazanego okresu.", "not_found", 2)
        days = [day_report(first + dt.timedelta(days=i), rows) for i in range((last - first).days + 1)]
        result = {"source": "PSE S.A.", "source_url": BASE, "timezone": "Europe/Warsaw", "price_basis": "RCE",
                  "fetched_at": iso(dt.datetime.fromtimestamp(fetched, UTC)), "cached": cached,
                  "latest_publication_at": max((i["published_at"] for i in rows), key=parse_timestamp), "note": NOTE}
        if args.command == "day":
            result.update(days[0], intervals=rows)
        elif args.command == "cheapest":
            if not days[0]["complete"]:
                raise SkillError("Dane doby są niepełne; nie można wskazać najtańszego okna całej doby.", "incomplete_data", 69)
            result.update(date=str(first), complete=True, window=cheapest(rows, args.minutes, args.kwh))
        else:
            complete = all(d["complete"] for d in days)
            mean = round(weighted_mean(rows), 6)
            result.update(first_date=str(first), last_date=str(last), complete=complete, days=days,
                          missing_dates=[d["date"] for d in days if not d["interval_count"]],
                          mean_available_pln_mwh=mean, mean_full_period_pln_mwh=mean if complete else None)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        print(json.dumps({"error": str(exc), "type": exc.kind}, ensure_ascii=False), file=sys.stderr)
        return exc.code
    except (ValueError, OverflowError):
        print(json.dumps({"error": "Wynik obliczeń cen PSE wykracza poza zakres liczbowy.",
                          "type": "upstream_format"}, ensure_ascii=False), file=sys.stderr)
        return 69


if __name__ == "__main__":
    sys.exit(main())
