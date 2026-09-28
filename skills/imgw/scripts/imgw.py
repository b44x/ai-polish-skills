#!/usr/bin/env python3
"""CLI for Instytut Meteorologii i Gospodarki Wodnej (IMGW-PIB) official open data.

Fetches official weather observations (synop), warnings (meteo & hydro),
and hydrological river measurements for Poland.

Official API: https://danepubliczne.imgw.pl/api/
Zero external dependencies (Python 3.8+ standard library only).

Copyright (c) 2026 Michell Hoduń <mhodun@gmail.com> (https://github.com/b44x)
Licensed under the MIT License.
"""

import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

API_BASE_URL = "https://danepubliczne.imgw.pl/api/data"

# Verified catalogue of all 62 synoptic weather stations operated by IMGW-PIB with WMO coordinates.
SYNOP_STATIONS: Dict[str, Dict[str, Any]] = {
    "12001": {"name": "Platforma", "slug": "platforma", "lat": 55.48, "lon": 18.17},
    "12100": {"name": "Kołobrzeg", "slug": "kolobrzeg", "lat": 54.18, "lon": 16.18},
    "12105": {"name": "Koszalin", "slug": "koszalin", "lat": 54.20, "lon": 16.18},
    "12115": {"name": "Ustka", "slug": "ustka", "lat": 54.58, "lon": 16.85},
    "12120": {"name": "Łeba", "slug": "leba", "lat": 54.75, "lon": 17.53},
    "12125": {"name": "Lębork", "slug": "lebork", "lat": 54.55, "lon": 17.75},
    "12135": {"name": "Hel", "slug": "hel", "lat": 54.60, "lon": 18.82},
    "12155": {"name": "Gdańsk", "slug": "gdansk", "lat": 54.38, "lon": 18.60},
    "12160": {"name": "Elbląg", "slug": "elblag", "lat": 54.17, "lon": 19.43},
    "12185": {"name": "Kętrzyn", "slug": "ketrzyn", "lat": 54.08, "lon": 21.36},
    "12195": {"name": "Suwałki", "slug": "suwalki", "lat": 54.13, "lon": 22.95},
    "12200": {"name": "Świnoujście", "slug": "swinoujscie", "lat": 53.92, "lon": 14.23},
    "12205": {"name": "Szczecin", "slug": "szczecin", "lat": 53.40, "lon": 14.62},
    "12210": {"name": "Resko", "slug": "resko", "lat": 53.77, "lon": 15.40},
    "12215": {"name": "Szczecinek", "slug": "szczecinek", "lat": 53.71, "lon": 16.69},
    "12230": {"name": "Piła", "slug": "pila", "lat": 53.13, "lon": 16.75},
    "12235": {"name": "Chojnice", "slug": "chojnice", "lat": 53.70, "lon": 17.55},
    "12250": {"name": "Toruń", "slug": "torun", "lat": 53.03, "lon": 18.60},
    "12270": {"name": "Mława", "slug": "mlawa", "lat": 53.13, "lon": 20.36},
    "12272": {"name": "Olsztyn", "slug": "olsztyn", "lat": 53.77, "lon": 20.48},
    "12280": {"name": "Mikołajki", "slug": "mikolajki", "lat": 53.78, "lon": 21.58},
    "12285": {"name": "Ostrołęka", "slug": "ostroleka", "lat": 53.08, "lon": 21.57},
    "12295": {"name": "Białystok", "slug": "bialystok", "lat": 53.11, "lon": 23.16},
    "12300": {"name": "Gorzów", "slug": "gorzow", "lat": 52.74, "lon": 15.28},
    "12310": {"name": "Słubice", "slug": "slubice", "lat": 52.35, "lon": 14.58},
    "12330": {"name": "Poznań", "slug": "poznan", "lat": 52.42, "lon": 16.83},
    "12345": {"name": "Koło", "slug": "kolo", "lat": 52.20, "lon": 18.63},
    "12360": {"name": "Płock", "slug": "plock", "lat": 52.58, "lon": 19.72},
    "12375": {"name": "Warszawa", "slug": "warszawa", "lat": 52.17, "lon": 20.97},
    "12385": {"name": "Siedlce", "slug": "siedlce", "lat": 52.25, "lon": 22.26},
    "12399": {"name": "Terespol", "slug": "terespol", "lat": 52.07, "lon": 23.62},
    "12400": {"name": "Zielona Góra", "slug": "zielonagora", "lat": 51.93, "lon": 15.53},
    "12415": {"name": "Legnica", "slug": "legnica", "lat": 51.18, "lon": 16.18},
    "12418": {"name": "Leszno", "slug": "leszno", "lat": 51.83, "lon": 16.53},
    "12424": {"name": "Wrocław", "slug": "wroclaw", "lat": 51.11, "lon": 16.89},
    "12435": {"name": "Kalisz", "slug": "kalisz", "lat": 51.78, "lon": 18.08},
    "12455": {"name": "Wieluń", "slug": "wielun", "lat": 51.22, "lon": 18.57},
    "12465": {"name": "Łódź", "slug": "lodz", "lat": 51.73, "lon": 19.40},
    "12469": {"name": "Sulejów", "slug": "sulejow", "lat": 51.35, "lon": 19.87},
    "12488": {"name": "Kozienice", "slug": "kozienice", "lat": 51.56, "lon": 21.53},
    "12495": {"name": "Lublin", "slug": "lublin", "lat": 51.22, "lon": 22.68},
    "12497": {"name": "Włodawa", "slug": "wlodawa", "lat": 51.55, "lon": 23.53},
    "12500": {"name": "Jelenia Góra", "slug": "jeleniagora", "lat": 50.90, "lon": 15.80},
    "12510": {"name": "Śnieżka", "slug": "sniezka", "lat": 50.74, "lon": 15.74},
    "12520": {"name": "Kłodzko", "slug": "klodzko", "lat": 50.43, "lon": 16.65},
    "12530": {"name": "Opole", "slug": "opole", "lat": 50.63, "lon": 17.96},
    "12540": {"name": "Racibórz", "slug": "raciborz", "lat": 50.06, "lon": 18.19},
    "12550": {"name": "Częstochowa", "slug": "czestochowa", "lat": 50.81, "lon": 19.10},
    "12560": {"name": "Katowice", "slug": "katowice", "lat": 50.24, "lon": 19.03},
    "12566": {"name": "Kraków", "slug": "krakow", "lat": 50.08, "lon": 19.80},
    "12570": {"name": "Kielce", "slug": "kielce", "lat": 50.81, "lon": 20.69},
    "12575": {"name": "Tarnów", "slug": "tarnow", "lat": 50.03, "lon": 20.98},
    "12580": {"name": "Rzeszów", "slug": "rzeszow", "lat": 50.10, "lon": 22.02},
    "12585": {"name": "Sandomierz", "slug": "sandomierz", "lat": 50.70, "lon": 21.73},
    "12595": {"name": "Zamość", "slug": "zamosc", "lat": 50.70, "lon": 23.25},
    "12600": {"name": "Bielsko Biała", "slug": "bielskobiala", "lat": 49.80, "lon": 19.00},
    "12625": {"name": "Zakopane", "slug": "zakopane", "lat": 49.30, "lon": 19.96},
    "12650": {"name": "Kasprowy Wierch", "slug": "kasprowywierch", "lat": 49.23, "lon": 19.98},
    "12660": {"name": "Nowy Sącz", "slug": "nowysacz", "lat": 49.62, "lon": 20.70},
    "12670": {"name": "Krosno", "slug": "krosno", "lat": 49.70, "lon": 21.77},
    "12690": {"name": "Lesko", "slug": "lesko", "lat": 49.47, "lon": 22.33},
    "12695": {"name": "Przemyśl", "slug": "przemysl", "lat": 49.80, "lon": 22.77},
}

