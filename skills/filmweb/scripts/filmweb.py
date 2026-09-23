#!/usr/bin/env python3
"""Filmweb.pl CLI for AI agents. Python 3.8+, standard library only.

Uses the JSON API behind www.filmweb.pl (https://www.filmweb.pl/api/v1).
Prints JSON to stdout; errors go to stderr as {"error": ..., "type": ...}.
Run without arguments to list commands.
"""

import datetime
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://www.filmweb.pl/api/v1"
SITE_URL = "https://www.filmweb.pl"
POSTER_URL = "https://fwcdn.pl/fpo"
PERSON_URL = "https://fwcdn.pl/ppo"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (filmweb-skill)",
    "Accept": "application/json",
    "x-locale": "pl_PL",
}
TIMEOUT = 15

EXIT_OK, EXIT_NOT_FOUND, EXIT_USAGE, EXIT_API_ERROR = 0, 2, 64, 69

# Path segment used by the API and the website for each title type.
TYPE_PATHS = {"film": "film", "serial": "serial", "game": "videogame"}


class UsageError(Exception):
    pass


class NotFound(Exception):
    pass


class ApiError(Exception):
    pass


def get(path, params=None):
    """GET an API path and return decoded JSON; raise NotFound on 404."""
    url = API_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise NotFound()
        raise ApiError("HTTP %d for %s" % (e.code, path))
    except (urllib.error.URLError, OSError) as e:
        raise ApiError("Request failed: %s" % e)
    if not body.strip():
        raise NotFound()
    try:
        return json.loads(body)
    except ValueError:
        raise ApiError("Cannot parse response for %s: %s" % (path, body[:200]))


def get_optional(path):
    try:
        return get(path)
    except NotFound:
        return None


def title_id(value):
    if value and re.fullmatch(r"\d+", value):
        return int(value)
    match = re.search(
        r"filmweb\.pl/(?:film|serial|videogame|game)/[^/?#]*-(\d+)(?:[/?#]|$)", value or ""
    )
    if match:
        return int(match.group(1))
    raise UsageError('Expected a numeric Filmweb ID or a filmweb.pl title URL, got "%s".' % value)


def strip_markup(text):
    """Turn '[person=87]Keanu Reeves[/person]' style tags into plain text."""
    if not isinstance(text, str):
        return text
    return re.sub(r"\[/?[a-z]+(?:=[^\]]*)?\]", "", text).strip()


def poster_url(path, base=POSTER_URL, size=3):
    return base + path.replace("$", str(size)) if path else None


def page_url(kind, title, year, tid):
    path = TYPE_PATHS.get(kind, "film")
    return "%s/%s/%s-%s-%d" % (SITE_URL, path, (title or "").replace(" ", "+"), year or "", tid)


def date_int(value):
    """20100730 -> '2010-07-30'."""
    s = str(value or "")
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8]) if len(s) == 8 else None


def names(items):
    return [{"id": i.get("id"), "name": i.get("name")} for i in items or []]


def parallel(func, items):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(func, items))


def cmd_search(query, kind, limit):
    if not query:
        raise UsageError('search needs a query, e.g.: search "matrix"')
    data = get("/live/search", {"query": query})
    hits = data.get("searchHits") or []
    if kind:
        hits = [h for h in hits if h.get("type") == kind]
    return [
        {
            "id": h.get("id"),
            "type": h.get("type"),
            "title": h.get("matchedTitle"),
            "mainCast": [c.get("name") for c in h.get("filmMainCast") or []],
        }
        for h in hits[:limit]
    ]


def cmd_film(tid):
    info = get("/title/%d/info" % tid)
    base = "/film/%d" % tid
    rating, critics, preview = parallel(
        get_optional, [base + "/rating", base + "/critics/rating", base + "/preview"]
    )
    rating, critics, preview = rating or {}, critics or {}, preview or {}
    plot = preview.get("plot") or {}
    return {
        "id": tid,
        "title": info.get("title"),
        "originalTitle": info.get("originalTitle"),
        "year": info.get("year"),
        "type": info.get("type"),
        "subType": info.get("subType"),
        "url": page_url(info.get("type"), info.get("title"), info.get("year"), tid),
        "posterUrl": poster_url(info.get("posterPath")),
        "rating": rating.get("rate"),
        "votesCount": rating.get("count"),
        "wantToSeeCount": rating.get("countWantToSee"),
        "votesDistribution": {
            str(n): rating["countVote%d" % n] for n in range(1, 11) if "countVote%d" % n in rating
        },
        "criticsRating": critics.get("rate"),
        "criticsCount": critics.get("count"),
        "genres": [(g.get("name") or {}).get("text") for g in preview.get("genres") or []],
        "countries": [c.get("code") for c in preview.get("countries") or []],
        "duration": preview.get("duration"),
        "directors": names(preview.get("directors")),
        "mainCast": names(preview.get("mainCast")),
        "plot": strip_markup(plot.get("synopsis") or preview.get("plotOrDescriptionSynopsis")),
        "siteRecommends": bool(preview.get("siteRecommends")),
    }


def cmd_description(tid):
    data = get("/film/%d/description" % tid)
    return {"id": tid, "description": strip_markup(data.get("synopsis"))}


def person_name(pid):
    info = get_optional("/person/%d/info" % pid) or {}
    return info.get("name")


