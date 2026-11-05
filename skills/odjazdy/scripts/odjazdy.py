#!/usr/bin/env python3
"""Stop lookup and departure boards from three Polish transport providers; stdlib only."""

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

UTC = dt.timezone.utc
PEKA = "https://www.peka.poznan.pl/vm/method.vm"
GD_STOPS = "https://ckan.multimediagdansk.pl/dataset/tristar/resource/4c4025f0-01bf-41f7-a39f-d156d201b82b/download/stops.json"
SZ = "https://www.zditm.szczecin.pl/api/v2/"
PROVIDERS = {
    "gdansk": {"city": "Gdańsk", "source": "ZTM Gdańsk / Otwarty Gdańsk", "homepage": "https://ckan.multimediagdansk.pl/dataset/tristar", "license": "CC BY", "gps_search": True, "coverage": "Przystanki i kursy publikowane przez ZTM Gdańsk, także poza granicą miasta."},
    "poznan": {"city": "Poznań", "source": "ZTM Poznań / PEKA Wirtualny Monitor", "homepage": "https://www.peka.poznan.pl/vm/", "license": "Zasady ponownego wykorzystania ZTM Poznań", "gps_search": False, "coverage": "Przystanki aglomeracji poznańskiej dostępne w Wirtualnym Monitorze PEKA; tablica obejmuje najbliższe około 30 minut."},
    "szczecin": {"city": "Szczecin", "source": "ZDiTM Szczecin", "homepage": "https://www.zditm.szczecin.pl/pl/zditm/dla-programistow/api-tablice-odjazdow", "license": "CC0 1.0", "gps_search": True, "coverage": "Przystanki i kursy publikowane przez ZDiTM Szczecin, także poza granicą miasta."},
}


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64):
        super().__init__(message)
        self.kind, self.code = kind, code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold().replace("ł", "l")) if not unicodedata.combining(c)).strip()


def text(value):
    # Some ZDiTM strings contain literal JSON Unicode escapes after JSON decoding.
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), str(value))


def now():
    return dt.datetime.now(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def timestamp(value):
    if not value:
        return None
    try:
        result = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(UTC)
    except ValueError:
        return None


def request(url, form=None, ttl=0):
    """Respect upstream max-age/ETag; expired responses never mask an outage."""
    cache_root = Path(os.environ.get("ODJAZDY_CACHE_DIR", str(Path.home() / ".cache" / "ai-polish-skills" / "odjazdy")))
    cache_file = cache_root / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    cached = None
    if form is None:
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached["url"] == url and cached["expires"] > time.time():
                return cached["data"]
        except (OSError, ValueError, KeyError, TypeError):
            cached = None
    headers = {"User-Agent": "ai-polish-skills-odjazdy/1.0.0 (+https://github.com/b44x/ai-polish-skills)", "Accept": "application/json"}
    if cached and cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    body = urllib.parse.urlencode(form).encode() if form is not None else None
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read(20_000_001)
            if len(raw) > 20_000_000:
                raise ValueError("Response too large")
            data = json.loads(raw)
            control = response.headers.get("Cache-Control", "")
            age = response.headers.get("Age", "0")
            match = re.search(r"(?:^|,)\s*max-age=(\d+)", control)
            lifetime = max(0, int(match.group(1)) - int(age)) if match else ttl
            if "no-cache" in control or "no-store" in control:
                lifetime = 0
            if form is None and "no-store" not in control:
                entry = {"url": url, "expires": time.time() + lifetime, "etag": response.headers.get("ETag"), "data": data}
                try:
                    cache_root.mkdir(parents=True, exist_ok=True)
                    temporary = cache_file.with_suffix("." + str(os.getpid()) + ".tmp")
                    temporary.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
                    temporary.replace(cache_file)
                except OSError:
                    pass
            return data
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and cached:
            exc.close()
            return cached["data"]
        if exc.code == 404:
            raise SkillError("Nie znaleziono zasobu lub przystanku u dostawcy.", "not_found", 2)
        raise SkillError("API HTTP " + str(exc.code) + ("; limit zapytań, spróbuj później." if exc.code == 429 else ""), "upstream_error", 69)
    except (urllib.error.URLError, OSError) as exc:
        raise SkillError("Błąd połączenia z dostawcą: " + str(exc), "network_error", 69)
    except (ValueError, UnicodeError):
        raise SkillError("Nieprawidłowa odpowiedź JSON dostawcy.", "upstream_format", 69)


def peka(method, params=None):
    form = {"method": method}
    if params is not None:
        form["p0"] = json.dumps(params, ensure_ascii=False)
    data = request(PEKA, form)
    if not isinstance(data, dict) or "success" not in data:
        raise SkillError("PEKA nie zwróciła poprawnego wyniku.", "upstream_format", 69)
    return data["success"]


def rows(value):
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise SkillError("Nieprawidłowa lista danych dostawcy.", "upstream_format", 69)
    return value


def city_id(value):
    city = normalize(value)
    if city not in PROVIDERS:
        raise SkillError("Nieobsługiwane miasto. Dostępne: gdansk, poznan, szczecin. Użyj cities.")
    return city


def haversine(lat, lon, row):
    a, b = math.radians(lat), math.radians(row["latitude"])
    h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(row["longitude"] - lon) / 2) ** 2
    return round(6371000 * 2 * math.asin(math.sqrt(min(1, max(0, h)))))