DIACRITICS_MAP = {
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ź": "z", "ż": "z",
}


def normalize_slug(text: str) -> str:
    """Normalize Polish text into a clean alphanumeric slug."""
    text = text.lower().strip()
    for char, replacement in DIACRITICS_MAP.items():
        text = text.replace(char, replacement)
    return re.sub(r"[^a-z0-9]", "", text)


def normalize_search(text: str) -> str:
    """Normalize Polish text for case/accent-insensitive search comparison."""
    text = text.lower().strip()
    for char, replacement in DIACRITICS_MAP.items():
        text = text.replace(char, replacement)
    return text


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_km * c


def error_exit(message: str, error_type: str = "error", code: int = 64) -> None:
    """Print structured error JSON to stderr and exit with the specified code."""
    json.dump({"error": message, "type": error_type}, sys.stderr, ensure_ascii=False)
    sys.stderr.write("\n")
    sys.exit(code)


def fetch_api(path: str) -> Any:
    """Execute GET request against IMGW-PIB API."""
    url = f"{API_BASE_URL}/{path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ai-polish-skills-imgw/1.0.0 (+https://github.com/b44x/ai-polish-skills)",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass

        if e.code == 404:
            error_exit(
                f"Brak danych w IMGW dla podanego zapytania: {body or '404 Not Found'}",
                "not_found",
                2,
            )
        elif e.code == 400:
            error_exit(f"Nieprawidłowe zapytanie do IMGW API: {body}", "bad_request", 64)
        else:
            error_exit(f"Błąd serwera IMGW-PIB (HTTP {e.code}): {body}", "server_error", 69)
    except urllib.error.URLError as e:
        error_exit(f"Błąd połączenia z serwerem IMGW-PIB: {e.reason}", "network_error", 69)
    except json.JSONDecodeError as e:
        error_exit(f"Błąd parsowania odpowiedzi JSON z IMGW: {e}", "parse_error", 69)
    except Exception as e:
        error_exit(f"Nieoczekiwany błąd: {str(e)}", "unknown_error", 69)
    return None


