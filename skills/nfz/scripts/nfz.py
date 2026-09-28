#!/usr/bin/env python3
"""CLI for Narodowy Fundusz Zdrowia (NFZ) official open data.

Fetches official public data from NFZ Terminy Leczenia / PCUŚ API (v1.4):
- Świadczenia (Medical benefits / services catalogue)
- Kolejki i czas oczekiwania (PCUŚ - Prognozowany Czas Oczekiwania na Świadczenie)
- Placówki medyczne i świadczeniodawcy (Healthcare providers & clinics)
- Wyszukiwanie geograficzne i porównywanie placówek w zadanym promieniu (Haversine)

Official API: https://apinfz.nfz.gov.pl/app-itl-api-pcus/
Zero external dependencies (Python 3.8+ standard library only).

Copyright (c) 2026 Michell Hoduń <mhodun@gmail.com> (https://github.com/b44x)
Licensed under the MIT License.
"""

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

API_BASE_URL = "https://apinfz.nfz.gov.pl/app-itl-api-pcus"

PROVINCES: Dict[str, str] = {
    "01": "dolnośląskie",
    "02": "kujawsko-pomorskie",
    "03": "lubelskie",
    "04": "lubuskie",
    "05": "łódzkie",
    "06": "małopolskie",
    "07": "mazowieckie",
    "08": "opolskie",
    "09": "podkarpackie",
    "10": "podlaskie",
    "11": "pomorskie",
    "12": "śląskie",
    "13": "świętokrzyskie",
    "14": "warmińsko-mazurskie",
    "15": "wielkopolskie",
    "16": "zachodniopomorskie",
}

DIACRITICS_MAP = {
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ź": "z", "ż": "z",
}

