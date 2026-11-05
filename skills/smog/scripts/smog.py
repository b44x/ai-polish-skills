#!/usr/bin/env python3
"""Official GIOŚ stations, measurements and air quality index; Python 3.8+ stdlib."""

import argparse
import datetime as dt
import json
import math
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.gios.gov.pl/pjp-api/v1/rest/"
STATIONS = "Lista stacji pomiarowych"
SENSORS = "Lista stanowisk pomiarowych dla podanej stacji"
DATA = "Lista danych pomiarowych"


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64):
        super().__init__(message)
        self.kind, self.code = kind, code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def fetch(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ai-polish-skills-smog/1.0.0", "Accept": "application/ld+json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SkillError("Brak danych GIOŚ dla wskazanego zasobu.", "not_found", 2)
        raise SkillError("GIOŚ HTTP " + str(exc.code), "upstream_error", 69)
    except (urllib.error.URLError, OSError) as exc:
        raise SkillError("Błąd połączenia z GIOŚ: " + str(exc), "network_error", 69)
    except (ValueError, UnicodeError):
        raise SkillError("Nieprawidłowa odpowiedź JSON GIOŚ.", "upstream_format", 69)


def collection(path, key):
    rows = []
    page = 0
    while True:
        data = fetch(path, {"page": page, "size": 500})
        batch, pages = data.get(key), data.get("totalPages")
        if not isinstance(batch, list) or not all(isinstance(r, dict) for r in batch) or not isinstance(pages, int) or not 0 <= pages <= 100:
            raise SkillError("Nieprawidłowa kolekcja lub paginacja GIOŚ.", "upstream_format", 69)
        rows.extend(batch)
        page += 1
        if page >= pages:
            return rows


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold().replace("ł", "l"))
                   if not unicodedata.combining(c)).strip()


def stations(city=None):
    result = []
    for row in collection("station/findAll", STATIONS):
        if city is not None and normalize(row["Nazwa miasta"]) != normalize(city):
            continue
        result.append({
            "id": row["Identyfikator stacji"], "name": row["Nazwa stacji"],
            "city": row["Nazwa miasta"], "voivodeship": row.get("Województwo"),
            "street": row.get("Ulica"),
            "latitude": float(row["WGS84 φ N"]), "longitude": float(row["WGS84 λ E"]),
        })
    if not result:
        raise SkillError("Nie znaleziono stacji GIOŚ dla podanego miasta.", "not_found", 2)
    return result


def distance(lat, lon, row):
    a, b = math.radians(lat), math.radians(row["latitude"])
    delta = math.radians(row["longitude"] - lon)
    h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(delta / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def latest(sensor):
    sensor_id = sensor["Identyfikator stanowiska"]
    result = {"sensor_id": sensor_id, "pollutant": sensor["Wskaźnik - kod"],
              "unit": "µg/m³", "value": None, "measured_at": None, "latest_slot_at": None}
    try:
        rows = collection("data/getData/" + str(sensor_id), DATA)
    except SkillError as exc:
        if exc.code != 2:
            raise
        result["status"] = "no_current_data"
        return result
    rows.sort(key=lambda r: r["Data"], reverse=True)
    result["latest_slot_at"] = rows[0]["Data"] if rows else None
    available = next((r for r in rows if r.get("Wartość") is not None), None)
    if available is not None:
        value = available["Wartość"]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise SkillError("Nieprawidłowa wartość pomiaru GIOŚ.", "upstream_format", 69)
        result.update(value=value, measured_at=available["Data"])
    result["status"] = ("no_current_data" if available is None else
                        "latest_slot_missing" if available["Data"] != result["latest_slot_at"] else "available")
    return result


def station(identifier, catalog=None):
    catalog = stations() if catalog is None else catalog
    row = next((r for r in catalog if r["id"] == identifier), None)
    if row is None:
        raise SkillError("Nie znaleziono stacji GIOŚ.", "not_found", 2)
    try:
        index = fetch("aqindex/getIndex/" + str(identifier))["AqIndex"]
        if not isinstance(index, dict):
            raise ValueError("Invalid index")
    except SkillError as exc:
        if exc.code != 2:
            raise
        index = {}
    sensors = collection("station/sensors/" + str(identifier), SENSORS)
    return {
        "station": row,
        "index": {"value": index.get("Wartość indeksu"), "category": index.get("Nazwa kategorii indeksu"),
                  "calculated_at": index.get("Data wykonania obliczeń indeksu"),
                  "measured_at": index.get("Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika st"),
                  "status": index.get("Status indeksu ogólnego dla stacji pomiarowej")},
        "measurements": [latest(sensor) for sensor in sensors],
        "measurement_timezone": "Europe/Warsaw",
        "note": "Dane GIOŚ są wstępne. Czas pomiaru może różnić się między czujnikami; brak pomiaru nie oznacza zera.",
    }


def positive(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Wymagana dodatnia liczba całkowita.")
    if number <= 0:
        raise argparse.ArgumentTypeError("Wymagana dodatnia liczba całkowita.")
    return number


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True)
        listing = commands.add_parser("stations", help="Lista stacji; przy wielu wynikach wybierz ID")
        listing.add_argument("--city")
        nearby = commands.add_parser("near", help="Pomiary z najbliższej stacji")
        nearby.add_argument("latitude", type=float)
        nearby.add_argument("longitude", type=float)
        detail = commands.add_parser("station", help="Pomiary i indeks stacji")
        detail.add_argument("id", type=positive)
        args = parser.parse_args(argv)
        if args.command == "stations":
            if args.city is not None and not args.city.strip():
                raise SkillError("Nazwa miasta nie może być pusta.")
            result = {"stations": stations(args.city)}
        elif args.command == "station":
            result = station(args.id)
        else:
            if not (-90 <= args.latitude <= 90 and -180 <= args.longitude <= 180):
                raise SkillError("Współrzędne poza zakresem: szerokość -90..90, długość -180..180.")
            catalog = stations()
            row = min(catalog, key=lambda s: distance(args.latitude, args.longitude, s))
            result = station(row["id"], catalog)
            result["distance_km"] = round(distance(args.latitude, args.longitude, row), 2)
        result.update(source="GIOŚ", source_url=BASE,
                      fetched_at=dt.datetime.now(dt.timezone.utc).isoformat())
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return report(SkillError("Nieprawidłowa struktura danych GIOŚ: " + str(exc), "upstream_format", 69))
    except SkillError as exc:
        return report(exc)


def report(exc):
    print(json.dumps({"error": str(exc), "type": exc.kind}, ensure_ascii=False), file=sys.stderr)
    return exc.code


if __name__ == "__main__":
    sys.exit(main())