def cmd_cast(tid, limit):
    roles = (get("/film/%d/top-roles" % tid) or [])[:limit]
    people = parallel(person_name, [r.get("person") for r in roles])
    return [
        {
            "personId": r.get("person"),
            "name": name,
            "profession": r.get("profession"),
            "roleRating": r.get("rate"),
            "roleVotes": r.get("count"),
        }
        for r, name in zip(roles, people)
    ]


def cmd_dates(tid):
    data = get("/film/%d/dates" % tid)
    labels = {
        "worldReleaseDate": "worldPremiere",
        "worldPublicReleaseDate": "worldRelease",
        "countryPublicReleaseDate": "polandRelease",
        "countryReissueLastPublicDate": "polandReissue",
    }
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[labels.get(key, key)] = {
                "date": date_int(value.get("dateInt")),
                "country": value.get("country"),
                "cinemas": bool(value.get("cinemasRelease")),
            }
    return result


def cmd_vod(tid):
    offers = get("/vod/film/%d/providers/list" % tid) or []
    providers = {p.get("id"): p for p in get_optional("/vod/providers/list") or []}
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    result = []
    for o in offers:
        if o.get("end") and o["end"] < now:
            continue
        provider = providers.get(o.get("vodProvider")) or {}
        modes = []
        for pay in o.get("payments") or []:
            mode = next((m for m in ("subscription", "free", "rent", "buy") if pay.get(m)), None)
            price = pay.get("price")
            modes.append({
                "type": mode,
                "pricePLN": round(price / 100.0, 2) if price else None,
            })
        if not modes:
            # Offers without payments are usually part of the provider's subscription.
            modes.append({"type": "subscription" if provider.get("abonaments") else None, "pricePLN": None})
        # Deduplicate identical offers (e.g. the same price in SD and HD).
        unique = [dict(m) for m in {tuple(sorted(m.items())) for m in modes}]
        result.append({
            "provider": provider.get("displayName") or o.get("vodProvider"),
            "link": o.get("link"),
            "availableFrom": o.get("start"),
            "availableUntil": o.get("end"),
            "offers": sorted(unique, key=lambda m: (m["type"] or "", m["pricePLN"] or 0)),
        })
    return result


def cmd_person(pid):
    data = get("/person/%d/preview" % pid)
    info = data.get("info") or {}
    return {
        "id": pid,
        "name": data.get("name"),
        "realName": info.get("realName"),
        "birthDate": date_int(info.get("birthDateInt")),
        "birthplace": (data.get("birthplace") or {}).get("cityName"),
        "height": info.get("height"),
        "mainProfession": data.get("mainProfession"),
        "photoUrl": poster_url((data.get("poster") or {}).get("path"), PERSON_URL),
        "knownForIds": data.get("filmsKnownFor") or [],
        "url": "%s/person/%s-%d" % (SITE_URL, (data.get("name") or "").replace(" ", "+"), pid),
    }


COMMANDS = {
    "search": ('"<query>" [--type=film|serial|game] [--limit=10]', "find titles by name"),
    "film": ("<id|url>", "title, year, ratings, genres, countries, duration, directors, main cast, plot"),
    "description": ("<id|url>", "full plot description"),
    "cast": ("<id|url> [--limit=10]", "top-rated roles with actor names"),
    "dates": ("<id|url>", "world and Polish premiere dates"),
    "vod": ("<id|url>", "where to watch: VOD providers, links, prices"),
    "person": ("<personId>", "actor/director details"),
    "id": ("<url>", "extract the Filmweb ID from a URL (offline)"),
}


def run(argv):
    options, positional = {}, []
    for arg in argv:
        match = re.fullmatch(r"--([a-z-]+)=(.*)", arg)
        if match:
            options[match.group(1)] = match.group(2)
        else:
            positional.append(arg)
    command = positional[0] if positional else None
    arg = " ".join(positional[1:])

    if command not in COMMANDS:
        usage = "\n".join("  %-12s %-50s %s" % (n, a, d) for n, (a, d) in COMMANDS.items())
        sys.stderr.write("Usage: python3 filmweb.py <command> [arguments]\n\n%s\n" % usage)
        return EXIT_OK if command is None else EXIT_USAGE

    try:
        limit = int(options.get("limit", 10))
    except ValueError:
        raise UsageError("--limit must be a number.")

    if command == "search":
        return cmd_search(arg, options.get("type"), limit)
    if command == "id":
        return {"id": title_id(arg)}
    if command == "person":
        if not arg.isdigit():
            raise UsageError("person needs a numeric person ID (see cast / film output).")
        return cmd_person(int(arg))
    tid = title_id(arg)
    if command == "film":
        return cmd_film(tid)
    if command == "description":
        return cmd_description(tid)
    if command == "cast":
        return cmd_cast(tid, limit)
    if command == "dates":
        return cmd_dates(tid)
    return cmd_vod(tid)


def fail(code, message, kind):
    sys.stderr.write(json.dumps({"error": message, "type": kind}, ensure_ascii=False) + "\n")
    return code


def main():
    # Windows consoles default to a legacy code page; force UTF-8 for Polish characters.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        result = run(sys.argv[1:])
    except UsageError as e:
        return fail(EXIT_USAGE, str(e), "usage")
    except NotFound:
        return fail(EXIT_NOT_FOUND, "Not found.", "not_found")
    except ApiError as e:
        return fail(EXIT_API_ERROR, str(e), "api")
    if isinstance(result, int):
        return result
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
