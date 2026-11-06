#!/usr/bin/env python3
"""Read bounded public GIS warnings from official Gov.pl HTML (stdlib only)."""

import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

LIST_URL = "https://www.gov.pl/web/gis/ostrzezenia"
LICENSE = "CC BY-SA 4.0"
NOTE = "Brak dopasowania w przeszukanej próbie nie potwierdza bezpieczeństwa produktu. Sprawdź dokładną nazwę, numer partii i datę w komunikacie GIS."
MAX_BYTES, TTL = 3 * 1024 * 1024, 300
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64, **details):
        super().__init__(message)
        self.kind, self.code, self.details = kind, code, details


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def canonical_url(value, base=LIST_URL, listing=False):
    try:
        if not isinstance(value, str) or not value.strip():
            raise ValueError()
        url = urllib.parse.urljoin(base, value.strip())
        p = urllib.parse.urlsplit(url)
        if p.scheme != "https" or p.hostname != "www.gov.pl" or p.port not in (None, 443) or p.username or p.password:
            raise ValueError()
        if not re.fullmatch(r"/web/gis/[a-z0-9][a-z0-9-]*", p.path):
            raise ValueError()
        if listing:
            if p.path != "/web/gis/ostrzezenia":
                raise ValueError()
            pairs = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
            if len(dict(pairs)) != len(pairs) or any(k not in ("page", "size") or not re.fullmatch(r"[1-9]\d{0,3}", v) for k, v in pairs):
                raise ValueError()
            if dict(pairs).get("size", "10") != "10":
                raise ValueError()
        elif p.query or p.path == "/web/gis/ostrzezenia":
            raise ValueError()
        return urllib.parse.urlunsplit(("https", "www.gov.pl", p.path, p.query, ""))
    except (ValueError, UnicodeError):
        raise SkillError("Wymagany oficjalny URL HTTPS www.gov.pl/web/gis/<komunikat>.")


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            path = urllib.parse.urlsplit(urllib.parse.urljoin(req.full_url, newurl)).path
            target = canonical_url(newurl, req.full_url, listing=path == "/web/gis/ostrzezenia")
        except SkillError:
            raise SkillError("GIS przekierował poza dozwolony zakres źródła.", "upstream_redirect", 69)
        return super().redirect_request(req, fp, code, msg, headers, target)


def timestamp(value=None):
    return dt.datetime.fromtimestamp(time.time() if value is None else value, dt.timezone.utc).isoformat()