def stop_search(city, query=None, lat=None, lon=None, limit=10):
    updated = None
    truncated = False
    if city == "poznan":
        if lat is not None:
            raise SkillError("Poznań: wyszukiwanie PEKA wymaga nazwy przystanku; GPS obsługują Gdańsk i Szczecin.")
        if not query:
            raise SkillError("Poznań: podaj --query, np. 'Rondo Kaponiera'.")
        groups = rows(peka("getStopPoints", {"pattern": query}))
        result = []
        # Provider limits autocomplete results. Resolve at most three matched groups.
        truncated = len(groups) > 3
        for group in groups[:3]:
            payload = peka("getBollardsByStopPoint", {"name": group["name"]})
            for item in rows(payload["bollards"]):
                b = item["bollard"]
                result.append({"id": b.get("tag") or b["symbol"], "public_code": b["symbol"], "name": b["name"], "latitude": None, "longitude": None, "directions": [{"line": r.get("lineName"), "destination": r.get("direction")} for r in item.get("directions", [])]})
    elif city == "gdansk":
        data = request(GD_STOPS, ttl=3600)
        # Daily bundles include future timetables; never take an arbitrary first key.
        today = warsaw_date(now()).isoformat()
        available = sorted(k for k in data if re.fullmatch(r"\d{4}-\d{2}-\d{2}", k) and k <= today)
        if not available:
            raise SkillError("Brak katalogu przystanków na bieżący dzień.", "upstream_format", 69)
        bundle = data[available[-1]]
        updated = bundle.get("lastUpdate")
        result = [{"id": str(r["stopId"]), "public_code": r.get("stopCode"), "name": r["stopDesc"] or r["stopName"], "latitude": float(r["stopLat"]), "longitude": float(r["stopLon"]), "type": r.get("type")} for r in rows(bundle["stops"]) if not r.get("nonpassenger") and not r.get("virtual")]
    else:
        data = request(SZ + "stops")
        result = [{"id": r["number"], "public_code": r["number"], "name": text(r["name"]), "latitude": float(r["latitude"]), "longitude": float(r["longitude"]), "updated_at": r.get("updated_at")} for r in rows(data["data"]) if not r.get("technical")]
    if query and city != "poznan":
        result = [r for r in result if normalize(query) in normalize(r["name"]) or query == r["id"]]
    if lat is not None:
        for row in result:
            row["distance_m"] = haversine(lat, lon, row)
        result.sort(key=lambda r: (r["distance_m"], r["id"]))
    elif city != "poznan":
        result.sort(key=lambda r: (normalize(r["name"]), r["id"]))
    if not result:
        raise SkillError("Nie znaleziono przystanków; spróbuj innej nazwy.", "not_found", 2)
    return {"stops": result[:limit], "matched_count": len(result), "truncated": truncated or len(result) > limit, "source_updated_at": updated, "source_timezone": "Europe/Warsaw" if city == "gdansk" else "UTC", "note": "PEKA zwraca ograniczoną listę podpowiedzi; przy niejednoznaczności doprecyzuj nazwę." if city == "poznan" else "Odległość jest liczona w linii prostej." if lat is not None else None}