# Standard coordinates and canonical names for major Polish cities for geo-distance fallback
CITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "warszawa": {"name": "Warszawa", "province": "07", "lat": 52.231, "lon": 21.006},
    "krakow": {"name": "Kraków", "province": "06", "lat": 50.061, "lon": 19.937},
    "wroclaw": {"name": "Wrocław", "province": "01", "lat": 51.107, "lon": 17.038},
    "lodz": {"name": "Łódź", "province": "05", "lat": 51.768, "lon": 19.456},
    "poznan": {"name": "Poznań", "province": "15", "lat": 52.406, "lon": 16.929},
    "gdansk": {"name": "Gdańsk", "province": "11", "lat": 54.352, "lon": 18.646},
    "szczecin": {"name": "Szczecin", "province": "16", "lat": 53.428, "lon": 14.553},
    "bydgoszcz": {"name": "Bydgoszcz", "province": "02", "lat": 53.123, "lon": 18.007},
    "lublin": {"name": "Lublin", "province": "03", "lat": 51.246, "lon": 22.568},
    "bialystok": {"name": "Białystok", "province": "10", "lat": 53.132, "lon": 23.168},
    "katowice": {"name": "Katowice", "province": "12", "lat": 50.264, "lon": 19.023},
    "gdynia": {"name": "Gdynia", "province": "11", "lat": 54.518, "lon": 18.530},
    "czestochowa": {"name": "Częstochowa", "province": "12", "lat": 50.811, "lon": 19.120},
    "radom": {"name": "Radom", "province": "07", "lat": 51.402, "lon": 21.147},
    "torun": {"name": "Toruń", "province": "02", "lat": 53.013, "lon": 18.598},
    "rzeszow": {"name": "Rzeszów", "province": "09", "lat": 50.041, "lon": 21.999},
    "sosnowiec": {"name": "Sosnowiec", "province": "12", "lat": 50.286, "lon": 19.104},
    "kielce": {"name": "Kielce", "province": "13", "lat": 50.870, "lon": 20.627},
    "gliwice": {"name": "Gliwice", "province": "12", "lat": 50.294, "lon": 18.671},
    "olsztyn": {"name": "Olsztyn", "province": "14", "lat": 53.778, "lon": 20.480},
    "bielsko-biala": {"name": "Bielsko-Biała", "province": "12", "lat": 49.822, "lon": 19.044},
    "bielskobiala": {"name": "Bielsko-Biała", "province": "12", "lat": 49.822, "lon": 19.044},
    "bytom": {"name": "Bytom", "province": "12", "lat": 50.348, "lon": 18.915},
    "zielona gora": {"name": "Zielona Góra", "province": "04", "lat": 51.935, "lon": 15.506},
    "zielonagora": {"name": "Zielona Góra", "province": "04", "lat": 51.935, "lon": 15.506},
    "rybnik": {"name": "Rybnik", "province": "12", "lat": 50.097, "lon": 18.541},
    "ruda slaska": {"name": "Ruda Śląska", "province": "12", "lat": 50.258, "lon": 18.855},
    "opole": {"name": "Opole", "province": "08", "lat": 50.675, "lon": 17.921},
    "tychy": {"name": "Tychy", "province": "12", "lat": 50.123, "lon": 18.986},
    "gorzow": {"name": "Gorzów Wielkopolski", "province": "04", "lat": 52.736, "lon": 15.228},
    "elblag": {"name": "Elbląg", "province": "14", "lat": 54.152, "lon": 19.408},
    "plock": {"name": "Płock", "province": "07", "lat": 52.546, "lon": 19.706},
    "dabrowa gornicza": {"name": "Dąbrowa Górnicza", "province": "12", "lat": 50.320, "lon": 19.194},
    "walbrzych": {"name": "Wałbrzych", "province": "01", "lat": 50.781, "lon": 16.284},
    "wloclawek": {"name": "Włocławek", "province": "02", "lat": 52.648, "lon": 19.067},
    "tarnow": {"name": "Tarnów", "province": "06", "lat": 50.012, "lon": 20.985},
    "chorzow": {"name": "Chorzów", "province": "12", "lat": 50.297, "lon": 18.954},
    "koszalin": {"name": "Koszalin", "province": "16", "lat": 54.194, "lon": 16.172},
    "kalisz": {"name": "Kalisz", "province": "15", "lat": 51.761, "lon": 18.091},
    "legnica": {"name": "Legnica", "province": "01", "lat": 51.207, "lon": 16.161},
    "grudziadz": {"name": "Grudziądz", "province": "02", "lat": 53.484, "lon": 18.753},
    "jaworzno": {"name": "Jaworzno", "province": "12", "lat": 50.205, "lon": 19.274},
    "slupsk": {"name": "Słupsk", "province": "11", "lat": 54.464, "lon": 17.028},
    "nowy sacz": {"name": "Nowy Sącz", "province": "06", "lat": 49.624, "lon": 20.692},
    "jelenia gora": {"name": "Jelenia Góra", "province": "01", "lat": 50.904, "lon": 15.739},
    "siedlce": {"name": "Siedlce", "province": "07", "lat": 52.167, "lon": 22.290},
    "konin": {"name": "Konin", "province": "15", "lat": 52.223, "lon": 18.251},
    "piotrkow trybunalski": {"name": "Piotrków Trybunalski", "province": "05", "lat": 51.405, "lon": 19.688},
    "pila": {"name": "Piła", "province": "15", "lat": 53.151, "lon": 16.737},
    "inowroclaw": {"name": "Inowrocław", "province": "02", "lat": 52.798, "lon": 18.263},
    "lubin": {"name": "Lubin", "province": "01", "lat": 51.398, "lon": 16.201},
    "suwalki": {"name": "Suwałki", "province": "10", "lat": 54.111, "lon": 22.930},
    "stargard": {"name": "Stargard", "province": "16", "lat": 53.338, "lon": 15.045},
    "glogow": {"name": "Głogów", "province": "01", "lat": 51.663, "lon": 16.084},
    "zamosc": {"name": "Zamość", "province": "03", "lat": 50.723, "lon": 23.251},
    "sopot": {"name": "Sopot", "province": "11", "lat": 54.441, "lon": 18.560},
    "starogard gdanski": {"name": "Starogard Gdański", "province": "11", "lat": 53.966, "lon": 18.528},
    "tczew": {"name": "Tczew", "province": "11", "lat": 54.092, "lon": 18.784},
    "rumia": {"name": "Rumia", "province": "11", "lat": 54.571, "lon": 18.388},
    "wejherowo": {"name": "Wejherowo", "province": "11", "lat": 54.604, "lon": 18.233},
    "kartuzy": {"name": "Kartuzy", "province": "11", "lat": 54.334, "lon": 18.197},
    "koscierzyna": {"name": "Kościerzyna", "province": "11", "lat": 54.122, "lon": 17.981},
    "malbork": {"name": "Malbork", "province": "11", "lat": 54.035, "lon": 19.027},
    "kwidzyn": {"name": "Kwidzyn", "province": "11", "lat": 53.734, "lon": 18.931},
    "zakopane": {"name": "Zakopane", "province": "06", "lat": 49.299, "lon": 19.949},
}