class Client:
    def __init__(self, cache_dir=None, no_cache=False):
        root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
        self.cache_dir = Path(cache_dir) if cache_dir else root / "ai-polish-skills" / "ostrzezenia-gis"
        self.no_cache, self.last_request, self.requests = no_cache, None, []
        self.opener = urllib.request.build_opener(RestrictedRedirect())

    def fetch(self, url):
        listing = urllib.parse.urlsplit(url).path == "/web/gis/ostrzezenia"
        url = canonical_url(url, listing=listing)
        cache = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if not self.no_cache:
            try:
                if cache.stat().st_size <= MAX_BYTES * 2:
                    saved = json.loads(cache.read_text(encoding="utf-8"))
                    if saved["url"] == url and 0 <= time.time() - saved["fetched_at"] < TTL and isinstance(saved["html"], str):
                        self.requests.append({"url": url, "fetched_at": timestamp(saved["fetched_at"]), "cached": True})
                        return saved["html"]
            except (OSError, KeyError, TypeError, ValueError):
                pass
        if self.last_request is not None:
            time.sleep(max(0, 1.0 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        request = urllib.request.Request(url, headers={"User-Agent": "ai-polish-skills-ostrzezenia-gis/1.0.0", "Accept": "text/html"})
        try:
            with self.opener.open(request, timeout=20) as response:
                body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("response size")
            html = body.decode("utf-8")
        except urllib.error.HTTPError as exc:
            missing_notice = exc.code == 404 and not listing
            exc.close()
            raise SkillError("GIS HTTP %s." % exc.code, "not_found" if missing_notice else "upstream_error",
                             2 if missing_notice else 69)
        except (urllib.error.URLError, OSError) as exc:
            raise SkillError("Błąd połączenia z GIS: " + str(exc), "network_error", 69)
        except (ValueError, UnicodeError):
            raise SkillError("Nieprawidłowa lub zbyt duża odpowiedź HTML GIS.", "upstream_format", 69)
        fetched, temporary = time.time(), None
        self.requests.append({"url": url, "fetched_at": timestamp(fetched), "cached": False})
        if not self.no_cache:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(self.cache_dir), delete=False) as handle:
                    temporary = handle.name
                    json.dump({"url": url, "fetched_at": fetched, "html": html}, handle, ensure_ascii=False)
                os.replace(temporary, str(cache))
            except OSError:
                pass
            finally:
                if temporary:
                    try:
                        os.unlink(temporary)
                    except OSError:
                        pass
        return html


class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children, self.closed = tag, dict(attrs), [], False

    def has_class(self, value):
        return value in (self.attrs.get("class") or "").split()


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.node_count = 0
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.node_count += 1
        if self.node_count > 100000 or len(self.stack) > 256:
            raise SkillError("Przekroczono złożoność struktury HTML GIS.", "upstream_format", 69)
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack[i].closed = True
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def nodes(node, predicate):
    for child in node.children:
        if isinstance(child, Node):
            if predicate(child):
                yield child
            yield from nodes(child, predicate)


def text(node):
    def raw(item):
        if isinstance(item, str):
            return item
        if item.tag in ("script", "style", "noscript"):
            return ""
        if item.tag == "br":
            return "\n"
        value = "".join(raw(child) for child in item.children)
        if item.tag in ("p", "li", "div", "h2", "h3", "h4", "h5", "h6", "table", "tr", "td", "th", "ul", "ol", "section", "blockquote"):
            return "\n" + value + "\n"
        return value
    return " ".join(raw(node).split())


def first(node, predicate):
    return next(nodes(node, predicate), None)


def page_date(value):
    try:
        return dt.datetime.strptime(value.strip(), "%d.%m.%Y").date().isoformat()
    except ValueError:
        raise SkillError("GIS zwrócił nieprawidłową datę publikacji.", "upstream_format", 69)


def parse_listing(html, url):
    root = Document(html).root
    article = first(root, lambda n: n.tag == "article" and n.has_class("article-area__article"))
    preview = first(article, lambda n: n.has_class("art-prev")) if article else None
    if not article or not article.closed or not preview or not preview.closed:
        raise SkillError("Nie rozpoznano listy ostrzeżeń GIS; możliwa zmiana HTML.", "upstream_format", 69)
    output, archives = [], []
    for item in nodes(preview, lambda n: n.tag == "li"):
        title_node = first(item, lambda n: n.has_class("title"))
        link = first(title_node, lambda n: n.tag == "a") if title_node else None
        date = first(item, lambda n: n.has_class("date"))
        if not link or not text(link):
            raise SkillError("Niekompletny rekord listy GIS.", "upstream_format", 69)
        try:
            target = canonical_url(link.attrs.get("href", ""), url)
        except SkillError:
            raise SkillError("Lista GIS zawiera nieprawidłowy link komunikatu.", "upstream_format", 69)
        if date is None and re.fullmatch(r"Ostrzeżenia(?: publiczne dot\. żywności:)?\s*\d{4}(?:\s*r\.|-\d{4})?", text(link)):
            archives.append({"title": text(link), "url": target})
            continue
        if date is None:
            raise SkillError("Brak daty w rekordzie ostrzeżenia GIS.", "upstream_format", 69)
        output.append({"title": text(link), "published_at": page_date(text(date)), "url": target})
    if not output and not archives:
        raise SkillError("Pusta struktura listy GIS; nie można potwierdzić braku ostrzeżeń.", "upstream_format", 69)
    pagination = first(article, lambda n: n.tag == "nav" and n.has_class("pagination"))
    next_link = first(pagination, lambda n: n.attrs.get("id") == "js-pagination-page-next") if pagination else None
    next_url = None
    if next_link:
        try:
            next_url = canonical_url(next_link.attrs.get("href", ""), url, listing=True)
        except SkillError:
            raise SkillError("Nieprawidłowy link kolejnej strony GIS.", "upstream_format", 69)
        current_page = int(dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)).get("page", "1"))
        next_page = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(next_url).query)).get("page")
        if next_page is None or int(next_page) != current_page + 1:
            raise SkillError("GIS nie przesunął numeru strony listy.", "upstream_pagination", 69)
    if pagination is None:
        raise SkillError("Brak kontrolki stron listy GIS; nieznany zakres wyników.", "upstream_format", 69)
    return output, next_url, archives


def content_blocks(container):
    blocks = []
    def visit(node):
        if node.tag in ("script", "style", "noscript"):
            return
        if node.tag == "table":
            rows = []
            for row in nodes(node, lambda n: n.tag == "tr"):
                cells = [{"text": text(cell), "header": cell.tag == "th",
                          "colspan": cell.attrs.get("colspan", "1"), "rowspan": cell.attrs.get("rowspan", "1")}
                         for cell in nodes(row, lambda n: n.tag in ("td", "th"))]
                if cells:
                    rows.append(cells)
            if rows:
                blocks.append({"type": "table", "rows": rows})
            return
        if node.tag in ("p", "li", "h2", "h3", "h4", "h5", "h6"):
            value = text(node)
            if value:
                blocks.append({"type": "heading" if node.tag.startswith("h") else ("list_item" if node.tag == "li" else "paragraph"), "text": value})
            return
        for child in node.children:
            if isinstance(child, Node):
                visit(child)
            elif child.strip():
                blocks.append({"type": "text", "text": " ".join(child.split())})
    visit(container)
    return blocks