def parse_float_safe(value: Any) -> Optional[float]:
    """Parse string/number to float, safely handling None or empty strings."""
    if value is None:
        return None
    try:
        val_str = str(value).strip().replace(",", ".")
        return float(val_str)
    except (ValueError, TypeError):
        return None


def parse_int_safe(value: Any) -> Optional[int]:
    """Parse string/number to int, safely handling None or empty strings."""
    if value is None:
        return None
    try:
        val_str = str(value).strip().split(".")[0]
        return int(val_str)
    except (ValueError, TypeError):
        return None


def format_synop_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw synop record into unified schema with units."""
    station_id = str(raw.get("id_stacji", "")).strip()
    station_name = raw.get("stacja", "").strip()
    date_meas = raw.get("data_pomiaru", "").strip()
    hour_meas = parse_int_safe(raw.get("godzina_pomiaru"))

    temp = parse_float_safe(raw.get("temperatura"))
    wind_speed = parse_float_safe(raw.get("predkosc_wiatru"))
    wind_dir = parse_int_safe(raw.get("kierunek_wiatru"))
    humidity = parse_float_safe(raw.get("wilgotnosc_wzgledna"))
    rain = parse_float_safe(raw.get("suma_opadu"))
    pressure = parse_float_safe(raw.get("cisnienie"))

    # Resolve coordinates if station known in catalogue
    coords = None
    if station_id in SYNOP_STATIONS:
        coords = {
            "lat": SYNOP_STATIONS[station_id]["lat"],
            "lon": SYNOP_STATIONS[station_id]["lon"],
        }
    else:
        # Try matching by name
        norm_name = normalize_slug(station_name)
        for s in SYNOP_STATIONS.values():
            if s["slug"] == norm_name:
                coords = {"lat": s["lat"], "lon": s["lon"]}
                break

    time_str = f"{date_meas} {hour_meas:02d}:00 UTC" if date_meas and hour_meas is not None else None

    formatted = {
        "temperature": f"{temp:.1f} °C" if temp is not None else "brak danych",
        "pressure": f"{pressure:.1f} hPa" if pressure is not None else "brak danych (stacja górska lub brak pomiaru)",
        "wind": f"{wind_speed:.1f} m/s ({wind_dir}°)" if wind_speed is not None and wind_dir is not None else "brak danych",
        "humidity": f"{humidity:.1f} %" if humidity is not None else "brak danych",
        "rainfall": f"{rain:.1f} mm" if rain is not None else "brak danych",
    }

    return {
        "stationId": station_id,
        "stationName": station_name,
        "measurementDate": date_meas,
        "measurementHour": hour_meas,
        "measurementTime": time_str,
        "temperatureC": temp,
        "windSpeedMs": wind_speed,
        "windDirectionDeg": wind_dir,
        "relativeHumidityPercent": humidity,
        "rainfallMm": rain,
        "pressureHpa": pressure,
        "formatted": formatted,
        "coordinates": coords,
        "source": "Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy (IMGW-PIB)",
    }


def find_station_id(station_query: str) -> Optional[Tuple[str, str]]:
    """Resolve station identifier or user query to (station_id, station_name)."""
    q_raw = station_query.strip()
    if q_raw in SYNOP_STATIONS:
        return q_raw, SYNOP_STATIONS[q_raw]["name"]

    q_slug = normalize_slug(q_raw)
    q_norm = normalize_search(q_raw)

    # 1. Exact slug match
    for sid, sinfo in SYNOP_STATIONS.items():
        if sinfo["slug"] == q_slug:
            return sid, sinfo["name"]

    # 2. Exact normalized name match
    for sid, sinfo in SYNOP_STATIONS.items():
        if normalize_search(sinfo["name"]) == q_norm:
            return sid, sinfo["name"]

    # 3. Substring match
    matches = []
    for sid, sinfo in SYNOP_STATIONS.items():
        if q_slug in sinfo["slug"] or q_norm in normalize_search(sinfo["name"]):
            matches.append((sid, sinfo["name"]))

    if len(matches) == 1:
        return matches[0]

    return None


def cmd_weather(args: argparse.Namespace) -> None:
    """Fetch current synoptic weather observation for a specific station."""
    query = args.station.strip()
    match = find_station_id(query)

    if match:
        station_id, _ = match
        data = fetch_api(f"synop/id/{station_id}")
    else:
        # Try direct slug query if user entered something custom
        slug = normalize_slug(query)
        if not slug:
            error_exit(f"Nieprawidłowa nazwa stacji: '{query}'", "bad_request", 64)
        try:
            data = fetch_api(f"synop/station/{slug}")
        except SystemExit:
            # Provide helpful recommendations
            suggestions = [
                f"{s['name']} (ID: {sid})"
                for sid, s in SYNOP_STATIONS.items()
                if normalize_slug(query) in s["slug"] or query.lower() in s["name"].lower()
            ]
            msg = f"Nie znaleziono stacji synoptycznej IMGW dla '{query}'."
            if suggestions:
                msg += f" Czy chodziło o: {', '.join(suggestions[:5])}?"
            else:
                msg += " Użyj polecenia 'stations' lub 'near <lat> <lon>', aby znaleźć najbliższą stację."
            error_exit(msg, "not_found", 2)

    if isinstance(data, dict):
        result = format_synop_record(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif isinstance(data, list) and data:
        result = format_synop_record(data[0])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        error_exit(f"Brak danych pogodowych dla stacji '{query}'.", "not_found", 2)


def cmd_synop(args: argparse.Namespace) -> None:
    """Fetch current observations for all synoptic stations with optional sorting and limiting."""
    raw_list = fetch_api("synop")
    if not isinstance(raw_list, list):
        error_exit("Otrzymano nieprawidłowy format danych z IMGW synop.", "server_error", 69)

    records = [format_synop_record(item) for item in raw_list]

    if args.sort == "temp":
        records.sort(key=lambda x: (x["temperatureC"] is None, x["temperatureC"]))
    elif args.sort == "temp_desc":
        records.sort(key=lambda x: (x["temperatureC"] is None, -(x["temperatureC"] or 0)))
    elif args.sort == "wind_desc":
        records.sort(key=lambda x: (x["windSpeedMs"] is None, -(x["windSpeedMs"] or 0)))
    elif args.sort == "pressure_desc":
        records.sort(key=lambda x: (x["pressureHpa"] is None, -(x["pressureHpa"] or 0)))
    elif args.sort == "rain_desc":
        records.sort(key=lambda x: (x["rainfallMm"] is None, -(x["rainfallMm"] or 0)))
    else:
        records.sort(key=lambda x: x["stationName"])

    if args.limit and args.limit > 0:
        records = records[:args.limit]

    output = {
        "count": len(records),
        "source": "Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy (IMGW-PIB)",
        "stations": records,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_near(args: argparse.Namespace) -> None:
    """Find nearest synoptic stations to GPS coordinates."""
    lat = args.lat
    lon = args.lon

    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        error_exit(f"Nieprawidłowe współrzędne GPS: lat={lat}, lon={lon}.", "bad_request", 64)

    ranked: List[Dict[str, Any]] = []
    for sid, sinfo in SYNOP_STATIONS.items():
        dist = haversine_distance_km(lat, lon, sinfo["lat"], sinfo["lon"])
        ranked.append({
            "stationId": sid,
            "stationName": sinfo["name"],
            "slug": sinfo["slug"],
            "coordinates": {"lat": sinfo["lat"], "lon": sinfo["lon"]},
            "distanceKm": round(dist, 1),
        })

    ranked.sort(key=lambda x: x["distanceKm"])
    limit = args.limit or 3
    top_stations = ranked[:limit]

    weather_data = None
    if not args.no_weather and top_stations:
        closest_id = top_stations[0]["stationId"]
        try:
            raw_weather = fetch_api(f"synop/id/{closest_id}")
            if isinstance(raw_weather, dict):
                weather_data = format_synop_record(raw_weather)
        except Exception:
            # Weather fetch optional if only distance was needed
            pass

    output = {
        "queryCoordinates": {"lat": lat, "lon": lon},
        "closestStation": {
            **top_stations[0],
            "weather": weather_data,
        } if top_stations else None,
        "nearbyStations": top_stations,
        "source": "IMGW-PIB",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def normalize_warning(item: Dict[str, Any], warning_type: str) -> Dict[str, Any]:
    """Normalize warning item from meteo or hydro endpoint."""
    level = item.get("stopień")
    parsed_level = parse_int_safe(level)

    regions: List[str] = []
    raw_obszary = item.get("obszary")
    if isinstance(raw_obszary, list):
        for o in raw_obszary:
            if isinstance(o, dict) and o.get("wojewodztwo"):
                regions.append(o.get("wojewodztwo", "").strip())
            elif isinstance(o, str):
                regions.append(o.strip())

    prob = parse_int_safe(item.get("prawdopodobienstwo"))

    return {
        "number": item.get("numer"),
        "type": warning_type,
        "event": item.get("zdarzenie"),
        "level": parsed_level if parsed_level is not None else level,
        "published": item.get("opublikowano"),
        "validFrom": item.get("data_od"),
        "validTo": item.get("data_do"),
        "probabilityPercent": prob,
        "office": item.get("biuro"),
        "course": item.get("przebieg"),
        "comment": item.get("komentarz"),
        "voivodeships": sorted(list(set(regions))),
    }


VOIVODESHIPS = [
    "dolnośląskie", "kujawsko-pomorskie", "lubelskie", "lubuskie",
    "łódzkie", "małopolskie", "mazowieckie", "opolskie",
    "podkarpackie", "podlaskie", "pomorskie", "śląskie",
    "świętokrzyskie", "warmińsko-mazurskie", "wielkopolskie", "zachodniopomorskie",
]
NORM_VOIVS = {normalize_search(v): v for v in VOIVODESHIPS}


def matches_voivodeship(query: str, target: str) -> bool:
    """Accurately match voivodeship query against target without false substring hits."""
    q = normalize_search(query)
    tgt = normalize_search(target)
    if q in NORM_VOIVS:
        return tgt == q
    return q in tgt


def cmd_warnings(args: argparse.Namespace) -> None:
    """Fetch official meteorological and hydrological warnings."""
    warnings: List[Dict[str, Any]] = []
    w_type = args.type.lower()

    if w_type in ("meteo", "all"):
        data_meteo = fetch_api("warningsmeteo")
        if isinstance(data_meteo, list):
            for it in data_meteo:
                warnings.append(normalize_warning(it, "meteo"))
        elif isinstance(data_meteo, dict) and "message" in data_meteo:
            pass  # No warnings

    if w_type in ("hydro", "all"):
        data_hydro = fetch_api("warningshydro")
        if isinstance(data_hydro, list):
            for it in data_hydro:
                warnings.append(normalize_warning(it, "hydro"))
        elif isinstance(data_hydro, dict) and "message" in data_hydro:
            pass  # No warnings

    # Filter by voivodeship if requested
    if args.voivodeship:
        v_query = args.voivodeship
        filtered = []
        for w in warnings:
            matched = False
            for v in w["voivodeships"]:
                if matches_voivodeship(v_query, v):
                    matched = True
                    break
            if not matched and w.get("course"):
                # Check for exact voivodeship mention in text
                v_q_norm = normalize_search(v_query)
                if v_q_norm in NORM_VOIVS:
                    if f"wojewodztw{v_q_norm}" in normalize_search(w["course"]) or v_q_norm in normalize_search(w["course"]).split():
                        matched = True
                elif v_q_norm in normalize_search(w["course"]):
                    matched = True
            if matched:
                filtered.append(w)
        warnings = filtered

    output = {
        "count": len(warnings),
        "filterType": w_type,
        "filterVoivodeship": args.voivodeship or None,
        "warnings": warnings,
        "message": "Brak aktywnych ostrzeżeń dla podanych kryteriów." if not warnings else None,
        "source": "Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy (IMGW-PIB)",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_hydro(args: argparse.Namespace) -> None:
    """Fetch hydrological measurements for Polish rivers and water gauge stations."""
    raw_hydro = fetch_api("hydro")
    if not isinstance(raw_hydro, list):
        error_exit("Otrzymano nieprawidłowy format danych z IMGW hydro.", "server_error", 69)

    results: List[Dict[str, Any]] = []

    q_station = normalize_search(args.station) if args.station else None
    q_river = normalize_search(args.river) if args.river else None
    q_voivodeship = normalize_search(args.voivodeship) if args.voivodeship else None

    for item in raw_hydro:
        stacja = item.get("stacja") or ""
        rzeka = item.get("rzeka") or ""
        woj = item.get("wojewodztwo") or ""

        if q_station and q_station not in normalize_search(stacja):
            continue
        if q_river and q_river not in normalize_search(rzeka):
            continue
        if q_voivodeship and q_voivodeship not in normalize_search(woj):
            continue

        stan_wody = parse_float_safe(item.get("stan_wody"))
        stan_ostrz = parse_float_safe(item.get("stan_ostrzegawczy"))
        stan_alarm = parse_float_safe(item.get("stan_alarmowy"))

        status = "normalny"
        if stan_alarm is not None and stan_wody is not None and stan_wody >= stan_alarm:
            status = "alarmowy"
        elif stan_ostrz is not None and stan_wody is not None and stan_wody >= stan_ostrz:
            status = "ostrzegawczy"

        if args.alarm_only and status == "normalny":
            continue

        results.append({
            "stationId": str(item.get("id_stacji", "")),
            "stationName": stacja,
            "river": rzeka,
            "voivodeship": woj,
            "status": status,
            "waterLevelCm": stan_wody,
            "warningLevelCm": stan_ostrz,
            "alarmLevelCm": stan_alarm,
            "waterTemperatureC": parse_float_safe(item.get("temperatura_wody")),
            "flowM3s": parse_float_safe(item.get("przeplyw")),
            "measurementDate": item.get("stan_wody_data_pomiaru"),
            "coordinates": {
                "lat": parse_float_safe(item.get("lat")),
                "lon": parse_float_safe(item.get("lon")),
            },
        })

    # Sort results: alarm states first, then alphabetical
    def sort_key(x):
        priority = 0 if x["status"] == "alarmowy" else (1 if x["status"] == "ostrzegawczy" else 2)
        return (priority, x["river"], x["stationName"])

    results.sort(key=sort_key)

    if args.limit and args.limit > 0:
        results = results[:args.limit]

    output = {
        "count": len(results),
        "alarmOnly": args.alarm_only,
        "stations": results,
        "source": "Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy (IMGW-PIB)",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_stations(args: argparse.Namespace) -> None:
    """List synoptic stations (works 100% offline)."""
    search = normalize_search(args.search) if args.search else None
    results = []

    for sid, sinfo in sorted(SYNOP_STATIONS.items(), key=lambda x: x[1]["name"]):
        if search:
            if search not in normalize_search(sinfo["name"]) and search not in sinfo["slug"] and search != sid:
                continue
        results.append({
            "stationId": sid,
            "stationName": sinfo["name"],
            "slug": sinfo["slug"],
            "coordinates": {
                "lat": sinfo["lat"],
                "lon": sinfo["lon"],
            },
        })

    output = {
        "count": len(results),
        "totalSynopStations": len(SYNOP_STATIONS),
        "stations": results,
        "source": "IMGW-PIB Catalogue",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Oficjalne dane meteorologiczne i hydrologiczne IMGW-PIB dla Polski."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # weather
    p_weather = subparsers.add_parser(
        "weather",
        help="Pobierz aktualną pogodę (synop) dla wybranej stacji lub miasta",
    )
    p_weather.add_argument(
        "station",
        help="Nazwa stacji (np. 'Warszawa', 'Kraków', 'Zakopane'), slug lub ID stacji",
    )
    p_weather.set_defaults(func=cmd_weather)

    # synop
    p_synop = subparsers.add_parser(
        "synop",
        help="Pobierz aktualne obserwacje ze wszystkich 62 stacji synoptycznych w Polsce",
    )
    p_synop.add_argument(
        "--sort",
        choices=["temp", "temp_desc", "wind_desc", "pressure_desc", "rain_desc", "name"],
        default="name",
        help="Sortowanie wyników (domyślnie alfabetycznie)",
    )
    p_synop.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Ogranicz liczbę zwracanych stacji",
    )
    p_synop.set_defaults(func=cmd_synop)

    # near
    p_near = subparsers.add_parser(
        "near",
        help="Znajdź najbliższą stację synoptyczną do podanych współrzędnych GPS (lat lon)",
    )
    p_near.add_argument("lat", type=float, help="Szerokość geograficzna (np. 52.23)")
    p_near.add_argument("lon", type=float, help="Długość geograficzna (np. 21.01)")
    p_near.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Liczba najbliższych stacji do zwrócenia (domyślnie 3)",
    )
    p_near.add_argument(
        "--no-weather",
        action="store_true",
        help="Nie pobieraj bieżącej pogody ze stacji, zwróć tylko odległości",
    )
    p_near.set_defaults(func=cmd_near)

    # warnings
    p_warn = subparsers.add_parser(
        "warnings",
        help="Pobierz oficjalne ostrzeżenia meteorologiczne i hydrologiczne IMGW",
    )
    p_warn.add_argument(
        "--type",
        choices=["meteo", "hydro", "all"],
        default="all",
        help="Typ ostrzeżeń (meteo, hydro lub all)",
    )
    p_warn.add_argument(
        "--voivodeship",
        help="Filtruj wg województwa (np. 'pomorskie', 'mazowieckie')",
    )
    p_warn.set_defaults(func=cmd_warnings)

    # hydro
    p_hydro = subparsers.add_parser(
        "hydro",
        help="Pobierz stany wód na rzekach w Polsce ze stacji hydrologicznych",
    )
    p_hydro.add_argument("--station", help="Filtruj wg nazwy stacji wodowskazowej")
    p_hydro.add_argument("--river", help="Filtruj wg nazwy rzeki (np. 'Wisła', 'Odra')")
    p_hydro.add_argument("--voivodeship", help="Filtruj wg województwa")
    p_hydro.add_argument(
        "--alarm-only",
        action="store_true",
        help="Pokaż tylko stacje z przekroczonym stanem ostrzegawczym lub alarmowym",
    )
    p_hydro.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Maksymalna liczba wyników (domyślnie 30)",
    )
    p_hydro.set_defaults(func=cmd_hydro)

    # stations
    p_stations = subparsers.add_parser(
        "stations",
        help="Lista 62 stacji synoptycznych IMGW wraz ze współrzędnymi (działa offline)",
    )
    p_stations.add_argument("--search", help="Filtruj stacje po nazwie lub slugu")
    p_stations.set_defaults(func=cmd_stations)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
