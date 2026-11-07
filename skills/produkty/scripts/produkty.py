#!/usr/bin/env python3
"""Read community food-label data from Open Food Facts; Python 3.8+ stdlib."""

import argparse
import base64
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

PRODUCT_HOST = "https://world.openfoodfacts.org"
STAGING_HOST = "https://world.openfoodfacts.net"
SEARCH_URL = "https://search.openfoodfacts.org/search"
USER_AGENT = "PolskieSkille/1.0 (mhodun@gmail.com)"
FIELDS = "code,product_name,product_name_pl,ingredients_text,ingredients_text_pl,ingredients_lc,lang,brands,brands_tags,quantity,countries_tags,allergens,allergens_tags,traces,traces_tags,tags_sources,nutrition,nutriscore_grade,nutriscore_version,nutriscore_score,completeness,data_quality_errors_tags,data_quality_warnings_tags,last_modified_t"
SEARCH_FIELDS = ["code", "product_name", "product_name_pl", "product_name.pl", "product_name.en", "brands", "quantity", "countries_tags", "last_modified_t"]


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64, **details):
        super().__init__(message)
        self.kind, self.code, self.details = kind, code, details


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def gtin(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})", value) or not value.strip("0"):
        raise SkillError("Podaj GTIN/EAN złożony z 8, 12, 13 albo 14 cyfr, bez spacji.")
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(value[:-1])))
    if (10 - total % 10) % 10 != int(value[-1]):
        raise SkillError("Nieprawidłowa cyfra kontrolna GTIN/EAN.")
    return value


def canonical(value):
    digits = value.lstrip("0") or "0"
    return digits.zfill(8 if len(digits) <= 8 else 13 if len(digits) <= 13 else 14)


def stamp(value=None):
    try:
        return dt.datetime.fromtimestamp(time.time() if value is None else value, dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError, OSError):
        raise SkillError("Nieprawidłowy czas danych Open Food Facts.", "upstream_format", 69)


def number(value):
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise SkillError("Nieprawidłowa wartość liczbowa Open Food Facts.", "upstream_format", 69)
    return value


def source_stamp(value):
    number(value)
    if value is None or value < 0:
        raise SkillError("Nieprawidłowy czas źródłowy Open Food Facts.", "upstream_format", 69)
    return stamp(value)


def array(value):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise SkillError("Nieprawidłowa lista etykiet Open Food Facts.", "upstream_format", 69)
    return value