def parse_notice(html, url):
    root = Document(html).root
    article = first(root, lambda n: n.tag == "article" and n.has_class("article-area__article"))
    title = first(article, lambda n: n.tag == "h2") if article else None
    date = first(article, lambda n: n.has_class("event-date")) if article else None
    body = first(article, lambda n: n.has_class("editor-content")) if article else None
    if not article or not article.closed or not title or not date or not body or not body.closed:
        raise SkillError("Nie rozpoznano treści komunikatu GIS; możliwa zmiana HTML.", "upstream_format", 69)
    blocks = content_blocks(body)
    if not text(title) or not blocks:
        raise SkillError("Pusty komunikat GIS.", "upstream_format", 69)
    return {"title": text(title), "published_at": page_date(text(date)), "url": url, "content": blocks,
            "content_text": "\n".join(block.get("text", " | ".join(cell["text"] for row in block.get("rows", []) for cell in row)) for block in blocks)}


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold().replace("ł", "l")) if not unicodedata.combining(c))


def collect(client, args):
    url, seen_pages, seen_notices, listed, matches, archives = LIST_URL, [], set(), [], [], []
    searched_notices = 0
    query = normalized(args.query).split() if args.command == "search" else []
    for _ in range(args.pages):
        if url in seen_pages:
            raise SkillError("GIS powtórzył stronę listy.", "upstream_pagination", 69)
        seen_pages.append(url)
        rows, next_url, page_archives = parse_listing(client.fetch(url), url)
        archives.extend(page_archives)
        for row in rows:
            if row["url"] in seen_notices:
                raise SkillError("GIS powtórzył komunikat podczas stronicowania.", "upstream_pagination", 69)
            seen_notices.add(row["url"])
            listed.append(row)
            if (args.date_from and row["published_at"] < args.date_from) or (args.date_to and row["published_at"] > args.date_to):
                continue
            if query:
                notice = parse_notice(client.fetch(row["url"]), row["url"])
                searched_notices += 1
                haystack = normalized(notice["title"] + "\n" + notice["content_text"])
                if all(term in haystack for term in query):
                    matches.append(notice)
            else:
                matches.append(row)
        url = next_url
        if url is None:
            break
    dates = [row["published_at"] for row in listed]
    return {"query": getattr(args, "query", None), "matching": "all_words_case_and_diacritic_insensitive_substrings" if query else None,
            "notices": matches[:args.limit], "matched_in_scope": len(matches), "display_limit_reached": len(matches) > args.limit,
            "scope": {"scanned_pages": len(seen_pages), "page_urls": seen_pages, "listed_notices": len(listed),
                      "searched_notices": searched_notices,
                      "publication_date_from": args.date_from, "publication_date_to": args.date_to,
                      "oldest_listed_date": min(dates) if dates else None, "newest_listed_date": max(dates) if dates else None,
                      "next_page_url": url, "page_limit_reached": url is not None, "archive_links_not_scanned": archives,
                      "coverage": "Bounded current listing only; year archives and images are not searched."}, "note": NOTE}


def date_value(value):
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError()
        return dt.date.fromisoformat(value).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError("Wymagana data YYYY-MM-DD.")


def main(argv=None):
    parser = Parser(description="Oficjalne ostrzeżenia GIS o produktach; ograniczony odczyt HTML Gov.pl, JSON.")
    parser.add_argument("--no-cache", action="store_true", help="Pomiń cache ważny 5 minut.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    for command in ("list", "search"):
        p = sub.add_parser(command)
        if command == "search":
            p.add_argument("query", help="Wszystkie słowa muszą wystąpić w tytule lub tekście komunikatu.")
        p.add_argument("--pages", type=int, choices=range(1, 6), default=2 if command == "search" else 1, metavar="1..5")
        p.add_argument("--limit", type=int, choices=range(1, 51), default=10, metavar="1..50")
        p.add_argument("--from", dest="date_from", type=date_value)
        p.add_argument("--to", dest="date_to", type=date_value)
    p = sub.add_parser("notice")
    p.add_argument("url")
    try:
        args = parser.parse_args(argv)
        if args.command == "search" and (not args.query.strip() or len(args.query) > 200):
            raise SkillError("Podaj nazwę produktu lub marki, do 200 znaków.")
        if args.command != "notice" and args.date_from and args.date_to and args.date_from > args.date_to:
            raise SkillError("Data --from nie może być późniejsza niż --to.")
        client = Client(no_cache=args.no_cache)
        if args.command == "notice":
            url = canonical_url(args.url)
            result = parse_notice(client.fetch(url), url)
        else:
            result = collect(client, args)
        print(json.dumps({"source": "Główny Inspektorat Sanitarny", "source_url": LIST_URL, "source_type": "scraping",
                          "content_license": LICENSE, "attribution": "Źródło: Główny Inspektorat Sanitarny, Gov.pl; HTML przekształcony do tekstu/JSON.",
                          "prepared_at": timestamp(), "requests": client.requests, "result": result}, ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        print(json.dumps(dict(error=str(exc), type=exc.kind, **exc.details), ensure_ascii=False), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
