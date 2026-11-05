#!/usr/bin/env python3
"""Discover and compare local statistics from the official GUS BDL API."""

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://bdl.stat.gov.pl/api/v1/"
SOURCE = "GUS, Bank Danych Lokalnych"
PRESETS = {"ludnosc": "72305"}
LEVELS = {0: "Polska", 1: "makroregion", 2: "województwo", 3: "region",
          4: "podregion", 5: "powiat", 6: "gmina"}


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64, **details):
        super().__init__(message)
        self.kind, self.code, self.details = kind, code, details


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def identifier(value):
    if not re.fullmatch(r"\d{12}", value):
        raise argparse.ArgumentTypeError("Wymagany 12-cyfrowy identyfikator BDL z komendy units, nie skrócony kod TERYT.")
    return value


def indicator(value):
    value = PRESETS.get(value, value)
    if not re.fullmatch(r"[1-9]\d{0,8}", value):
        raise argparse.ArgumentTypeError("Podaj dodatni identyfikator zmiennej BDL albo ludnosc.")
    return int(value)


def year_value(value):
    try:
        year = int(value)
        if not 1995 <= year <= dt.datetime.now(dt.timezone.utc).year:
            raise ValueError()
        return year
    except ValueError:
        raise argparse.ArgumentTypeError("Podaj rok od 1995 do bieżącego roku.")


class Client:
    """Cache public responses; stop on 429 instead of retrying shared IP limits."""
    def __init__(self, cache_dir=None, no_cache=False):
        self.cache_dir = Path(cache_dir or os.environ.get("MOJA_GMINA_CACHE_DIR") or
                              (Path.home() / ".cache" / "ai-polish-skills" / "moja-gmina"))
        self.no_cache = no_cache
        self.last_request = None
        self.responses = []

    def fetch(self, path, params=None, ttl=86400):
        query = [("format", "json"), ("lang", "pl")] + list(params or [])
        url = BASE + path + "?" + urllib.parse.urlencode(query, doseq=True)
        now = time.time()
        cache_file = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if not self.no_cache:
            try:
                saved = json.loads(cache_file.read_text(encoding="utf-8"))
                if saved["url"] == url and 0 <= now - saved["fetched_at"] < ttl and isinstance(saved["data"], dict):
                    self.responses.append({"url": url, "fetched_at": stamp(saved["fetched_at"]), "cached": True})
                    return saved["data"]
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if self.last_request is not None:
            time.sleep(max(0, 0.3 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        headers = {"User-Agent": "ai-polish-skills-moja-gmina/1.0.0", "Accept": "application/json"}
        if os.environ.get("BDL_API_KEY"):
            headers["X-ClientId"] = os.environ["BDL_API_KEY"]
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
                data = json.load(response)
            if not isinstance(data, dict) or "error" in data:
                raise ValueError("Expected a BDL object")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise SkillError("Nie znaleziono zasobu BDL.", "not_found", 2)
            if exc.code == 429:
                raise SkillError("Limit zapytań GUS BDL. Spróbuj później; opcjonalny BDL_API_KEY zwiększa limit.",
                                 "rate_limit", 69, retry_after=exc.headers.get("Retry-After"))
            raise SkillError("GUS BDL HTTP %s." % exc.code, "upstream_error", 69)
        except (urllib.error.URLError, OSError) as exc:
            raise SkillError("GUS BDL jest niedostępny: " + str(exc), "network_error", 69)
        except (ValueError, UnicodeError):
            raise SkillError("Nieprawidłowa odpowiedź JSON GUS BDL.", "upstream_format", 69)
        fetched = time.time()
        self.responses.append({"url": url, "fetched_at": stamp(fetched), "cached": False})
        if not self.no_cache:
            temporary = None
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(self.cache_dir), delete=False) as handle:
                    temporary = handle.name
                    json.dump({"url": url, "fetched_at": fetched, "data": data}, handle, ensure_ascii=False)
                os.replace(temporary, str(cache_file))
            except OSError:
                pass
            finally:
                if temporary:
                    try:
                        os.unlink(temporary)
                    except OSError:
                        pass
        return data


def stamp(timestamp=None):
    return dt.datetime.fromtimestamp(timestamp if timestamp is not None else time.time(), dt.timezone.utc).isoformat()


def results(data):
    rows = data.get("results")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise SkillError("BDL nie zwrócił listy results.", "upstream_format", 69)
    return rows


def metadata(client, variable_id):
    row = client.fetch("variables/" + str(variable_id))
    if str(row.get("id")) != str(variable_id) or not isinstance(row.get("years"), list):
        raise SkillError("Niekompletne metadane zmiennej BDL.", "upstream_format", 69)
    return row


def unit_details(client, unit_id):
    row = client.fetch("units/" + unit_id)
    if row.get("id") != unit_id or row.get("level") not in LEVELS:
        raise SkillError("Niekompletne metadane jednostki BDL.", "upstream_format", 69)
    return row


def observation(row, attributes):
    year = row.get("year")
    if isinstance(year, bool) or not (isinstance(year, int) or
                                    (isinstance(year, str) and re.fullmatch(r"\d{4}", year))):
        raise ValueError("Invalid observation year")
    year = int(year)
    if not 1995 <= year <= dt.datetime.now(dt.timezone.utc).year:
        raise ValueError("Observation year outside BDL range")
    raw = row.get("val")
    number = raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw) else None
    attr_id = row.get("attrId")
    attribute = attributes.get(str(attr_id)) if attr_id is not None else None
    # Resolve the actual dictionary, rather than assuming particular attribute IDs.
    description = " ".join(str(attribute.get(k) or "") for k in ("name", "description")) if attribute else ""
    unknown = attr_id is not None and attribute is None
    unavailable = unknown or (attribute or {}).get("symbol") in ("#", ".", "x", "X") or any(
        term in description.lower() for term in
        ("tajemnic", "utajn", "brak danych", "nie dotyczy", "niedostępn", "nie podano", "niepublik"))
    if unavailable:
        number = None
    return {"year": year, "value": number, "attribute_id": attr_id,
            "attribute": attribute, "status": "attribute_unknown" if unknown else ("missing" if number is None else "available"),
            "source_value": raw}


