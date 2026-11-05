#!/usr/bin/env python3
"""Read bounded real-estate transaction records from the official RCN WFS."""

import argparse
import collections
import datetime as dt
from fractions import Fraction
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://mapy.geoportal.gov.pl/wss/service/rcn"
DOCS = "https://www.geoportal.gov.pl/pl/dane/rejestr-cen-nieruchomosci-rcn/"
LAYERS = {"lokale": ("LOK", "ID_LOKALU", "POW_UZYT", "FUNKCJA"),
          "budynki": ("BUD", "ID_BUDYNKU", "POW_UZYT", "RODZAJ"),
          "dzialki": ("DZI", "ID_DZIALKI", "POW_EWID", "SPOSOB_UZYT")}
MARKETS = {"pierwotny": "rynekPierwotny", "wtorny": "rynekWtorny"}
NOTES = ["Centralna usługa RCN jest tymczasowa; zakres i aktualność danych zależą od powiatu.",
         "Brak rekordu nie dowodzi braku transakcji. Dane opisują daty aktów, a nie bieżące oferty.",
         "Statystyki dotyczą wyłącznie pobranej próby porównywalnych lokali; nie stanowią wyceny."]


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64):
        super().__init__(message)
        self.kind, self.code = kind, code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def finite_number(value):
    try:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError()
        return number
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("Wymagana skończona liczba.")


def date_value(value):
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError()
        return dt.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Wymagana prawidłowa data YYYY-MM-DD.")


def project(lat, lon):
    """GRS80 Transverse Mercator, EPSG:2180, return (northing, easting).

    Snyder series through A^6; WGS84/ETRS89 distinction is below the precision
    needed for a neighbourhood search. No external projection library is needed.
    """
    a, flattening = 6378137.0, 1 / 298.257222101
    e2 = flattening * (2 - flattening)
    ep2 = e2 / (1 - e2)
    phi, delta = math.radians(lat), math.radians(lon - 19)
    s, c, t = math.sin(phi), math.cos(phi), math.tan(phi)
    n, cc, aa = a / math.sqrt(1 - e2 * s * s), ep2 * c * c, c * delta
    m = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi)
             - 35 * e2 ** 3 / 3072 * math.sin(6 * phi))
    east = 500000 + .9993 * n * (aa + (1 - t * t + cc) * aa ** 3 / 6
             + (5 - 18 * t * t + t ** 4 + 72 * cc - 58 * ep2) * aa ** 5 / 120)
    north = -5300000 + .9993 * (m + n * t * (aa * aa / 2
             + (5 - t * t + 9 * cc + 4 * cc * cc) * aa ** 4 / 24
             + (61 - 58 * t * t + t ** 4 + 600 * cc - 330 * ep2) * aa ** 6 / 720))
    return north, east


