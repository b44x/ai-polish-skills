#!/usr/bin/env python3
"""Offline GIS parser, bounded search, URL restriction and provenance regressions."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("ostrzezenia_gis", str(ROOT / "skills/ostrzezenia-gis/scripts/ostrzezenia_gis.py"))
gis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gis)
FIXTURES = ROOT / "skills/ostrzezenia-gis/resources"
URL_A = "https://www.gov.pl/web/gis/ostrzezenie-test-a"
URL_B = "https://www.gov.pl/web/gis/ostrzezenie-test-b"
PAGE_2 = gis.LIST_URL + "?page=2&size=10"


def listing(rows, next_href=None):
    items = "".join('<li><span class="date">%s</span><div class="title"><a href="%s">%s</a></div></li>' % row for row in rows)
    next_html = '<a id="js-pagination-page-next" href="%s"></a>' % next_href if next_href else ""
    return '<article class="article-area__article"><div class="art-prev"><ul>%s</ul></div><nav class="pagination">%s</nav></article>' % (items, next_html)


def notice(title="Ostrzeżenie testowe", body="<p>Produkt testowy, partia 00ABC-01.</p>"):
    return '<article class="article-area__article"><h2>%s</h2><p class="event-date">28.10.2026</p><div class="editor-content">%s</div></article>' % (title, body)


def invoke(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = gis.main(args)
    return code, out.getvalue(), err.getvalue()


class ParserTests(unittest.TestCase):
    def test_live_snapshot_listing_uses_real_next_link(self):
        rows, next_url, archives = gis.parse_listing((FIXTURES / "listing.html").read_text(), gis.LIST_URL)
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["published_at"], "2026-10-28")
        self.assertEqual(next_url, PAGE_2)
        self.assertEqual(archives, [])

    def test_live_snapshot_preserves_batch_and_expiry_as_text(self):
        result = gis.parse_notice((FIXTURES / "notice.html").read_text(), URL_A)
        self.assertEqual(result["published_at"], "2026-10-28")
        self.assertIn("Numer partii: 0708BW06O", result["content_text"])
        self.assertIn("Data minimalnej trwałości: 07.08.2027", result["content_text"])
        self.assertNotIn("stopka", result["content_text"])

    def test_tables_lists_entities_and_inline_text_are_preserved(self):
        result = gis.parse_notice(notice(body='<h3>Szczeg&oacute;ły</h3><p>Nazwa: Żelki &amp; sok<br>Partia <b>001X</b></p><ul><li>Nie spożywać.</li></ul><table><tr><th>Partia</th><th>Data</th></tr><tr><td rowspan="2">00A-01</td><td>01.02.2027</td></tr></table>'), URL_A)
        self.assertIn("Żelki & sok", result["content_text"])
        self.assertIn("Partia 001X", result["content_text"])
        self.assertIn("00A-01", result["content_text"])
        table = next(block for block in result["content"] if block["type"] == "table")
        self.assertEqual(table["rows"][1][0], {"text": "00A-01", "header": False, "colspan": "1", "rowspan": "2"})
        self.assertTrue(any(b["type"] == "list_item" for b in result["content"]))

    def test_archive_links_are_explicitly_skipped(self):
        html = '<article class="article-area__article"><div class="art-prev"><ul><li><div class="title"><a href="/web/gis/ostrzezenia-2024-r">Ostrzeżenia 2024 r.</a></div></li></ul></div><nav class="pagination"></nav></article>'
        rows, next_url, archives = gis.parse_listing(html, gis.LIST_URL)
        self.assertEqual(rows, [])
        self.assertIsNone(next_url)
        self.assertEqual(archives[0]["title"], "Ostrzeżenia 2024 r.")

    def test_adjacent_blocks_are_separated_but_inline_batch_fragments_join(self):
        result = gis.parse_notice(notice(body='<ul><li><p>Partia A</p><p>Partia B</p><ul><li>Partia C</li></ul></li></ul><p>Numer: <b>00</b><em>1X</em>.</p>'), URL_A)
        self.assertIn("Partia A Partia B Partia C", result["content_text"])
        self.assertIn("Numer: 001X.", result["content_text"])

    def test_unrecognized_empty_or_malformed_listing_is_error(self):
        for html in ["<html>Server maintenance</html>", listing([]), listing([("28.10.2026", URL_A, "Test")]).replace('</article>', ''),
                     listing([("28.10.2026", URL_A, "Test")]).replace('class="date"', 'class="changed-date"'),
                     listing([("28.10.2026", URL_A, "Test")]).replace('<nav class="pagination"></nav>', '')]:
            with self.subTest(html=html[:70]), self.assertRaises(gis.SkillError) as error:
                gis.parse_listing(html, gis.LIST_URL)
            self.assertEqual(error.exception.code, 69)

    def test_detail_without_expected_body_is_error(self):
        for html in ["<html>blocked</html>", notice(body=""), notice().replace('</div></article>', '</article>')]:
            with self.assertRaises(gis.SkillError) as error:
                gis.parse_notice(html, URL_A)
            self.assertEqual(error.exception.code, 69)

    def test_bad_date_or_untrusted_list_link_is_upstream_error(self):
        for row in [("31.02.2026", URL_A, "Test"), ("28.10.2026", "https://evil.example/", "Test")]:
            with self.assertRaises(gis.SkillError) as error:
                gis.parse_listing(listing([row]), gis.LIST_URL)
            self.assertEqual(error.exception.code, 69)

    def test_missing_href_is_structured_upstream_error(self):
        html = listing([("28.10.2026", URL_A, "Test")]).replace('href="%s"' % URL_A, 'href')
        with self.assertRaises(gis.SkillError) as error:
            gis.parse_listing(html, gis.LIST_URL)
        self.assertEqual(error.exception.code, 69)

    def test_deep_html_does_not_escape_as_python_recursion_error(self):
        html = notice(body='<div>' * 300 + '<p>Test</p>' + '</div>' * 300)
        with self.assertRaises(gis.SkillError) as error:
            gis.parse_notice(html, URL_A)
        self.assertEqual(error.exception.code, 69)

    def test_pagination_must_move_to_actual_next_page(self):
        for next_url in ['?page=1&size=10', '?page=3&size=10', 'https://evil.example/']:
            with self.assertRaises(gis.SkillError) as error:
                gis.parse_listing(listing([("28.10.2026", URL_A, "Test")], next_url), gis.LIST_URL)
            self.assertEqual(error.exception.code, 69)


class ScopeTests(unittest.TestCase):
    def run_command(self, args, pages):
        calls = []
        def fetch(client, url):
            calls.append(url)
            return pages[url]
        with patch.object(gis.Client, "fetch", fetch):
            code, out, err = invoke(args)
        self.assertEqual((code, err), (0, ""))
        return json.loads(out), calls

    def test_search_reads_brand_from_body_and_ignores_accents_case(self):
        pages = {gis.LIST_URL: listing([("28.10.2026", URL_A, "Ostrzeżenie")]),
                 URL_A: notice(body='<p>ŻÓŁĆ &amp; żelki, partia 000A.</p>')}
        result, calls = self.run_command(["search", "zolc ZELKI"], pages)
        self.assertEqual(result["result"]["matched_in_scope"], 1)
        self.assertEqual(result["result"]["scope"]["searched_notices"], 1)
        self.assertEqual(calls, [gis.LIST_URL, URL_A])

    def test_all_query_words_are_required(self):
        pages = {gis.LIST_URL: listing([("28.10.2026", URL_A, "Ostrzeżenie")]), URL_A: notice(body="<p>Żelki testowe</p>")}
        result, _ = self.run_command(["search", "zelki nieobecne"], pages)
        self.assertEqual(result["result"]["notices"], [])
        self.assertIn("nie potwierdza", result["result"]["note"])

    def test_two_pages_are_searched_even_when_display_limit_is_one(self):
        pages = {gis.LIST_URL: listing([("28.10.2026", URL_A, "Test A")], '?page=2&amp;size=10'),
                 PAGE_2: listing([("20.10.2026", URL_B, "Test B")]), URL_A: notice(), URL_B: notice()}
        result, calls = self.run_command(["search", "produkt", "--pages", "2", "--limit", "1"], pages)
        scope = result["result"]["scope"]
        self.assertEqual(scope["scanned_pages"], 2)
        self.assertEqual(scope["listed_notices"], 2)
        self.assertEqual(result["result"]["matched_in_scope"], 2)
        self.assertTrue(result["result"]["display_limit_reached"])
        self.assertEqual(len(result["result"]["notices"]), 1)
        self.assertIn(PAGE_2, calls)

    def test_date_filter_applies_within_scanned_pages_only(self):
        pages = {gis.LIST_URL: listing([("28.10.2026", URL_A, "Test"), ("01.09.2026", URL_B, "Old")]), URL_A: notice()}
        result, calls = self.run_command(["search", "produkt", "--from", "2026-10-01"], pages)
        self.assertNotIn(URL_B, calls)
        self.assertEqual(result["result"]["scope"]["oldest_listed_date"], "2026-09-01")
        self.assertEqual(result["result"]["scope"]["searched_notices"], 1)

    def test_page_limit_reports_unread_next_link(self):
        pages = {gis.LIST_URL: listing([("28.10.2026", URL_A, "Test")], '?page=2&size=10')}
        result, calls = self.run_command(["list", "--pages", "1"], pages)
        self.assertTrue(result["result"]["scope"]["page_limit_reached"])
        self.assertEqual(result["result"]["scope"]["next_page_url"], PAGE_2)
        self.assertEqual(calls, [gis.LIST_URL])

    def test_repeated_notice_is_pagination_error(self):
        pages = {gis.LIST_URL: listing([("28.10.2026", URL_A, "Test")], '?page=2&size=10'),
                 PAGE_2: listing([("28.10.2026", URL_A, "Test")])}
        with patch.object(gis.Client, "fetch", lambda client, url: pages[url]):
            code, out, err = invoke(["list", "--pages", "2"])
        self.assertEqual((code, out), (69, ""))
        self.assertEqual(json.loads(err)["type"], "upstream_pagination")

    def test_invalid_cli_inputs_never_fetch(self):
        for args in [["notice", "https://evil.example/"], ["search", " "], ["list", "--pages", "6"],
                     ["list", "--from", "2026-11-01", "--to", "2026-10-01"], ["list", "--from", "2026-02-31"]]:
            with self.subTest(args=args), patch.object(gis.Client, "fetch", side_effect=AssertionError("unexpected network")):
                code, out, err = invoke(args)
            self.assertEqual((code, out), (64, ""))
            self.assertIn("error", json.loads(err))


class NetworkTests(unittest.TestCase):
    def test_notice_url_restrictions(self):
        self.assertEqual(gis.canonical_url('/web/gis/ostrzezenie-test-a#partia'), URL_A)
        for value in ['http://www.gov.pl/web/gis/a', 'https://gov.pl/web/gis/a', 'https://www.gov.pl.evil.example/web/gis/a',
                      'https://user:pass@www.gov.pl/web/gis/a', 'https://www.gov.pl/web/gis/../a',
                      'https://www.gov.pl/web/gis/%2fexample', 'https://www.gov.pl/web/gis/a?redirect=https://evil.example',
                      'https://www.gov.pl:444/web/gis/a', gis.LIST_URL]:
            with self.subTest(value=value), self.assertRaises(gis.SkillError):
                gis.canonical_url(value)

    def test_external_redirect_is_rejected_before_following(self):
        handler = gis.RestrictedRedirect()
        request = gis.urllib.request.Request(URL_A)
        with self.assertRaises(gis.SkillError) as error:
            handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example/")
        self.assertEqual(error.exception.kind, "upstream_redirect")

    def test_cache_preserves_source_time_and_expires_without_stale_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            first = gis.Client(cache_dir=folder)
            first.opener.open = Mock(return_value=io.BytesIO(b'<html>test</html>'))
            with patch.object(gis.time, "time", return_value=1000):
                self.assertEqual(first.fetch(URL_A), '<html>test</html>')
            cached = gis.Client(cache_dir=folder)
            cached.opener.open = Mock(side_effect=AssertionError("fresh cache should avoid network"))
            with patch.object(gis.time, "time", return_value=1299):
                self.assertEqual(cached.fetch(URL_A), '<html>test</html>')
            self.assertEqual(cached.requests[0]["fetched_at"], gis.timestamp(1000))
            self.assertTrue(cached.requests[0]["cached"])
            cached.opener.open = Mock(side_effect=urllib.error.URLError("offline"))
            with patch.object(gis.time, "time", return_value=1300), self.assertRaises(gis.SkillError) as error:
                cached.fetch(URL_A)
            self.assertEqual(error.exception.code, 69)

    def test_listing_404_is_upstream_failure_notice_404_is_not_found(self):
        for url, expected in [(gis.LIST_URL, 69), (URL_A, 2)]:
            client = gis.Client(no_cache=True)
            client.opener.open = Mock(side_effect=urllib.error.HTTPError(url, 404, "Not found", {}, io.BytesIO()))
            with self.assertRaises(gis.SkillError) as error:
                client.fetch(url)
            self.assertEqual(error.exception.code, expected)

    def test_http_429_does_not_retry(self):
        client = gis.Client(no_cache=True)
        client.opener.open = Mock(side_effect=urllib.error.HTTPError(URL_A, 429, "Rate limit", {}, io.BytesIO()))
        with self.assertRaises(gis.SkillError) as error:
            client.fetch(URL_A)
        self.assertEqual(error.exception.code, 69)
        self.assertEqual(client.opener.open.call_count, 1)

    def test_oversize_and_non_utf8_response_are_errors(self):
        for body in [b'x' * (gis.MAX_BYTES + 1), b'\xff']:
            client = gis.Client(no_cache=True)
            client.opener.open = Mock(return_value=io.BytesIO(body))
            with self.assertRaises(gis.SkillError) as error:
                client.fetch(URL_A)
            self.assertEqual(error.exception.code, 69)

    def test_network_requests_are_spaced(self):
        client = gis.Client(no_cache=True)
        client.opener.open = Mock(side_effect=[io.BytesIO(b'one'), io.BytesIO(b'two')])
        with patch.object(gis.time, "monotonic", side_effect=[0, 0.1, 0.1]), patch.object(gis.time, "sleep") as sleep:
            client.fetch(URL_A)
            client.fetch(URL_B)
        sleep.assert_called_once_with(0.9)


if __name__ == "__main__":
    unittest.main()