def optional_text(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise SkillError("Nieprawidłowe pole tekstowe Open Food Facts.", "upstream_format", 69)
    return value.strip() or None


def atomic(path, data):
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
            temporary = handle.name
            json.dump(data, handle, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, str(path))
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass


class Client:
    def __init__(self, cache_dir=None, no_cache=False, staging=False):
        self.folder = Path(cache_dir or os.environ.get("PRODUKTY_CACHE_DIR") or (Path.home() / ".cache" / "ai-polish-skills" / "produkty"))
        self.no_cache, self.staging = no_cache, staging
        self.requests = []

    def pace(self, kind):
        """Reserve a slot across processes sharing the cache directory; never retry HTTP."""
        lock = self.folder / "rate.lock"
        state_path = self.folder / "rate.json"
        acquired = False
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            for unused in range(20):
                try:
                    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(fd)
                    acquired = True
                    break
                except FileExistsError:
                    try:
                        if time.time() - lock.stat().st_mtime > 30:
                            lock.unlink()
                    except FileNotFoundError:
                        pass
                    time.sleep(0.05)
            if not acquired:
                raise SkillError("Trwa inne zapytanie lokalne; spróbuj później.", "local_rate_limit", 69, retry_after=2)
            try:
                state = json.loads(state_path.read_text())
                if not isinstance(state, dict):
                    state = {}
            except (OSError, ValueError):
                state = {}
            current = time.time()
            next_at = max(float(state.get(kind, 0)), float(state.get("blocked_until", 0)), current)
            wait = next_at - current
            if wait > 10:
                raise SkillError("Odczekaj przed kolejnym zapytaniem Open Food Facts.", "local_rate_limit", 69, retry_after=math.ceil(wait))
            state[kind] = next_at + (4.1 if kind == "product" else 6.1)
            atomic(state_path, state)
        except OSError as exc:
            raise SkillError("Nie można zapisać lokalnego limitu zapytań: " + str(exc), "local_rate_limit", 69)
        finally:
            if acquired:
                try:
                    lock.unlink()
                except OSError:
                    pass
        if wait > 0:
            time.sleep(wait)

    def fetch(self, url, kind, body=None):
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True).encode() if body is not None else None
        key = hashlib.sha256(url.encode() + (encoded or b"")).hexdigest()
        cache = self.folder / (key + ".json")
        ttl = 86400 if kind == "product" else 900
        if not self.no_cache:
            try:
                stored = json.loads(cache.read_text(encoding="utf-8"))
                if stored["url"] == url and 0 <= time.time() - stored["fetched_at"] < ttl and isinstance(stored["data"], dict):
                    self.requests.append({"url": url, "fetched_at": stamp(stored["fetched_at"]), "cached": True})
                    return stored["data"]
            except (OSError, ValueError, TypeError, KeyError):
                pass
        self.pace(kind)
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if encoded is not None:
            headers["Content-Type"] = "application/json"
        if self.staging:
            headers["Authorization"] = "Basic " + base64.b64encode(b"off:off").decode()
        req = urllib.request.Request(url, data=encoded, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError("Response too large")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Expected object")
        except urllib.error.HTTPError as exc:
            status, retry = exc.code, exc.headers.get("Retry-After")
            exc.close()
            if status == 404 and kind == "product":
                raise SkillError("Nie znaleziono produktu Open Food Facts.", "not_found", 2)
            if status == 429:
                # Honour explicit upstream cooldown in future invocations as well.
                if retry and str(retry).isdigit():
                    try:
                        atomic(self.folder / "rate.json", {"blocked_until": time.time() + int(retry)})
                    except OSError:
                        pass
                raise SkillError("Limit Open Food Facts; odczekaj przed kolejną próbą.", "rate_limit", 69, retry_after=retry)
            raise SkillError("Open Food Facts HTTP " + str(status), "upstream_error", 69)
        except (urllib.error.URLError, OSError) as exc:
            raise SkillError("Open Food Facts jest niedostępne: " + str(exc), "network_error", 69)
        except (ValueError, UnicodeError):
            raise SkillError("Nieprawidłowy JSON Open Food Facts.", "upstream_format", 69)
        fetched = time.time()
        self.requests.append({"url": url, "fetched_at": stamp(fetched), "cached": False})
        if not self.no_cache:
            try:
                atomic(cache, {"url": url, "fetched_at": fetched, "data": data})
            except OSError:
                pass
        return data


def localized(product, field, language_field="lang"):
    polish = optional_text(product.get(field + "_pl"))
    if polish:
        return {"text": polish, "language": "pl", "field": field + "_pl", "polish_available": True}
    value = product.get(field)
    language = product.get(language_field) or product.get("lang") or "und"
    if isinstance(value, dict):
        for lang in ("pl", language, "en"):
            content = optional_text(value.get(lang))
            if content:
                return {"text": content, "language": lang, "field": field + "." + lang, "polish_available": lang == "pl"}
        for lang, content in value.items():
            if optional_text(content):
                return {"text": content, "language": lang, "field": field + "." + lang, "polish_available": lang == "pl"}
    else:
        content = optional_text(value)
        if content:
            return {"text": content, "language": language, "field": field, "polish_available": language == "pl"}
    return {"text": None, "language": None, "field": None, "polish_available": False}


def nutrition_set(value):
    if not isinstance(value, dict) or not isinstance(value.get("nutrients", {}), dict):
        raise SkillError("Nieprawidłowa struktura wartości odżywczych OFF 3.6.", "upstream_format", 69)
    nutrients = []
    for name, raw in value.get("nutrients", {}).items():
        if not isinstance(raw, dict):
            raise SkillError("Nieprawidłowy wpis składnika odżywczego.", "upstream_format", 69)
        nutrients.append({"name": name, "value": number(raw.get("value")), "unit": optional_text(raw.get("unit")), "modifier": optional_text(raw.get("modifier")), "value_string": optional_text(raw.get("value_string")), "value_computed": number(raw.get("value_computed")), "source": optional_text(raw.get("source")), "source_per": optional_text(raw.get("source_per"))})
    return {"per": optional_text(value.get("per")), "per_quantity": number(value.get("per_quantity")), "per_unit": optional_text(value.get("per_unit")), "preparation": optional_text(value.get("preparation")), "source": optional_text(value.get("source")), "last_updated_at": source_stamp(value["last_updated_t"]) if value.get("last_updated_t") is not None else None, "nutrients": nutrients}


def nutrition(product):
    raw = product.get("nutrition")
    if raw is None:
        return {"status": "missing", "input_sets": [], "aggregated_set": None}
    if not isinstance(raw, dict) or not isinstance(raw.get("input_sets", []), list):
        raise SkillError("Nieprawidłowe dane nutrition OFF 3.6.", "upstream_format", 69)
    inputs = [nutrition_set(v) for v in raw.get("input_sets", [])]
    aggregated = nutrition_set(raw["aggregated_set"]) if raw.get("aggregated_set") is not None else None
    return {"status": "available" if any(v["nutrients"] for v in inputs) or (aggregated and aggregated["nutrients"]) else "missing", "input_sets": inputs, "aggregated_set": aggregated}


def labels(product, field):
    tags = array(product.get(field + "_tags"))
    sources = product.get("tags_sources", {})
    if not isinstance(sources, dict):
        raise SkillError("Nieprawidłowe tags_sources OFF 3.6.", "upstream_format", 69)
    return {"tags": tags, "text": optional_text(product.get(field)), "sources": sources.get(field), "status": "reported" if tags or product.get(field) else "unknown", "absence_confirmed": False}


def summary(product):
    if not isinstance(product, dict) or not isinstance(product.get("code"), str) or not re.fullmatch(r"[0-9]{1,24}", product["code"]):
        raise SkillError("Nieprawidłowy kod produktu w odpowiedzi OFF.", "upstream_format", 69)
    code = product["code"]
    brands = product.get("brands")
    if isinstance(brands, list):
        brands = ", ".join(array(brands))
    else:
        brands = optional_text(brands)
    try:
        gtin(code)
        supported = True
    except SkillError:
        supported = False
    return {"barcode": code, "barcode_lookup_supported": supported, "name": localized(product, "product_name"), "brands": brands, "quantity": optional_text(product.get("quantity")), "countries_tags": array(product.get("countries_tags")), "last_modified_at": source_stamp(product["last_modified_t"]) if product.get("last_modified_t") is not None else None, "url": PRODUCT_HOST + "/product/" + code}


def product_lookup(client, barcode):
    gtin(barcode)
    host = STAGING_HOST if client.staging else PRODUCT_HOST
    data = client.fetch(host + "/api/v3.6/product/" + barcode + ".json?" + urllib.parse.urlencode({"fields": FIELDS}), "product")
    if data.get("result", {}).get("id") == "product_not_found":
        raise SkillError("Nie znaleziono produktu Open Food Facts.", "not_found", 2)
    if data.get("errors") or data.get("status") not in ("success", "success_with_warnings", "warning") or not isinstance(data.get("product"), dict):
        raise SkillError("Open Food Facts nie zwróciło poprawnego produktu.", "upstream_format", 69)
    product = data["product"]
    returned = product.get("code")
    if not isinstance(returned, str) or canonical(returned) != canonical(barcode) or (data.get("code") is not None and (not isinstance(data["code"], str) or canonical(data["code"]) != canonical(barcode))):
        raise SkillError("Open Food Facts zwróciło inny kod produktu niż żądany.", "upstream_mismatch", 69)
    result = summary(product)
    result["url"] = host + "/product/" + product["code"]
    grade = optional_text(product.get("nutriscore_grade"))
    completeness = number(product.get("completeness"))
    if completeness is not None and not 0 <= completeness <= 1:
        raise SkillError("Nieprawidłowy wskaźnik kompletności OFF.", "upstream_format", 69)
    result.update(requested_barcode=barcode, normalized_barcode=canonical(barcode), ingredients=localized(product, "ingredients_text", "ingredients_lc"), allergens=labels(product, "allergens"), traces=labels(product, "traces"), nutrition=nutrition(product), nutriscore={"grade": grade if grade in ("a", "b", "c", "d", "e") else None, "source_grade": grade, "score": number(product.get("nutriscore_score")), "version": product.get("nutriscore_version"), "calculated_by_skill": False}, completeness=completeness, quality_errors=array(product.get("data_quality_errors_tags")), quality_warnings=array(product.get("data_quality_warnings_tags")), source_warnings=data.get("warnings") or [])
    result["missing_fields"] = [name for name, value in (("name", result["name"]["text"]), ("ingredients", result["ingredients"]["text"]), ("quantity", result["quantity"]), ("allergens", result["allergens"]["status"] == "reported"), ("traces", result["traces"]["status"] == "reported"), ("nutrition", result["nutrition"]["status"] == "available"), ("nutriscore", result["nutriscore"]["grade"])) if not value]
    return result


def search(client, query, scope="poland", page=1, limit=10):
    if client.staging:
        raise SkillError("--staging obsługuje barcode; Search-a-licious nie ma tu zweryfikowanego środowiska staging. Testy search uruchamiaj offline.")
    # Do not allow a plain product name to inject Lucene filters or operators.
    plain = " ".join(re.sub(r"[^\w\s]", " ", query.casefold()).split())
    if not plain or len(query) > 150:
        raise SkillError("Podaj nazwę lub markę produktu do 150 znaków.")
    lucene = ('countries_tags:"en:poland" ' if scope == "poland" else "") + plain
    data = client.fetch(SEARCH_URL, "search", {"q": lucene, "langs": ["pl", "en"], "page": page, "page_size": limit, "fields": SEARCH_FIELDS})
    if data.get("errors") or data.get("timed_out") is not False or not isinstance(data.get("hits"), list):
        raise SkillError("Wyszukiwanie OFF nie zwróciło kompletnej poprawnej strony.", "upstream_format", 69)
    for name in ("page", "page_size", "page_count", "count"):
        if not isinstance(data.get(name), int) or isinstance(data[name], bool) or data[name] < 0:
            raise SkillError("Nieprawidłowa paginacja wyszukiwania OFF.", "upstream_format", 69)
    if data["page"] != page or data["page_size"] != limit or len(data["hits"]) > limit:
        raise SkillError("OFF zwróciło inną stronę wyników.", "upstream_mismatch", 69)
    exact = data.get("is_count_exact")
    if not isinstance(exact, bool):
        raise SkillError("Nieprawidłowa informacja o dokładności liczby wyników OFF.", "upstream_format", 69)
    if data["hits"] and (data["count"] < len(data["hits"]) or data["page_count"] < page):
        raise SkillError("Sprzeczna liczba wyników i stron OFF.", "upstream_format", 69)
    if exact and (data["page_count"] != math.ceil(data["count"] / limit) or len(data["hits"]) != min(limit, max(0, data["count"] - (page - 1) * limit))):
        raise SkillError("Niezgodna dokładna paginacja wyników OFF.", "upstream_format", 69)
    products = [summary(p) for p in data["hits"]]
    if scope == "poland" and any("en:poland" not in p["countries_tags"] for p in products):
        raise SkillError("Wyniki OFF nie spełniają filtra kraju sprzedaży Polska.", "upstream_mismatch", 69)
    if not products:
        raise SkillError("Nie znaleziono produktów dla zapytania i zakresu.", "not_found", 2)
    return {"query": query, "normalized_query": plain, "scope": scope, "country_filter": "en:poland" if scope == "poland" else None, "country_meaning": "Deklarowany kraj sprzedaży, nie pochodzenie produktu ani dostępność w sklepie.", "products": products, "page": page, "page_size": limit, "page_count": data["page_count"], "count": data["count"], "count_exact": data.get("is_count_exact"), "has_more": page < data["page_count"], "source_warnings": data.get("warnings") or [], "details": "Wyniki są skrótem indeksu wyszukiwania. Odczytaj barcode wybranego produktu, aby pobrać skład i wartości odżywcze."}


def main(argv=None):
    try:
        parser = Parser(description="Skład, alergeny i wartości odżywcze z bazy społecznościowej Open Food Facts; bez cen i zakupów.")
        parser.add_argument("--no-cache", action="store_true")
        parser.add_argument("--cache-dir")
        parser.add_argument("--staging", action="store_true", help="Testowy serwer OFF, tylko barcode; testy search są offline.")
        sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
        p = sub.add_parser("barcode", help="Produkt według GTIN/EAN-8/12/13/14")
        p.add_argument("barcode")
        p = sub.add_parser("search", help="Nazwa lub marka; domyślnie produkty zgłoszone jako sprzedawane w Polsce")
        p.add_argument("query")
        p.add_argument("--scope", choices=("poland", "world"), default="poland")
        p.add_argument("--page", type=int, default=1)
        p.add_argument("--limit", type=int, default=10)
        args = parser.parse_args(argv)
        client = Client(args.cache_dir, args.no_cache, args.staging)
        if args.command == "barcode":
            result = product_lookup(client, args.barcode)
        else:
            if not 1 <= args.page <= 100 or not 1 <= args.limit <= 20:
                raise SkillError("--page: 1–100; --limit: 1–20.")
            result = search(client, args.query, args.scope, args.page, args.limit)
        output = {"source": "Open Food Facts", "source_type": "community_database", "api": "3.6" if args.command == "barcode" else "Search-a-licious", "environment": "staging" if args.staging else "production", "license": {"database": "ODbL 1.0", "contents": "DbCL 1.0", "attribution": "Open Food Facts contributors", "url": "https://world.openfoodfacts.org/terms-of-use"}, "fetched_at": stamp(), "requests": client.requests, "result": result, "notice": "Dane społecznościowe mogą być niepełne lub błędne; sprawdź aktualne opakowanie. Brak wpisu o alergenie lub śladach nie potwierdza ich braku. Wskaźnik kompletności nie mierzy poprawności danych."}
        print(json.dumps(output, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        print(json.dumps(dict(error=str(exc), type=exc.kind, **exc.details), ensure_ascii=False), file=sys.stderr)
        return exc.code
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        print(json.dumps({"error": "Nieprawidłowa struktura danych Open Food Facts.", "type": "upstream_format"}), file=sys.stderr)
        return 69


if __name__ == "__main__":
    sys.exit(main())