def warsaw_date(value):
    # EU DST rules since 1996; Python 3.8 has no zoneinfo dependency.
    year = value.year
    def last_sunday(month):
        end = dt.datetime(year, month + 1, 1, tzinfo=UTC) - dt.timedelta(days=1)
        return end.replace(hour=1) - dt.timedelta(days=(end.weekday() + 1) % 7)
    offset = 2 if last_sunday(3) <= value < last_sunday(10) else 1
    return (value + dt.timedelta(hours=offset)).date()


def departure(line, destination, scheduled=None, estimated=None, realtime=False, canceled=False):
    for value in (scheduled, estimated):
        if value is not None and timestamp(value) is None:
            raise SkillError("Nieprawidłowy czas odjazdu dostawcy.", "upstream_format", 69)
    return {"line": str(line), "destination": text(destination), "scheduled_at": scheduled, "estimated_at": estimated if realtime else None, "realtime": realtime, "status": "canceled" if canceled else "realtime" if realtime else "scheduled", "canceled": canceled, "delay_seconds": None}


def departures(city, stop, limit=10, line=None):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", stop):
        raise SkillError("Nieprawidłowy identyfikator przystanku; użyj stops.")
    result, warnings, messages = [], [], []
    name = None
    updated = None
    if city == "gdansk":
        if not stop.isdigit():
            raise SkillError("Gdańsk: stopId musi być liczbą z komendy stops.")
        data = request("https://ckan2.multimediagdansk.pl/departures?" + urllib.parse.urlencode({"stopId": stop}))
        updated = data.get("lastUpdate")
        for r in rows(data["departures"]):
            real = r.get("status") == "REALTIME"
            item = departure(r.get("routeShortName", r["routeId"]), r.get("headsign", ""), r.get("theoreticalTime"), r.get("estimatedTime"), real)
            item.update(delay_seconds=r.get("delayInSeconds") if real else None, vehicle_updated_at=r.get("timestamp"))
            result.append(item)
    elif city == "szczecin":
        if not stop.isdigit():
            raise SkillError("Szczecin: numer przystanku musi być liczbą z komendy stops.")
        data = request(SZ + "departure-boards/" + stop + "?limit=" + str(100 if line else limit))["data"]
        name = data["stop"]["name"]
        updated = data.get("updated_at")
        messages = [text(m) for m in data.get("messages", [])]
        for r in rows(data["departures"]):
            t = r["departure_time"]
            item = departure(r["line"]["number"], r["trip"]["headsign"]["long"], t.get("scheduled"), t.get("estimated"), t.get("real_time") is True, t.get("canceled") is True)
            scheduled, estimated = timestamp(item["scheduled_at"]), timestamp(item["estimated_at"])
            if scheduled and estimated:
                item["delay_seconds"] = round((estimated - scheduled).total_seconds())
            item["departing_now"] = t.get("departing_now")
            result.append(item)
    else:
        data = peka("getTimes", {"symbol": stop})
        if not isinstance(data, dict) or not isinstance(data.get("bollard"), dict):
            raise SkillError("Nie znaleziono tablicy PEKA.", "not_found", 2)
        name = data["bollard"].get("name")
        server_ms = peka("getServerTime")
        if not isinstance(server_ms, (int, float)) or isinstance(server_ms, bool) or not math.isfinite(server_ms):
            raise SkillError("Nieprawidłowy zegar PEKA.", "upstream_format", 69)
        server = dt.datetime.fromtimestamp(server_ms / 1000, UTC)
        for r in rows(data["times"]):
            minutes = r.get("minutes")
            if not isinstance(minutes, (int, float)) or isinstance(minutes, bool) or not math.isfinite(minutes):
                raise SkillError("Nieprawidłowa liczba minut PEKA.", "upstream_format", 69)
            real = r.get("realTime") is True
            item = departure(r["line"], r["direction"], estimated=iso(server + dt.timedelta(minutes=minutes)), realtime=real)
            # PEKA encodes Warsaw wall-clock times with literal Z; its frontend
            # parses them as local. Do not incorrectly shift these by 1–2 hours.
            item.update(minutes=minutes, scheduled_local=str(r.get("departure", "")).rstrip("Z"), scheduled_timezone="Europe/Warsaw", provider_departure_raw=r.get("departure"), time_basis="provider_minutes" if real else "provider_local_schedule", departing_now=r.get("onStopPoint"))
            result.append(item)
        warnings.append("PEKA nie publikuje czasu aktualizacji pomiaru. Czas serwera i pobrania nie potwierdza świeżości pozycji pojazdu. estimated_at jest przybliżeniem z minut dostawcy; scheduled_local to czas Europe/Warsaw mimo Z w surowej odpowiedzi.")
    if line is not None:
        result = [r for r in result if r["line"] == line]
    update = timestamp(updated)
    age = round((now() - update).total_seconds()) if update else None
    freshness = "unknown" if age is None else "stale" if age > 180 or age < -60 else "current"
    if freshness == "stale":
        warnings.append("Tablica ma nieaktualny czas źródłowy. Nie traktuj prognoz jako bieżących.")
    for item in result:
        measured = timestamp(item.get("vehicle_updated_at"))
        measurement_age = (now() - measured).total_seconds() if measured else None
        item["measurement_stale"] = measurement_age > 180 or measurement_age < -60 if measured else None
        item["usable_realtime"] = item["realtime"] and timestamp(item["estimated_at"]) is not None and not item["canceled"] and freshness == "current" and item["measurement_stale"] is not True
    return {"stop": {"id": stop, "name": text(name) if name else None}, "departures": result[:limit], "status": "available" if result else "no_departures", "source_updated_at": updated, "source_age_seconds": age, "freshness": freshness, "messages": messages, "warnings": warnings, "timezone": "UTC", "note": "Brak odjazdów oznacza pustą tablicę w zakresie dostawcy lub filtra; nie dowodzi braku kursów przez cały dzień." if not result else None}