def compare(client, unit_ids, variable_ids, year=None):
    units = [unit_details(client, unit_id) for unit_id in unit_ids]
    if len({unit["level"] for unit in units}) != 1:
        raise SkillError("Porównuj jednostki tego samego poziomu BDL (np. gminy z gminami, powiaty z powiatami).")
    variables = [metadata(client, variable_id) for variable_id in variable_ids]
    attribute_data = client.fetch("attributes")
    attribute_rows = results(attribute_data)
    # The official AttributeList is unpaginated (no page/page-size parameters).
    # Never treat a truncated dictionary as unknown/missing statistical values.
    if attribute_data.get("totalRecords", len(attribute_rows)) != len(attribute_rows):
        raise SkillError("Niepełny słownik atrybutów BDL.", "upstream_format", 69)
    attributes = {str(row["id"]): row for row in attribute_rows if "id" in row}
    if len(attributes) != len(attribute_rows):
        raise SkillError("Nieprawidłowe identyfikatory słownika atrybutów BDL.", "upstream_format", 69)
    series = {}
    for unit in units:
        params = [("var-id", variable_id) for variable_id in variable_ids] + [("page-size", 100)]
        if year is not None:
            params.append(("year", year))
        data = client.fetch("data/by-unit/" + unit["id"], params, ttl=3600)
        if data.get("unitId") != unit["id"]:
            raise SkillError("BDL zwrócił dane innej jednostki.", "upstream_format", 69)
        rows = results(data)
        if data.get("totalRecords", len(rows)) > len(rows):
            raise SkillError("Niepełna strona danych BDL; zawęź liczbę wskaźników.", "upstream_pagination", 69)
        indexed = {}
        for row in rows:
            if str(row.get("id")) not in {str(v) for v in variable_ids}:
                raise SkillError("BDL zwrócił niezamówiony wskaźnik.", "upstream_format", 69)
            if str(row.get("id")) in indexed or not isinstance(row.get("values"), list):
                raise SkillError("Powtórzone lub niepełne szeregi danych BDL.", "upstream_format", 69)
            values = {}
            for value in row["values"]:
                try:
                    item = observation(value, attributes)
                except (ValueError, TypeError, KeyError, AttributeError):
                    raise SkillError("Nieprawidłowy rok lub wartość BDL.", "upstream_format", 69)
                if item["year"] in values:
                    raise SkillError("Powtórzony rok w szeregu BDL.", "upstream_format", 69)
                values[item["year"]] = item
            indexed[str(row["id"])] = {"measure_unit_id": row.get("measureUnitId"),
                                        "last_update": row.get("lastUpdate"), "values": values}
        series[unit["id"]] = indexed
    comparisons = []
    for variable in variables:
        key = str(variable["id"])
        years = []
        for unit in units:
            record = series[unit["id"]].get(key, {})
            measure_id = record.get("measure_unit_id")
            if measure_id is not None and measure_id != variable.get("measureUnitId"):
                raise SkillError("Niezgodne jednostki miary w danych BDL.", "upstream_format", 69)
            years.append({y for y, value in record.get("values", {}).items() if value["value"] is not None})
        common = set.intersection(*years)
        selected = year if year is not None else (max(common) if common else None)
        values = []
        for unit in units:
            record = series[unit["id"]].get(key, {})
            item = record.get("values", {}).get(selected) if selected is not None else None
            values.append({"unit_id": unit["id"], "unit_name": unit.get("name"),
                           "observation": item, "last_update": record.get("last_update"),
                           "available_years": sorted(record.get("values", {})),
                           "numeric_years": sorted(y for y, v in record.get("values", {}).items() if v["value"] is not None)})
        comparisons.append({"indicator": variable, "year": selected,
                            "status": "comparable" if selected in common else "no_common_data",
                            "values": values})
    return {"units": units, "level": units[0]["level"], "level_name": LEVELS[units[0]["level"]],
            "year_policy": "explicit" if year is not None else "latest_common_per_indicator",
            "comparisons": comparisons,
            "note": "Rok jest wspólny dla jednostek, osobno dla każdego wskaźnika. Uwzględnij metadane i atrybuty. Brak danych nie oznacza zera; różne rodzaje gmin mają różny zakres terytorialny."}


