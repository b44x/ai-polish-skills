#!/usr/bin/env python3
"""CLI for InPost tracking and Paczkomat parcel locker points search across Poland.

Official endpoints from InPost ShipX API (api-shipx-pl.easypack24.net).
Zero external dependencies required (Python 3.8+ stdlib only).
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

API_BASE_URL = "https://api-shipx-pl.easypack24.net/v1"

COMMON_STATUS_TITLES: Dict[str, str] = {
    "created": "Przesyłka utworzona",
    "confirmed": "Przygotowana przez Nadawcę",
    "dispatched_by_sender": "Nadana w Paczkomacie / POP",
    "taken_by_courier": "Odebrana przez Kuriera",
    "adopted_at_source_branch": "Przyjęta w Oddziale Nadawczym",
    "sent_from_source_branch": "Wysłana z Oddziału Nadawczego",
    "adopted_at_sorting_center": "Przyjęta w Sortowni",
    "sent_from_sorting_center": "Wysłana z Sortowni",
    "adopted_at_target_branch": "Przyjęta w Oddziale Doręczenia",
    "out_for_delivery": "Wydana do doręczenia",
    "ready_to_pickup": "Gotowa do odbioru w Paczkomacie",
    "delivered": "Doręczona / Odebrana",
    "returned_to_sender": "Zwrócona do Nadawcy",
    "expired": "Upłynął termin odbioru",
}


def error_exit(message: str, error_type: str = "error", code: int = 64) -> None:
    """Print error JSON to stderr and exit."""
    json.dump({"error": message, "type": error_type}, sys.stderr, ensure_ascii=False)
    sys.stderr.write("\n")
    sys.exit(code)


def sanitize_tracking_number(val: str) -> str:
    """Strip spaces and dashes from tracking number."""
    return re.sub(r"[\s\-_]", "", val.strip())


def validate_tracking_number(val: str) -> Tuple[bool, Optional[str]]:
    """Validate InPost 24-digit tracking number."""
    cleaned = sanitize_tracking_number(val)
    if not cleaned.isdigit():
        return False, "Numer przesyłki musi składać się wyłącznie z cyfr."
    if len(cleaned) != 24:
        return False, f"Numer przesyłki InPost musi mieć dokładnie 24 cyfry (podano {len(cleaned)})."
    return True, None


def fetch_api(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute GET request against the ShipX API."""
    url = f"{API_BASE_URL}/{path}"
    if params:
        clean_params = {k: v for k, v in params.items() if v is not None}
        if clean_params:
            url += f"?{urllib.parse.urlencode(clean_params)}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ai-polish-skills-inpost/1.0.0 (+https://github.com/b44x/ai-polish-skills)",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
            parsed = json.loads(data)
            if isinstance(parsed, dict) and parsed.get("status") == 404:
                error_exit(
                    parsed.get("error", "Nie znaleziono obiektu w systemie InPost."),
                    "not_found",
                    2,
                )
            return parsed
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err_json = json.loads(body)
            msg = (
                err_json.get("message")
                or err_json.get("error")
                or err_json.get("key")
                or body
            )
        except Exception:
            msg = body
        if e.code == 404:
            error_exit(f"Nie znaleziono danych w systemie InPost: {msg}", "not_found", 2)
        elif e.code == 400:
            error_exit(f"Nieprawidłowe zapytanie InPost: {msg}", "bad_request", 64)
        else:
            error_exit(f"Błąd serwera InPost (HTTP {e.code}): {msg}", "server_error", 69)
    except urllib.error.URLError as e:
        error_exit(f"Błąd połączenia z serwerem InPost: {e.reason}", "network_error", 69)
    except Exception as e:
        error_exit(f"Nieoczekiwany błąd: {str(e)}", "unknown_error", 69)
    return {}