def normalize_search(text: str) -> str:
    """Normalize Polish text for case- and accent-insensitive search."""
    text = text.lower().strip()
    for char, replacement in DIACRITICS_MAP.items():
        text = text.replace(char, replacement)
    return text


def resolve_province(query: Optional[str]) -> Optional[str]:
    """Resolve province name or code to 2-digit NFZ province code ('01'-'16')."""
    if not query:
        return None
    q = query.strip()
    if q in PROVINCES:
        return q

    # Try 1-digit code conversion (e.g. '1' -> '01')
    if q.isdigit() and len(q) == 1 and f"0{q}" in PROVINCES:
        return f"0{q}"

    q_norm = normalize_search(q)
    for code, name in PROVINCES.items():
        if q_norm in normalize_search(name):
            return code
    return None


def resolve_city_info(query: str) -> Optional[Dict[str, Any]]:
    """Look up city in reference registry to get canonical Polish name, province, and coordinates."""
    q_norm = normalize_search(query)
    if q_norm in CITY_REGISTRY:
        return CITY_REGISTRY[q_norm]
    for key, cinfo in CITY_REGISTRY.items():
        if q_norm == key or q_norm in normalize_search(cinfo["name"]):
            return cinfo
    return None


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


def normalize_coordinates(raw_lat: Any, raw_lon: Any) -> Tuple[Optional[float], Optional[float]]:
    """Normalize latitude and longitude, correcting inverted coordinates from provider records."""
    if raw_lat is None or raw_lon is None:
        return None, None
    try:
        c1, c2 = float(raw_lat), float(raw_lon)
    except (ValueError, TypeError):
        return None, None

    # Poland bounding box: lat ~ 49.0 - 55.5, lon ~ 14.0 - 24.5
    if 48.0 <= c1 <= 56.0 and 13.0 <= c2 <= 25.0:
        return round(c1, 6), round(c2, 6)
    if 13.0 <= c1 <= 25.0 and 48.0 <= c2 <= 56.0:
        return round(c2, 6), round(c1, 6)
    return round(c1, 6), round(c2, 6)


def error_exit(message: str, error_type: str = "error", code: int = 64) -> None:
    """Print structured error JSON to stderr and exit."""
    json.dump({"error": message, "type": error_type}, sys.stderr, ensure_ascii=False)
    sys.stderr.write("\n")
    sys.exit(code)


def get_fixtures_path() -> Path:
    """Get path to offline fixtures JSON."""
    return Path(__file__).resolve().parent.parent / "resources" / "fixtures.json"