def search_bounds(args):
    if args.bbox is not None:
        if args.lat is not None or args.lon is not None or args.radius_km is not None:
            raise SkillError("Użyj --bbox albo --lat/--lon/--radius-km.")
        west, south, east, north = args.bbox
        if not (14 <= west < east <= 24.3 and 49 <= south < north <= 54.9):
            raise SkillError("--bbox: min_lon min_lat max_lon max_lat w granicach Polski.")
        if east - west > .2 + 1e-10 or north - south > .12 + 1e-10:
            raise SkillError("Obszar za duży: maksymalnie 0,2° długości i 0,12° szerokości.")
        # Curved projected edges can have an extremum between the corners,
        # especially where the box crosses the central meridian (19 degrees).
        points = []
        for step in range(41):
            fraction = step / 40
            lat, lon = south + (north - south) * fraction, west + (east - west) * fraction
            points.extend([project(south, lon), project(north, lon),
                           project(lat, west), project(lat, east)])
        # Two metres cover residual curvature between the sampled edge points.
        bbox = (min(p[0] for p in points) - 2, min(p[1] for p in points) - 2,
                max(p[0] for p in points) + 2, max(p[1] for p in points) + 2)
        return bbox, {"bbox_wgs84": args.bbox, "shape": "bounding_box"}
    if args.lat is None or args.lon is None:
        raise SkillError("Podaj --lat i --lon albo --bbox.")
    if not (49 <= args.lat <= 54.9 and 14 <= args.lon <= 24.3):
        raise SkillError("Współrzędne muszą wskazywać Polskę (lat 49–54,9; lon 14–24,3).")
    radius = 1 if args.radius_km is None else args.radius_km
    if not .1 <= radius <= 5:
        raise SkillError("--radius-km musi wynosić 0,1–5.")
    north, east = project(args.lat, args.lon)
    r = radius * 1000
    return (north - r, east - r, north + r, east + r), {
        "lat": args.lat, "lon": args.lon, "radius_km": radius,
        "shape": "square", "note": "Kwadrat o boku 2 × promień w układzie PL-1992, obejmujący otoczenie punktu."}


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def parse_page(raw):
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, ValueError):
        raise SkillError("RCN zwrócił nieprawidłowy XML.", "upstream_format", 69)
    if local_name(root.tag) != "FeatureCollection":
        raise SkillError("RCN odrzucił zapytanie lub zwrócił nieznany format.", "upstream_error", 69)
    rows = []
    for member in root.findall("{*}member"):
        for feature in member:
            row = {local_name(e.tag): "".join(e.itertext()).strip() or None for e in feature
                   if local_name(e.tag) not in ("GEOMETRIA", "boundedBy")}
            row["_feature_id"] = feature.get("{http://www.opengis.net/gml/3.2}id")
            if not row["_feature_id"]:
                raise SkillError("Rekord RCN nie zawiera identyfikatora.", "upstream_format", 69)
            rows.append(row)
    declared = root.get("numberReturned")
    if declared is not None and (not declared.isdigit() or int(declared) != len(rows)):
        raise SkillError("Niespójna liczba rekordów w odpowiedzi RCN.", "upstream_format", 69)
    return rows, root.get("timeStamp")