def format_point(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize InPost point details into clean JSON."""
    loc = item.get("location") or {}
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    addr_details = item.get("address_details") or {}
    addr = item.get("address") or {}

    types = item.get("type") or []
    type_str = types[0] if isinstance(types, list) and types else str(types)
    type_desc = "Paczkomat" if "parcel_locker" in type_str else "Punkt Odbioru (POP)"

    distance_m = item.get("distance")
    distance_fmt = None
    if distance_m is not None:
        if distance_m >= 1000:
            distance_fmt = f"{distance_m / 1000:.1f} km"
        else:
            distance_fmt = f"{int(distance_m)} m"

    maps_url = (
        f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        if (lat and lon)
        else None
    )

    return {
        "name": item.get("name"),
        "type": type_str,
        "typeDescription": type_desc,
        "status": item.get("status"),
        "address": {
            "line1": addr.get("line1") or addr_details.get("street", ""),
            "line2": addr.get("line2") or addr_details.get("post_code", ""),
            "city": addr_details.get("city") or "",
            "postCode": addr_details.get("post_code") or "",
            "street": addr_details.get("street") or "",
            "buildingNumber": addr_details.get("building_number") or "",
        },
        "locationDescription": item.get("location_description"),
        "location": {
            "latitude": lat,
            "longitude": lon,
        },
        "distanceMeters": distance_m,
        "distanceFormatted": distance_fmt,
        "openingHours": item.get("opening_hours", "24/7"),
        "is24_7": item.get("location_247", False),
        "easyAccessZone": item.get("easy_access_zone", False),
        "paymentAvailable": item.get("payment_available", False),
        "paymentDescription": item.get("payment_point_descr"),
        "imageUrl": item.get("image_url"),
        "googleMapsUrl": maps_url,
    }


def cmd_track(args: argparse.Namespace) -> None:
    raw_num = args.number
    valid, err = validate_tracking_number(raw_num)
    if not valid:
        error_exit(f"Błędny numer przesyłki '{raw_num}': {err}", "validation_error", 64)

    num = sanitize_tracking_number(raw_num)
    data = fetch_api(f"tracking/{num}")

    status_code = data.get("status", "unknown")
    status_title = COMMON_STATUS_TITLES.get(status_code, status_code)

    details_list = data.get("tracking_details") or []
    events = []
    for d in details_list:
        st = d.get("status")
        events.append({
            "datetime": d.get("datetime"),
            "status": st,
            "title": COMMON_STATUS_TITLES.get(st, st),
            "agency": d.get("agency"),
        })

    custom_attr = data.get("custom_attributes") or {}
    target_machine = custom_attr.get("target_machine_id")

    res = {
        "trackingNumber": num,
        "service": data.get("service"),
        "status": status_code,
        "statusTitle": status_title,
        "targetMachine": target_machine,
        "createdAt": data.get("created_at"),
        "updatedAt": data.get("updated_at"),
        "expectedFlow": data.get("expected_flow") or [],
        "events": events,
        "trackingUrl": f"https://inpost.pl/sledzenie-przesylek?number={num}",
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_point(args: argparse.Namespace) -> None:
    name = args.name.strip().upper()
    data = fetch_api(f"points/{name}")
    formatted = format_point(data)
    print(json.dumps(formatted, ensure_ascii=False, indent=2))


def cmd_search(args: argparse.Namespace) -> None:
    params: Dict[str, Any] = {}
    if args.city:
        params["city"] = args.city.strip()
    if args.post_code:
        params["post_code"] = args.post_code.strip()
    if args.type:
        params["type"] = args.type.strip()
    if args.query:
        params["query"] = args.query.strip()
    params["per_page"] = 100

    # ShipX points endpoint
    data = fetch_api("points", params)
    items = data.get("items") or []

    query = args.query.strip().lower() if args.query else None
    matched: List[Dict[str, Any]] = []

    for item in items:
        # Filter operating points
        if item.get("status") not in ("Operating", None):
            continue

        if query:
            name = (item.get("name") or "").lower()
            loc_desc = (item.get("location_description") or "").lower()
            addr = item.get("address") or {}
            line1 = (addr.get("line1") or "").lower()
            line2 = (addr.get("line2") or "").lower()
            if (
                query not in name
                and query not in loc_desc
                and query not in line1
                and query not in line2
            ):
                continue

        matched.append(format_point(item))
        if len(matched) >= args.limit:
            break

    output = {
        "query": {
            "city": args.city,
            "postCode": args.post_code,
            "filter": args.query,
            "type": args.type,
            "limit": args.limit,
        },
        "count": len(matched),
        "points": matched,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_near(args: argparse.Namespace) -> None:
    lat = args.latitude
    lon = args.longitude
    params: Dict[str, Any] = {
        "relative_point": f"{lat},{lon}",
        "limit": args.limit,
    }
    if args.type:
        params["type"] = args.type.strip()

    data = fetch_api("points", params)
    items = data.get("items") or []

    points = []
    for item in items:
        dist = item.get("distance")
        if args.max_distance and dist is not None and dist > args.max_distance:
            continue
        points.append(format_point(item))
        if len(points) >= args.limit:
            break

    output = {
        "origin": {
            "latitude": lat,
            "longitude": lon,
        },
        "count": len(points),
        "points": points,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_statuses(args: argparse.Namespace) -> None:
    data = fetch_api("statuses")
    items = data.get("items") or []
    catalog = [
        {
            "name": it.get("name"),
            "title": it.get("title"),
            "description": it.get("description"),
        }
        for it in items
    ]
    print(json.dumps({"count": len(catalog), "statuses": catalog}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wyszukuj Paczkomaty i śledź przesyłki InPost w całej Polsce."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # track
    p_track = subparsers.add_parser("track", help="Śledź przesyłkę po 24-cyfrowym numerze")
    p_track.add_argument("number", help="24-cyfrowy numer przesyłki InPost")
    p_track.set_defaults(func=cmd_track)

    # point
    p_point = subparsers.add_parser(
        "point", help="Pobierz szczegółowe informacje o Paczkomacie po kodzie (np. WAW01M)"
    )
    p_point.add_argument("name", help="Kod punktu / Paczkomatu (np. WAW01M, KRA01A)")
    p_point.set_defaults(func=cmd_point)

    # search
    p_search = subparsers.add_parser("search", help="Wyszukaj Paczkomaty w wybranym mieście lub okolicy")
    p_search.add_argument("--city", help="Nazwa miejscowości (np. Warszawa, Poznań)")
    p_search.add_argument("--post-code", help="Kod pocztowy (np. 00-001)")
    p_search.add_argument("--query", help="Słowo kluczowe (ulica, nazwa punktu, obiekt)")
    p_search.add_argument(
        "--type",
        choices=["parcel_locker", "pop"],
        default="parcel_locker",
        help="Typ punktu (domyślnie parcel_locker)",
    )
    p_search.add_argument("--limit", type=int, default=10, help="Maksymalna liczba wyników (domyślnie 10)")
    p_search.set_defaults(func=cmd_search)

    # near
    p_near = subparsers.add_parser("near", help="Znajdź najbliższe Paczkomaty według współrzędnych GPS")
    p_near.add_argument("latitude", type=float, help="Szerokość geograficzna (np. 52.2297)")
    p_near.add_argument("longitude", type=float, help="Długość geograficzna (np. 21.0122)")
    p_near.add_argument("--limit", type=int, default=5, help="Maksymalna liczba punktów (domyślnie 5)")
    p_near.add_argument(
        "--max-distance",
        type=float,
        help="Maksymalna odległość w metrach (np. 1000 dla 1 km)",
    )
    p_near.add_argument(
        "--type",
        choices=["parcel_locker", "pop"],
        default="parcel_locker",
        help="Typ punktu (domyślnie parcel_locker)",
    )
    p_near.set_defaults(func=cmd_near)

    # statuses
    p_statuses = subparsers.add_parser("statuses", help="Pobierz pełną listę statusów przesyłek InPost")
    p_statuses.set_defaults(func=cmd_statuses)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