def load_fixture(fixture_key: str) -> Any:
    """Load sample fixture data for offline contract testing."""
    fpath = get_fixtures_path()
    if not fpath.is_file():
        error_exit(f"Plik danych testowych fixture nie istnieje: {fpath}", "not_found", 2)
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        if fixture_key in data:
            return data[fixture_key]
        error_exit(f"Klucz fixture '{fixture_key}' nie znaleziony w {fpath}", "not_found", 2)
    except Exception as e:
        error_exit(f"Błąd odczytu fixture: {e}", "parse_error", 69)


def fetch_api(endpoint: str, query_params: Optional[Dict[str, Any]] = None, timeout: int = 12) -> Any:
    """Execute GET request against NFZ Terminy Leczenia API."""
    params = dict(query_params or {})
    params.setdefault("format", "json")
    query_str = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}?{query_str}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ai-polish-skills-nfz/1.0.0 (+https://github.com/b44x/ai-polish-skills)",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass

        # Try parsing structured NFZ error
        msg = f"HTTP {e.code}"
        try:
            err_json = json.loads(body)
            if "errors" in err_json and err_json["errors"]:
                e_first = err_json["errors"][0]
                msg = f"{e_first.get('error-reason', '')}: {e_first.get('error-solution', '')}".strip(": ")
        except Exception:
            pass

        if e.code == 404:
            error_exit(f"Brak danych w NFZ dla podanego zapytania: {msg}", "not_found", 2)
        elif e.code == 400:
            error_exit(f"Nieprawidłowe zapytanie do API NFZ (400 Bad Request): {msg}", "bad_request", 64)
        else:
            error_exit(f"Błąd serwera NFZ (HTTP {e.code}): {msg or body}", "server_error", 69)
    except urllib.error.URLError as e:
        error_exit(f"Błąd połączenia z serwerem NFZ: {e.reason}", "network_error", 69)
    except json.JSONDecodeError as e:
        error_exit(f"Błąd parsowania odpowiedzi JSON z NFZ: {e}", "parse_error", 69)
    except Exception as e:
        error_exit(f"Nieoczekiwany błąd: {str(e)}", "unknown_error", 69)
    return None


def format_queue_record(raw: Dict[str, Any], origin_lat: Optional[float] = None, origin_lon: Optional[float] = None) -> Dict[str, Any]:
    """Normalize raw queue item into a structured record."""
    attr = raw.get("attributes", {})
    qid = raw.get("id")

    # Coordinates handling with city fallback
    raw_lat, raw_lon = attr.get("latitude"), attr.get("longitude")
    lat, lon = normalize_coordinates(raw_lat, raw_lon)
    is_approximate = False

    locality_str = attr.get("locality", "").strip()
    if (lat is None or lon is None) and locality_str:
        city_info = resolve_city_info(locality_str)
        if city_info:
            lat = city_info["lat"]
            lon = city_info["lon"]
            is_approximate = True

    # Calculate distance if origin coordinates available
    dist_km = None
    if origin_lat is not None and origin_lon is not None and lat is not None and lon is not None:
        dist_km = round(haversine_distance_km(origin_lat, origin_lon, lat, lon), 1)

    # Statistics
    stats = attr.get("statistics", {}) or {}
    prov_data = stats.get("provider-data") or {}
    avg_days = prov_data.get("average-period")
    awaiting_count = prov_data.get("awaiting")
    stats_month = prov_data.get("update")

    # Dates
    dates = attr.get("dates") or {}
    pcus_text = dates.get("pcus")
    as_of_date = dates.get("date-situation-as-at")

    # Case
    case_code = attr.get("case", 1)
    case_label = "pilny" if case_code == 2 else "stabilny"

    # Accessibility
    accessibility = {
        "toilet": attr.get("toilet") == "Y",
        "ramp": attr.get("ramp") == "Y",
        "carPark": attr.get("car-park") == "Y",
        "elevator": attr.get("elevator") == "Y",
        "ac": attr.get("ac") == "Y",
        "wheelchairs": attr.get("wheelchairs") == "Y",
        "automaticDoor": attr.get("automatic-door") == "Y",
    }

    return {
        "id": qid,
        "benefit": attr.get("benefit"),
        "provider": attr.get("provider"),
        "place": attr.get("place"),
        "locality": locality_str,
        "address": attr.get("address"),
        "phone": attr.get("phone"),
        "case": case_label,
        "waitingTime": {
            "pcus": pcus_text,
            "averagePeriodDays": avg_days,
            "awaiting": awaiting_count,
            "dateSituationAsAt": as_of_date,
            "statisticsUpdateMonth": stats_month,
        },
        "coordinates": {
            "lat": lat,
            "lon": lon,
            "isApproximate": is_approximate,
        } if lat is not None and lon is not None else None,
        "distanceKm": dist_km,
        "queueInCer": attr.get("queue-in-cer") == "Y",
        "accessibility": accessibility,
        "source": "Narodowy Fundusz Zdrowia (apinfz.nfz.gov.pl)",
    }


def find_matching_benefit(query: str) -> Optional[str]:
    """Search benefits dictionary to find official NFZ benefit name."""
    q = query.strip()
    if len(q) < 3:
        return q.upper()

    try:
        data = fetch_api("benefits", {"name": q, "limit": 10})
        b_list = data.get("data", [])
        if b_list:
            # 1. Exact case-insensitive match
            for b in b_list:
                if normalize_search(b) == normalize_search(q):
                    return b
            # 2. Return first match
            return b_list[0]
    except Exception:
        pass
    return q.upper()


def cmd_benefits(args: argparse.Namespace) -> None:
    """Search official NFZ benefits dictionary."""
    query = args.query.strip()
    if len(query) < 3:
        error_exit("Wyszukiwanie świadczenia wymaga podania co najmniej 3 znaków.", "bad_request", 64)

    if args.offline:
        fix = load_fixture("benefit")
        print(json.dumps(fix, ensure_ascii=False, indent=2))
        return

    data = fetch_api("benefits", {"name": query, "limit": args.limit or 20})
    b_list = data.get("data", [])
    count = data.get("meta", {}).get("count", len(b_list))

    output = {
        "query": query,
        "count": count,
        "benefits": b_list,
        "source": "Narodowy Fundusz Zdrowia (apinfz.nfz.gov.pl)",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_queues(args: argparse.Namespace) -> None:
    """Search queues and estimated waiting times for benefits."""
    if args.offline:
        fix = load_fixture("queue")
        output = {
            "count": 1,
            "benefit": fix.get("benefit"),
            "queues": [fix],
            "source": "Narodowy Fundusz Zdrowia (Fixture)",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    benefit_query = args.benefit.strip() if args.benefit else None
    province_code = resolve_province(args.province) if args.province else None
    locality_query = args.locality.strip() if args.locality else None

    # Location resolution for geo-distance
    origin_lat = args.near_lat
    origin_lon = args.near_lon

    if locality_query:
        city_info = resolve_city_info(locality_query)
        if city_info:
            # Canonical name helps NFZ API matching with proper Polish diacritics
            locality_query = city_info["name"]
            if not province_code:
                province_code = city_info["province"]
            if origin_lat is None or origin_lon is None:
                origin_lat = city_info["lat"]
                origin_lon = city_info["lon"]

    # Official benefit resolution
    official_benefit = None
    if benefit_query:
        official_benefit = find_matching_benefit(benefit_query)

    # API requirement check: requires at least benefit or province
    if not official_benefit and not province_code:
        error_exit(
            "Zapytanie wymaga podania co najmniej nazwy świadczenia (--benefit) lub województwa (--province).",
            "bad_request",
            64,
        )

    # Case parameter: 1 - stabilny, 2 - pilny
    case_param = 2 if args.urgent or args.case == 2 else 1

    params: Dict[str, Any] = {
        "benefit": official_benefit,
        "province": province_code,
        "locality": locality_query,
        "case": case_param,
        "page": args.page or 1,
        "limit": min(args.limit or 25, 25),
    }

    data = fetch_api("queues", params)
    raw_list = data.get("data", [])
    total_count = data.get("meta", {}).get("count", len(raw_list))

    records = [format_queue_record(it, origin_lat, origin_lon) for it in raw_list]

    # Filter by radius if requested
    if args.radius_km and args.radius_km > 0 and origin_lat is not None and origin_lon is not None:
        records = [r for r in records if r.get("distanceKm") is not None and r["distanceKm"] <= args.radius_km]

    # Sorting
    if args.sort == "time":
        records.sort(key=lambda x: (
            x["waitingTime"]["averagePeriodDays"] is None,
            x["waitingTime"]["averagePeriodDays"] or 9999
        ))
    elif args.sort == "distance":
        records.sort(key=lambda x: (
            x["distanceKm"] is None,
            x["distanceKm"] or 9999
        ))
    elif args.sort == "awaiting":
        records.sort(key=lambda x: (
            x["waitingTime"]["awaiting"] is None,
            x["waitingTime"]["awaiting"] or 9999
        ))

    output = {
        "benefit": official_benefit or benefit_query,
        "province": PROVINCES.get(province_code, province_code) if province_code else None,
        "locality": locality_query,
        "case": "pilny" if case_param == 2 else "stabilny",
        "count": len(records),
        "totalMatchingInNfz": total_count,
        "queues": records,
        "source": "Narodowy Fundusz Zdrowia (apinfz.nfz.gov.pl)",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_near(args: argparse.Namespace) -> None:
    """Find nearby clinics and waiting times for a medical benefit within a radius."""
    benefit_query = args.benefit.strip()
    radius_km = args.radius_km or 50.0

    # Resolve location
    origin_lat = None
    origin_lon = None
    locality_name = None
    province_code = None

    if args.lon is not None:
        # User provided lat and lon
        try:
            origin_lat = float(args.location)
            origin_lon = float(args.lon)
        except ValueError:
            error_exit(f"Nieprawidłowe współrzędne GPS: lat={args.location}, lon={args.lon}", "bad_request", 64)
    else:
        # Location is city name
        city_info = resolve_city_info(args.location)
        if not city_info:
            error_exit(f"Nie rozpoznano miejscowości '{args.location}'. Podaj większe miasto lub współrzędne GPS.", "not_found", 2)
        locality_name = city_info["name"]
        origin_lat = city_info["lat"]
        origin_lon = city_info["lon"]
        province_code = city_info["province"]

    if origin_lat is None or origin_lon is None:
        error_exit("Nie udało się ustalić współrzędnych geograficznych do wyszukiwania.", "bad_request", 64)

    official_benefit = find_matching_benefit(benefit_query)
    case_param = 2 if args.urgent or args.case == 2 else 1

    params: Dict[str, Any] = {
        "benefit": official_benefit,
        "province": province_code,
        "case": case_param,
        "page": 1,
        "limit": 25,
    }

    data = fetch_api("queues", params)
    raw_list = data.get("data", [])

    records = [format_queue_record(it, origin_lat, origin_lon) for it in raw_list]
    within_radius = [r for r in records if r.get("distanceKm") is not None and r["distanceKm"] <= radius_km]

    # Sort
    if args.sort == "distance":
        within_radius.sort(key=lambda x: (x["distanceKm"] is None, x["distanceKm"] or 9999))
    else:
        # Default sort by shortest waiting time
        within_radius.sort(key=lambda x: (
            x["waitingTime"]["averagePeriodDays"] is None,
            x["waitingTime"]["averagePeriodDays"] or 9999,
            x["distanceKm"] or 9999
        ))

    limit = args.limit or 10
    within_radius = within_radius[:limit]

    output = {
        "query": {
            "benefit": official_benefit,
            "location": locality_name or f"{origin_lat}, {origin_lon}",
            "coordinates": {"lat": origin_lat, "lon": origin_lon},
            "radiusKm": radius_km,
            "case": "pilny" if case_param == 2 else "stabilny",
        },
        "count": len(within_radius),
        "results": within_radius,
        "source": "Narodowy Fundusz Zdrowia (apinfz.nfz.gov.pl)",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_compare(args: argparse.Namespace) -> None:
    """Compare healthcare providers and waiting times side-by-side."""
    benefit_query = args.benefit.strip()
    official_benefit = find_matching_benefit(benefit_query)
    province_code = resolve_province(args.province) if args.province else None
    locality_query = args.locality.strip() if args.locality else None

    origin_lat = None
    origin_lon = None
    if locality_query:
        city_info = resolve_city_info(locality_query)
        if city_info:
            locality_query = city_info["name"]
            if not province_code:
                province_code = city_info["province"]
            origin_lat = city_info["lat"]
            origin_lon = city_info["lon"]

    params: Dict[str, Any] = {
        "benefit": official_benefit,
        "province": province_code,
        "locality": locality_query,
        "case": 2 if args.urgent else 1,
        "page": 1,
        "limit": min(args.limit or 5, 25),
    }

    data = fetch_api("queues", params)
    raw_list = data.get("data", [])
    records = [format_queue_record(it, origin_lat, origin_lon) for it in raw_list]

    if not records:
        error_exit(f"Brak placówek do porównania dla świadczenia '{benefit_query}'.", "not_found", 2)

    # Identify highlights
    with_wait = [r for r in records if r["waitingTime"]["averagePeriodDays"] is not None]
    shortest_wait = min(with_wait, key=lambda x: x["waitingTime"]["averagePeriodDays"]) if with_wait else None

    with_awaiting = [r for r in records if r["waitingTime"]["awaiting"] is not None]
    fewest_awaiting = min(with_awaiting, key=lambda x: x["waitingTime"]["awaiting"]) if with_awaiting else None

    with_dist = [r for r in records if r["distanceKm"] is not None]
    closest = min(with_dist, key=lambda x: x["distanceKm"]) if with_dist else None

    summary = {
        "shortestWaitClinic": {
            "place": shortest_wait["place"],
            "locality": shortest_wait["locality"],
            "pcus": shortest_wait["waitingTime"]["pcus"],
            "averageDays": shortest_wait["waitingTime"]["averagePeriodDays"],
        } if shortest_wait else None,
        "fewestAwaitingClinic": {
            "place": fewest_awaiting["place"],
            "locality": fewest_awaiting["locality"],
            "awaitingCount": fewest_awaiting["waitingTime"]["awaiting"],
        } if fewest_awaiting else None,
        "closestClinic": {
            "place": closest["place"],
            "locality": closest["locality"],
            "distanceKm": closest["distanceKm"],
        } if closest else None,
    }

    output = {
        "benefit": official_benefit,
        "comparedCount": len(records),
        "highlights": summary,
        "clinics": records,
        "source": "Narodowy Fundusz Zdrowia (apinfz.nfz.gov.pl)",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_provinces(args: argparse.Namespace) -> None:
    """List 16 Polish voivodeships with their 2-digit NFZ codes (offline)."""
    prov_list = [{"code": code, "name": name} for code, name in sorted(PROVINCES.items())]
    output = {
        "count": len(prov_list),
        "provinces": prov_list,
        "source": "Narodowy Fundusz Zdrowia (Słownik Województw)",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Oficjalne dane NFZ: wyszukiwanie świadczeń, kolejek, placówek i prognozowanego czasu oczekiwania."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # benefits
    p_ben = subparsers.add_parser("benefits", aliases=["benefit"], help="Wyszukaj oficjalne nazwy świadczeń w słowniku NFZ")
    p_ben.add_argument("query", help="Fraza wyszukiwania (min. 3 znaki, np. 'rezonans', 'kolonoskopia', 'ortoped')")
    p_ben.add_argument("--limit", type=int, default=20, help="Maksymalna liczba wyników")
    p_ben.add_argument("--offline", action="store_true", help="Tryb testowy offline (zwraca fixture)")
    p_ben.set_defaults(func=cmd_benefits)

    # queues / search
    p_que = subparsers.add_parser("queues", aliases=["search"], help="Wyszukaj kolejki i prognozowany czas oczekiwania")
    p_que.add_argument("--benefit", help="Nazwa świadczenia (np. 'REZONANS MAGNETYCZNY', 'KOLONOSKOPIA')")
    p_que.add_argument("--province", help="Kod lub nazwa województwa (np. '11' lub 'pomorskie')")
    p_que.add_argument("--locality", help="Miejscowość udzielania świadczenia (np. 'Gdańsk', 'Warszawa')")
    p_que.add_argument("--case", type=int, choices=[1, 2], default=1, help="Przypadek (1 - stabilny, 2 - pilny)")
    p_que.add_argument("--urgent", action="store_true", help="Szukaj dla przypadku pilnego (case=2)")
    p_que.add_argument("--near-lat", type=float, help="Szerokość geograficzna punktu odniesienia")
    p_que.add_argument("--near-lon", type=float, help="Długość geograficzna punktu odniesienia")
    p_que.add_argument("--radius-km", type=float, help="Filtruj do placówek w zadanym promieniu (km)")
    p_que.add_argument("--sort", choices=["time", "distance", "awaiting"], default="time", help="Sortowanie wyników")
    p_que.add_argument("--limit", type=int, default=15, help="Liczba pozycji (maks. 25)")
    p_que.add_argument("--page", type=int, default=1, help="Numer strony")
    p_que.add_argument("--offline", action="store_true", help="Tryb testowy offline (zwraca fixture)")
    p_que.set_defaults(func=cmd_queues)

    # near
    p_near = subparsers.add_parser("near", help="Znajdź najbliższe placówki wykonujące świadczenie w promieniu km")
    p_near.add_argument("location", help="Nazwa miasta (np. 'Gdańsk') lub szerokość geograficzna lat")
    p_near.add_argument("lon", nargs="?", type=float, help="Opcjonalna długość geograficzna lon (gdy location to lat)")
    p_near.add_argument("--benefit", required=True, help="Nazwa świadczenia (np. 'rezonans', 'kolonoskopia')")
    p_near.add_argument("--radius-km", type=float, default=50.0, help="Maksymalny promień w km (domyślnie 50 km)")
    p_near.add_argument("--case", type=int, choices=[1, 2], default=1, help="Przypadek (1 - stabilny, 2 - pilny)")
    p_near.add_argument("--urgent", action="store_true", help="Szukaj dla przypadku pilnego")
    p_near.add_argument("--sort", choices=["time", "distance"], default="time", help="Sortuj wg czasu oczekiwania lub odległości")
    p_near.add_argument("--limit", type=int, default=10, help="Maksymalna liczba placówek (domyślnie 10)")
    p_near.set_defaults(func=cmd_near)

    # compare
    p_comp = subparsers.add_parser("compare", help="Porównaj placówki i czas oczekiwania dla danego świadczenia")
    p_comp.add_argument("--benefit", required=True, help="Nazwa świadczenia")
    p_comp.add_argument("--locality", help="Miejscowość (np. 'Gdańsk')")
    p_comp.add_argument("--province", help="Województwo")
    p_comp.add_argument("--urgent", action="store_true", help="Przypadek pilny")
    p_comp.add_argument("--limit", type=int, default=5, help="Liczba porównywanych placówek (domyślnie 5)")
    p_comp.set_defaults(func=cmd_compare)

    # provinces
    p_prov = subparsers.add_parser("provinces", help="Lista województw i kodów NFZ (działa offline)")
    p_prov.set_defaults(func=cmd_provinces)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