def main(argv=None):
    try:
        parser = Parser(description="Przystanki i odjazdy: Gdańsk, Poznań i Szczecin. Python 3.8+, bez kluczy API.")
        sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
        sub.add_parser("cities", help="Obsługiwane miasta, źródła i zakres funkcji (offline)")
        p = sub.add_parser("stops", help="Znajdź przystanki i ich identyfikatory")
        p.add_argument("city")
        p.add_argument("--query")
        p.add_argument("--lat", type=float)
        p.add_argument("--lon", type=float)
        p.add_argument("--limit", type=int, default=10)
        p = sub.add_parser("departures", help="Tablica odjazdów konkretnego słupka")
        p.add_argument("city")
        p.add_argument("stop")
        p.add_argument("--line")
        p.add_argument("--limit", type=int, default=10)
        args = parser.parse_args(argv)
        if args.command == "cities":
            result = {"cities": [dict(id=k, authentication="none", departures=True, realtime_available=True, **v) for k, v in PROVIDERS.items()], "coverage": "Trzy obsługiwane sieci, nie cała Polska; dostępność danych na żywo zależy od kursu i dostawcy."}
        else:
            city = city_id(args.city)
            if not 1 <= args.limit <= 100:
                raise SkillError("--limit musi wynosić od 1 do 100.")
            if args.command == "stops":
                if (args.lat is None) != (args.lon is None):
                    raise SkillError("Podaj jednocześnie --lat i --lon.")
                if args.lat is not None and (not math.isfinite(args.lat) or not math.isfinite(args.lon) or not -90 <= args.lat <= 90 or not -180 <= args.lon <= 180):
                    raise SkillError("Nieprawidłowe współrzędne GPS.")
                if args.query is not None and not args.query.strip():
                    raise SkillError("--query nie może być puste.")
                result = stop_search(city, args.query, args.lat, args.lon, args.limit)
            else:
                if args.line is not None and not args.line.strip():
                    raise SkillError("--line nie może być puste.")
                result = departures(city, args.stop, args.limit, args.line)
            result.update(city=city, source=PROVIDERS[city]["source"], source_url=PROVIDERS[city]["homepage"], license=PROVIDERS[city]["license"], processed=True)
        result["fetched_at"] = iso(now())
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        print(json.dumps({"error": str(exc), "type": exc.kind}, ensure_ascii=False), file=sys.stderr)
        return exc.code
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        print(json.dumps({"error": "Nieprawidłowy format danych dostawcy: " + str(exc), "type": "upstream_format"}, ensure_ascii=False), file=sys.stderr)
        return 69


if __name__ == "__main__":
    sys.exit(main())