def main(argv=None):
    parser = Parser(description="Statystyki gmin i powiatów z oficjalnego GUS BDL (JSON).")
    parser.add_argument("--no-cache", action="store_true", help="Pomiń lokalny cache; metadane 24 h, dane 1 h.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    for name, help_text in (("units", "Wyszukaj jednostki terytorialne."), ("indicators", "Wyszukaj wskaźniki po nazwie wymiarów.")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("query")
        p.add_argument("--level", type=int, choices=range(7), help="0 Polska, 2 województwo, 5 powiat, 6 gmina.")
        p.add_argument("--limit", type=int, default=20, choices=range(1, 101), metavar="1..100")
        p.add_argument("--page", type=int, default=0, help="Numer strony od 0.")
    p = sub.add_parser("indicator", help="Pełna definicja wskaźnika i lata dostępności.")
    p.add_argument("id", type=indicator)
    p = sub.add_parser("compare", help="Porównaj 1–10 jednostek tego samego poziomu.")
    p.add_argument("--units", nargs="+", required=True, type=identifier)
    p.add_argument("--indicators", nargs="+", required=True, type=indicator)
    p.add_argument("--year", type=year_value, help="Bez parametru: najnowszy wspólny rok osobno dla wskaźnika.")
    try:
        args = parser.parse_args(argv)
        client = Client(no_cache=args.no_cache)
        if args.command in ("units", "indicators"):
            if not args.query.strip() or len(args.query) > 200 or not 0 <= args.page <= 10000:
                raise SkillError("Podaj nazwę do 200 znaków i numer strony 0..10000.")
            params = [("name", args.query.strip()), ("page-size", args.limit), ("page", args.page)]
            if args.level is not None:
                params.append(("level", args.level))
            data = client.fetch(("units" if args.command == "units" else "variables") + "/search", params)
            rows = results(data)
            if not rows:
                raise SkillError("Brak wyników GUS BDL.", "not_found", 2)
            total = data.get("totalRecords")
            result = {"results": rows, "page": args.page, "page_size": args.limit, "total_records": total,
                      "has_more": (args.page + 1) * args.limit < total if isinstance(total, int) else None}
        elif args.command == "indicator":
            result = metadata(client, args.id)
        else:
            if not 1 <= len(args.units) <= 10 or not 1 <= len(args.indicators) <= 5:
                raise SkillError("Podaj 1–10 jednostek i 1–5 wskaźników.")
            if len(set(args.units)) != len(args.units) or len(set(args.indicators)) != len(args.indicators):
                raise SkillError("Nie powtarzaj jednostek ani wskaźników.")
            result = compare(client, args.units, args.indicators, args.year)
        output = {"source": SOURCE, "source_url": "https://bdl.stat.gov.pl/", "license": "CC BY 4.0",
                  "fetched_at": stamp(), "requests": client.responses, "result": result}
        print(json.dumps(output, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        print(json.dumps(dict(error=str(exc), type=exc.kind, **exc.details), ensure_ascii=False), file=sys.stderr)
        return exc.code
    except (ValueError, TypeError, KeyError, AttributeError):
        print(json.dumps({"error": "Nieprawidłowa struktura danych GUS BDL.", "type": "upstream_format"}), file=sys.stderr)
        return 69


if __name__ == "__main__":
    sys.exit(main())