def fetch_page(params):
    request = urllib.request.Request(BASE + "?" + urllib.parse.urlencode(params), headers={
        "User-Agent": "ai-polish-skills-nieruchomosci/1.0.0", "Accept": "application/gml+xml, application/xml"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(12 * 1024 * 1024 + 1)
        if len(raw) > 12 * 1024 * 1024:
            raise SkillError("Odpowiedź RCN przekracza limit 12 MiB.", "upstream_format", 69)
        return parse_page(raw)
    except urllib.error.HTTPError as exc:
        raise SkillError("RCN HTTP %s; spróbuj później." % exc.code,
                         "rate_limit" if exc.code == 429 else "upstream_error", 69)
    except (urllib.error.URLError, OSError) as exc:
        raise SkillError("Błąd połączenia z RCN: " + str(exc), "network_error", 69)


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def full_share(value):
    try:
        return bool(value) and Fraction(value.replace(" ", "").replace(",", ".")) == 1
    except (ValueError, ZeroDivisionError):
        return False


def normalize(row, layer):
    prefix, ident, area, function = LAYERS[layer]
    price = number(row.get(prefix + "_CENA_BRUTTO"))
    area_value = number(row.get(prefix + "_" + area))
    share = row.get("NIER_UDZIAL")
    # Only an explicitly allocated object price is used. Transaction/property
    # totals can include other objects, land, parking spaces or other shares.
    rate = price / area_value if (price is not None and price > 0 and area_value is not None
                                 and area_value > 0 and full_share(share)) else None
    if rate is not None and not math.isfinite(rate):
        raise SkillError("Nieprawidłowa stawka jednostkowa RCN.", "upstream_format", 69)
    deed_date = row.get("DOK_DATA")
    if deed_date:
        try:
            dt.date.fromisoformat(deed_date[:10])
        except (TypeError, ValueError):
            raise SkillError("Nieprawidłowa data aktu RCN.", "upstream_format", 69)
    return {
        "feature_id": row["_feature_id"], "object_id": row.get(prefix + "_" + ident),
        "transaction_id": row.get("TRAN_LOKALNY_ID_IIP"),
        "transaction_namespace": row.get("TRAN_PRZESTRZEN_NAZW"),
        "transaction_number": row.get("TRAN_OZNACZENIE_TRANS"), "county_teryt": row.get("TERYT"),
        "deed_number": row.get("DOK_OZNACZENIE"), "deed_creator": row.get("DOK_TWORCA"),
        "deed_date": deed_date, "record_updated_at": row.get("TRAN_WERSJA_ID"),
        "market": row.get("TRAN_RODZAJ_RYNKU"), "transaction_type": row.get("TRAN_RODZAJ_TRANS"),
        "property_type": row.get("NIER_RODZAJ"), "right": row.get("NIER_PRAWO"),
        "share": share, "full_ownership_share": full_share(share),
        "function": row.get(prefix + "_" + function), "address": row.get(prefix + "_ADRES"),
        "area_m2": area_value, "object_price_pln": price,
        "property_price_pln": number(row.get("NIER_CENA_BRUTTO")),
        "transaction_price_pln": number(row.get("TRAN_CENA_BRUTTO")),
        "object_price_per_m2_pln": round(rate, 2) if rate is not None else None,
        "property_description": row.get("NIER_OPIS"), "object_notes": row.get(prefix + "_INFO"),
    }


def transaction_key(row):
    # The namespace prevents collisions between county-local identifiers.
    if row["transaction_id"] and row["transaction_namespace"]:
        return (row["transaction_namespace"], row["transaction_id"])
    return None


def deed_key(row):
    # A bulk deed may be split into several RCN transaction identifiers. Keep
    # the notary as part of the identity: deed numbers are not county-unique.
    if not all(row.get(k) for k in ("transaction_namespace", "deed_date", "deed_number", "deed_creator")):
        return None
    normalize_text = lambda value: " ".join(value.casefold().split())
    return (row["transaction_namespace"], row["deed_date"][:10],
            normalize_text(row["deed_number"]), normalize_text(row["deed_creator"]))


def excluded_deeds(rows):
    groups = collections.defaultdict(list)
    for row in rows:
        key = deed_key(row)
        if key is not None:
            groups[key].append(row)
    return {key for key, items in groups.items()
            if len({r["object_id"] for r in items}) != 1
            or len({r["object_price_per_m2_pln"] for r in items}) != 1
            or not all(comparable(r) for r in items)}


def comparable(row):
    return (row["function"] == "mieszkalna" and row["market"] in MARKETS.values()
            and row["property_type"] == "nieruchomoscLokalowa"
            and row["right"] == "wlasnoscLokaluWrazZPrawemZwiazanym"
            and row["transaction_type"] == "wolnyRynek" and row["full_ownership_share"]
            and row["object_id"] and row["object_price_per_m2_pln"] is not None
            and row["transaction_price_pln"] is not None
            and math.isclose(row["transaction_price_pln"], row["object_price_pln"], rel_tol=0, abs_tol=.01)
            and (row["property_price_pln"] is None or row["property_price_pln"] <= 0
                 or math.isclose(row["property_price_pln"], row["object_price_pln"], rel_tol=0, abs_tol=.01))
            and row["deed_date"] and transaction_key(row) is not None and deed_key(row) is not None)


def safe_median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return (ordered[middle] if len(ordered) % 2 else
            ordered[middle - 1] + (ordered[middle] - ordered[middle - 1]) / 2)


def summarize(rows, layer):
    groups = collections.defaultdict(list)
    for row in rows:
        key = transaction_key(row)
        if key is not None:
            groups[key].append(row)
    candidates, seen_deeds = [], set()
    bad_deeds = excluded_deeds(rows)
    if layer == "lokale":
        for items in groups.values():
            # A multi-object transaction does not receive extra statistical weight.
            distinct = {r["object_id"] for r in items}
            if len(distinct) == 1 and all(comparable(r) for r in items):
                rates = {r["object_price_per_m2_pln"] for r in items}
                deed = deed_key(items[0])
                if len(rates) == 1 and deed not in bad_deeds and deed not in seen_deeds:
                    candidates.append(items[0])
                    seen_deeds.add(deed)
    # Preserve separate primary/secondary markets and deed years.
    partitions = collections.defaultdict(list)
    for row in candidates:
        partitions[(row["market"], row["deed_date"][:4])].append(row["object_price_per_m2_pln"])
    return {"comparable_transactions": len(candidates), "excluded_records": len(rows) - len(candidates),
            "basis": "Explicit object prices matching transaction totals, full ownership residential units on the free market; at most one observation per transaction and deed, excluding multi-object deeds; separated by market and deed year.",
            "groups": [{"market": market, "deed_year": year, "count": len(rates),
                        "median_object_price_per_m2_pln": round(safe_median(rates), 2),
                        "min_object_price_per_m2_pln": min(rates), "max_object_price_per_m2_pln": max(rates)}
                       for (market, year), rates in sorted(partitions.items(), key=lambda item: (item[0][1], item[0][0] or ""), reverse=True)],
            "is_valuation": False}


def matches(row, args, date_from, date_to):
    date = (row["deed_date"] or "")[:10]
    if not date or not date_from <= date <= date_to:
        return False
    if args.market != "all" and row["market"] != MARKETS[args.market]:
        return False
    if args.function and row["function"] != args.function:
        return False
    if args.min_area is not None and (row["area_m2"] is None or row["area_m2"] < args.min_area):
        return False
    if args.max_area is not None and (row["area_m2"] is None or row["area_m2"] > args.max_area):
        return False
    return True


def search(args, fetch=fetch_page):
    bbox, location = search_bounds(args)
    if not 1 <= args.limit <= 100 or not 1 <= args.scan_limit <= 1000:
        raise SkillError("--limit: 1–100; --scan-limit: 1–1000.")
    if any(v is not None and v <= 0 for v in (args.min_area, args.max_area)):
        raise SkillError("Powierzchnia musi być dodatnia.")
    if args.min_area is not None and args.max_area is not None and args.min_area > args.max_area:
        raise SkillError("--min-area nie może przekraczać --max-area.")
    if args.function is not None and (not args.function.strip() or len(args.function) > 100):
        raise SkillError("--function wymaga niepustej wartości do 100 znaków.")
    today = dt.date.today()
    date_from = (args.date_from or today - dt.timedelta(days=730)).isoformat()
    date_to = (args.date_to or today).isoformat()
    if date_from > date_to:
        raise SkillError("Data --from nie może być późniejsza niż --to.")
    params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
              "typeNames": "ms:" + args.layer, "sortBy": "DOK_DATA D,gid A",
              "bbox": ",".join("%.3f" % v for v in bbox) + ",EPSG:2180"}
    # Keep native CRS: the service has returned wrongly labelled untransformed
    # geometries when requesting srsName=EPSG:4326. BBOX uses official N,E axes.
    records, seen, timestamp, exhausted = [], set(), None, False
    while len(records) < args.scan_limit:
        count = min(100, args.scan_limit - len(records))
        batch, timestamp = fetch(dict(params, count=count, startIndex=len(records)))
        if len(batch) > count:
            raise SkillError("RCN przekroczył rozmiar strony.", "upstream_pagination", 69)
        for row in batch:
            if row["_feature_id"] in seen:
                raise SkillError("RCN powtórzył rekord podczas stronicowania.", "upstream_pagination", 69)
            seen.add(row["_feature_id"])
            records.append(row)
        if len(batch) < count:
            exhausted = True
            break
    normalized = [normalize(r, args.layer) for r in records]
    # Build the transaction cohort before filters so a multi-object transaction
    # cannot become apparently single-object after filtering by area/function.
    eligible_keys = {transaction_key(r) for r in normalized if comparable(r)}
    multi_keys = {key for key, count in collections.Counter(transaction_key(r) for r in normalized if transaction_key(r)).items() if count > 1}
    bad_deeds = excluded_deeds(normalized)
    filtered = [r for r in normalized if matches(r, args, date_from, date_to)]
    if not filtered:
        raise SkillError("Brak rekordów w pobranej próbie RCN dla tych filtrów; nie oznacza to braku transakcji. Przeskanowano %s rekordów; osiągnięto limit: %s." % (len(records), not exhausted), "not_found", 2)
    # Exclude all multi-row transactions from aggregates, including components
    # filtered out of the displayed list. Individual records remain inspectable.
    summary = summarize([r for r in filtered if transaction_key(r) in eligible_keys - multi_keys
                         and deed_key(r) not in bad_deeds], args.layer)
    summary["excluded_records"] = len(filtered) - summary["comparable_transactions"]
    source_url = BASE + "?" + urllib.parse.urlencode(dict(params, count=100, startIndex=0))
    return {"source": "GUGiK — Rejestr Cen Nieruchomości", "source_url": source_url,
            "documentation": DOCS, "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "upstream_timestamp": timestamp, "layer": args.layer, "location": location,
            "bbox_epsg2180_north_east": [round(v, 3) for v in bbox],
            "filters": {"from": date_from, "to": date_to, "market": args.market,
                        "function": args.function, "min_area_m2": args.min_area, "max_area_m2": args.max_area},
            "scanned_records": len(records), "scan_limit_reached": not exhausted,
            "has_more": None if not exhausted else False,
            "matched_in_sample": len(filtered), "returned_records": min(len(filtered), args.limit),
            "display_limit_reached": len(filtered) > args.limit,
            "order": "deed_date_descending", "records": filtered[:args.limit],
            "summary": summary, "notes": NOTES}


def build_parser():
    parser = Parser(description="Ceny transakcyjne RCN w ograniczonym obszarze Polski; JSON, bez klucza API.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("search", help="Szukaj lokali, budynków lub działek wokół współrzędnych albo w BBOX.")
    p.add_argument("--lat", type=finite_number, help="Szerokość WGS84, np. 52.2297.")
    p.add_argument("--lon", type=finite_number, help="Długość WGS84, np. 21.0122.")
    p.add_argument("--radius-km", type=finite_number, help="0,1–5 km; domyślnie 1. Zapytanie obejmuje kwadrat.")
    p.add_argument("--bbox", nargs=4, type=finite_number, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"))
    p.add_argument("--layer", choices=sorted(LAYERS), default="lokale")
    p.add_argument("--market", choices=["all", "pierwotny", "wtorny"], default="all")
    p.add_argument("--function", help="Dokładna funkcja źródłowa, np. mieszkalna, garaz, gruntyRolne.")
    p.add_argument("--from", dest="date_from", type=date_value, help="Data aktu YYYY-MM-DD; domyślnie 730 dni wstecz.")
    p.add_argument("--to", dest="date_to", type=date_value, help="Data aktu YYYY-MM-DD; domyślnie dzisiaj.")
    p.add_argument("--min-area", type=finite_number, help="Minimalna powierzchnia obiektu w m².")
    p.add_argument("--max-area", type=finite_number, help="Maksymalna powierzchnia obiektu w m².")
    p.add_argument("--limit", type=int, default=20, help="1–100 rekordów do wyświetlenia; domyślnie 20.")
    p.add_argument("--scan-limit", type=int, default=200, help="1–1000 najnowszych rekordów obszaru do filtrowania; domyślnie 200.")
    return parser


def main(argv=None):
    try:
        args = build_parser().parse_args(argv)
        result = search(args)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except SkillError as exc:
        print(json.dumps({"error": str(exc), "type": exc.kind}, ensure_ascii=False), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
