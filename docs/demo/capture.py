#!/usr/bin/env python3
"""Capture live data for the Polskie Skille demo video.

Runs the real, unmodified skill scripts from ``skills/`` against the official
upstream APIs and writes ``demo_data.json``: for every scene the exact command,
exit code, duration, capture timestamp, the raw JSON returned by the skill and a
short human-readable "card" derived from it. Nothing is invented: if a skill call
fails, the capture fails (no offline fixtures, no fallbacks with fake values).

Usage:
    python3 docs/demo/capture.py [--out docs/demo/demo_data.json]

Optional environment:
    DEMO_INPOST_TRACKING  24-digit InPost number of a parcel you own. It is
                          masked in the video. Without it, the InPost scene
                          shows a live Paczkomat lookup instead of tracking.

Python 3.8+ standard library only.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
RETRIES = 2
PAUSE_S = 2.0  # be gentle with public APIs (NFZ/MF sit behind rate-limiting WAFs)


class CaptureError(Exception):
    pass


def run_skill(skill: str, *args: str) -> Dict[str, Any]:
    """Run a skill script and return its parsed stdout plus provenance."""
    script = SKILLS / skill / "scripts" / f"{skill.replace('-', '_')}.py"
    argv = [sys.executable, str(script), *args]
    shown = ["python3", str(script.relative_to(ROOT)), *args]
    last_err = ""
    for attempt in range(1, RETRIES + 1):
        time.sleep(PAUSE_S)
        started = time.monotonic()
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180)
        duration_ms = int((time.monotonic() - started) * 1000)
        if proc.returncode == 0:
            return {
                "command": shown,
                "exitCode": 0,
                "durationMs": duration_ms,
                "attempts": attempt,
                "capturedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "output": json.loads(proc.stdout),
            }
        last_err = (proc.stderr or proc.stdout).strip()[:300]
        # Retry only upstream/network errors (exit 69), never throttling or usage failures.
        if proc.returncode != 69:
            break
        try:
            error = json.loads(proc.stderr)
        except ValueError:
            error = {}
        if error.get("retry_after") or error.get("http_status") == 429 or error.get("type") in ("rate_limit", "local_rate_limit"):
            break
        print(f"  … {skill} {' '.join(args)}: attempt {attempt} failed ({last_err[:90]})", file=sys.stderr)
        time.sleep(min(5 * attempt, 40))
    raise CaptureError(f"{skill} {' '.join(args)} failed: {last_err}")


def warsaw_time(utc_text: str) -> str:
    """'2026-09-28 13:00 UTC' -> '15:00' (Europe/Warsaw)."""
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
    except ImportError:  # pragma: no cover
        return ""
    dt = datetime.datetime.strptime(utc_text, "%Y-%m-%d %H:%M UTC").replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(ZoneInfo("Europe/Warsaw")).strftime("%H:%M")


def pln(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " zł"


def short(text: Optional[str], limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def mask_tracking(num: str) -> str:
    return num[:4] + " •••• •••• •••• •••• " + num[-4:]


# --------------------------------------------------------------------------- scenes

def scene_biala_lista() -> Dict[str, Any]:
    nip = "5261040828"
    run = run_skill("biala-lista", "nip", nip)
    o = run["output"]
    rows = [
        ["NIP", o["nipFormatted"]],
        ["Status VAT", o["statusVat"]],
        ["REGON", o["regon"]],
        ["Adres", o["workingAddress"] or o["residenceAddress"] or "—"],
        ["Rachunki na Białej Liście", str(o["accountCount"])],
    ]
    return {
        "id": "biala-lista",
        "question": f"Sprawdź firmę po NIP {nip}",
        "skill": "biala-lista",
        "source": "Ministerstwo Finansów",
        "sourceShort": "Biała Lista VAT",
        "runs": [run],
        "card": {"title": o["name"], "badge": o["statusVat"], "badgeOk": o["isVatActive"], "rows": rows},
        "footer": f"Źródło: wl-api.mf.gov.pl · stan na {o['requestDateTime']} · requestId {o['requestId']}",
    }


def scene_krs() -> Dict[str, Any]:
    # The demo NIP (GUS) is a state office with no KRS entry, so the KRS scene uses
    # the company documented as the KRS example in this repository.
    krs = "0000006865"
    run = run_skill("krs", "repr", krs)
    o = run["output"]
    people = [f"{p['nazwisko']} — {p['funkcja'].lower()}" for p in o["zarzad"]]
    proxies = [f"{p['nazwisko']} — prokura {p['rodzaj'].lower()}" for p in o["prokurenci"]]
    listed = (people + proxies)[:5]
    more = len(people) + len(proxies) - len(listed)
    rule = o["sposobReprezentacji"].split("\n")[-1]
    return {
        "id": "krs",
        "question": f"Kto reprezentuje spółkę o numerze KRS {krs}?",
        "skill": "krs",
        "source": "Ministerstwo Sprawiedliwości",
        "sourceShort": "KRS",
        "runs": [run],
        "card": {
            "title": o["nazwa"],
            "badge": f"KRS {o['krs']}",
            "badgeOk": True,
            "rows": [
                ["Forma prawna", o["formaPrawna"].capitalize()],
                ["Zarząd", f"{len(people)} os. · prokurenci: {len(proxies)}"],
                ["Reprezentacja", short(rule.capitalize(), 240)],
            ],
            "list": listed + ([f"+ {more} kolejne osoby"] if more > 0 else []),
        },
        "footer": "Źródło: api-krs.ms.gov.pl · dane osobowe zanonimizowane przez API KRS",
    }


def scene_nbp() -> Dict[str, Any]:
    rate_run = run_skill("nbp", "rate", "EUR")
    conv_run = run_skill("nbp", "convert", "25000", "EUR", "PLN")
    r, c = rate_run["output"], conv_run["output"]
    if abs(r["mid"] - c["rateFromPln"]) > 1e-9:
        raise CaptureError("NBP rate changed between calls — please re-run the capture.")
    return {
        "id": "nbp",
        "question": "Jaki jest dzisiaj kurs EUR i ile to jest 25 000 EUR w PLN?",
        "skill": "nbp",
        "source": "Narodowy Bank Polski",
        "sourceShort": "NBP",
        "runs": [rate_run, conv_run],
        "card": {
            "title": f"1 EUR = {r['mid']:.4f} PLN".replace(".", ","),
            "badge": f"tabela {r['tableNumber']}",
            "badgeOk": True,
            "big": f"25 000 EUR = {pln(c['convertedAmount'])}",
            "rows": [
                ["Kurs średni NBP", f"{r['mid']:.4f}".replace(".", ",") + " PLN"],
                ["Tabela", f"{r['tableNumber']} z {r['effectiveDate']}"],
            ],
        },
        "footer": "Źródło: api.nbp.pl · kurs średni (tabela A)",
    }


def scene_imgw() -> Dict[str, Any]:
    run = run_skill("imgw", "weather", "zakopane")
    o = run["output"]
    local = warsaw_time(o["measurementTime"])
    pressure = o["formatted"]["pressure"] if o["pressureHpa"] is None else f"{o['pressureHpa']} hPa"
    return {
        "id": "imgw",
        "question": "Jaka jest teraz pogoda w Zakopanem?",
        "skill": "imgw",
        "source": "IMGW-PIB",
        "sourceShort": "IMGW-PIB",
        "runs": [run],
        "card": {
            "title": f"Stacja synoptyczna {o['stationName']}",
            "badge": f"pomiar {local} (czas PL)" if local else o["measurementTime"],
            "badgeOk": True,
            "big": o["formatted"]["temperature"],
            "rows": [
                ["Ciśnienie", pressure],
                ["Wiatr", o["formatted"]["wind"]],
                ["Wilgotność", o["formatted"]["humidity"]],
                ["Opad", o["formatted"]["rainfall"]],
                ["Czas pomiaru", o["measurementTime"]],
            ],
        },
        "footer": "Źródło: Instytut Meteorologii i Gospodarki Wodnej – PIB (danepubliczne.imgw.pl)",
    }


def scene_nfz() -> Dict[str, Any]:
    ben_run = run_skill("nfz", "benefits", "rezonans")
    benefit = ben_run["output"]["benefits"][0]
    near_run = run_skill("nfz", "near", "Gdańsk", "--benefit", benefit, "--radius-km", "50", "--limit", "5")
    o = near_run["output"]
    if not o["results"]:
        raise CaptureError("NFZ returned no clinics within 50 km of Gdańsk.")
    table: List[List[str]] = []
    any_approx = False
    as_of = None
    for r in o["results"]:
        approx = bool((r.get("coordinates") or {}).get("isApproximate"))
        any_approx = any_approx or approx
        dist = r.get("distanceKm")
        if dist is None:
            dist_txt = "—"
        elif approx:
            dist_txt = f"≈ {dist:.0f} km*"
        else:
            dist_txt = f"{dist:.1f} km".replace(".", ",")
        as_of = as_of or r["waitingTime"].get("dateSituationAsAt")
        table.append([
            short(r["provider"].replace('"', ""), 44),
            r["locality"].title(),
            r["waitingTime"].get("pcus") or "—",
            dist_txt,
        ])
    notes = ["PCUŚ = prognozowany czas oczekiwania (statystyka NFZ), nie termin wizyty."]
    if any_approx:
        notes.append("* położenie przybliżone do centrum miejscowości — odległość orientacyjna.")
    return {
        "id": "nfz",
        "question": "Gdzie w promieniu 50 km od Gdańska mogę zrobić rezonans na NFZ?",
        "skill": "nfz",
        "source": "Narodowy Fundusz Zdrowia",
        "sourceShort": "NFZ API",
        "runs": [ben_run, near_run],
        "steps": [
            f"świadczenie: „rezonans” → {benefit}",
            f"placówki w promieniu {o['query']['radiusKm']:.0f} km · przypadek {o['query']['case']} · sortowanie wg czasu",
        ],
        "card": {
            "title": f"{benefit} · okolice Gdańska",
            "badge": f"stan kolejek na {as_of}" if as_of else "NFZ",
            "badgeOk": True,
            "table": {"head": ["PLACÓWKA", "MIASTO", "PROGNOZOWANY CZAS OCZEKIWANIA", "ODLEGŁOŚĆ"], "rows": table},
            "notes": notes,
        },
        "footer": "Źródło: apinfz.nfz.gov.pl (Terminy leczenia NFZ)",
    }


def scene_sejm() -> Dict[str, Any]:
    list_run = run_skill("sejm", "votings", "--limit", "0")
    lst = list_run["output"]
    # Neutral, deterministic choice: the most recent substantive vote (skip quorum checks).
    candidates = [v for v in lst["votings"] if (v.get("yes") or 0) + (v.get("no") or 0) + (v.get("abstain") or 0) > 0]
    if not candidates:
        raise CaptureError("No substantive votings found on the latest sitting.")
    chosen = candidates[-1]
    vote_run = run_skill("sejm", "voting", str(lst["sitting"]), str(chosen["votingNumber"]))
    v = vote_run["output"]
    res = v["results"]
    when = v["date"].replace("T", " ")[:16]
    return {
        "id": "sejm",
        "question": "Jak głosowano w ostatnim głosowaniu Sejmu?",
        "skill": "sejm",
        "source": "Kancelaria Sejmu RP",
        "sourceShort": "Sejm RP",
        "runs": [list_run, vote_run],
        "card": {
            "title": f"Posiedzenie {v['sitting']} · głosowanie nr {v['votingNumber']}",
            "badge": when,
            "badgeOk": True,
            "rows": [
                ["Sprawa", short(v.get("title"), 170)],
                ["Przedmiot", short(v.get("topic"), 80)],
            ],
            "votes": [
                ["za", res["yes"]],
                ["przeciw", res["no"]],
                ["wstrzymało się", res["abstain"]],
                ["nie głosowało", res["notParticipating"]],
            ],
        },
        "footer": f"Źródło: api.sejm.gov.pl · kadencja {v['term']} · dane bez komentarza",
    }


def scene_inpost() -> Dict[str, Any]:
    tracking = "".join(ch for ch in os.environ.get("DEMO_INPOST_TRACKING", "") if ch.isdigit())
    if tracking:
        run = run_skill("inpost", "track", tracking)
        o = run["output"]
        last = o["events"][0] if o["events"] else {}
        masked = mask_tracking(tracking)
        run["command"] = [a if a != tracking else masked.replace(" ", "") for a in run["command"]]
        run["output"] = {k: o[k] for k in ("status", "statusTitle", "updatedAt", "service")}
        return {
            "id": "inpost",
            "question": "Gdzie jest moja paczka?",
            "skill": "inpost",
            "source": "InPost ShipX",
            "sourceShort": "InPost API",
            "runs": [run],
            "card": {
                "title": f"Przesyłka {masked}",
                "badge": o["statusTitle"],
                "badgeOk": True,
                "rows": [
                    ["Status", o["statusTitle"]],
                    ["Ostatnie zdarzenie", (last.get("datetime") or o["updatedAt"] or "—")[:16].replace("T", " ")],
                    ["Zdarzeń w historii", str(len(o["events"]))],
                ],
            },
            "footer": "Źródło: api-shipx-pl.easypack24.net · numer przesyłki zamaskowany",
        }
    # No tracking number of our own to show publicly: live Paczkomat lookup instead.
    lat, lon = "54.3556", "18.6440"  # Gdańsk Główny railway station
    run = run_skill("inpost", "near", lat, lon, "--limit", "3")
    o = run["output"]
    rows = []
    for p in o["points"][:3]:
        rows.append([p["name"], f"{p['address']['line1']} · {p.get('distanceFormatted') or '—'} · {p.get('openingHours') or ''}".strip(" ·")])
    return {
        "id": "inpost",
        "question": "Gdzie odbiorę paczkę? Najbliższy Paczkomat przy dworcu Gdańsk Główny",
        "skill": "inpost",
        "source": "InPost ShipX",
        "sourceShort": "InPost API",
        "runs": [run],
        "card": {"title": "Najbliższe Paczkomaty", "badge": f"{o['count']} wyniki", "badgeOk": True, "rows": rows},
        "footer": "Źródło: api-shipx-pl.easypack24.net",
    }


def scene_cert_pl() -> Dict[str, Any]:
    domain = os.environ.get("DEMO_CERT_DOMAIN", "cert.pl")
    run = run_skill("cert-pl", "check", domain)
    o = run["output"]
    return {
        "id": "cert-pl", "question": f"Sprawdź domenę {o['domain']} na liście CERT Polska",
        "skill": "cert-pl", "source": "CERT Polska", "sourceShort": "Lista ostrzeżeń",
        "runs": [run],
        "card": {"title": o["domain"], "badge": "Na liście" if o["listed"] else "Brak wpisu",
                 "badgeOk": False,
                 "rows": [["Wpis na liście", o["matched_domain"] or "Nie znaleziono"],
                          ["Interpretacja", o["message"]], ["Lista pobrana", o["list_fetched_at"]]]},
        "footer": "Źródło: CERT Polska · brak wpisu nie potwierdza bezpieczeństwa · badany adres nie jest otwierany",
    }


def scene_smog() -> Dict[str, Any]:
    run = run_skill("smog", "near", "50.06", "19.94")
    o = run["output"]
    rows = [["Indeks GIOŚ", o["index"]["category"] or "Brak indeksu"],
            ["Dane indeksu", o["index"]["measured_at"] or "Brak czasu"]]
    for m in o["measurements"]:
        if m["pollutant"] in ("PM10", "PM2.5", "NO2"):
            value = "Brak pomiaru" if m["value"] is None else f"{m['value']} {m['unit']}"
            rows.append([m["pollutant"], value + " · " + (m["measured_at"] or "—")])
    return {
        "id": "smog", "question": "Jaka jest jakość powietrza w pobliżu centrum Krakowa?",
        "skill": "smog", "source": "GIOŚ", "sourceShort": "Jakość powietrza",
        "runs": [run], "card": {"title": o["station"]["name"], "badge": f"{o['distance_km']} km",
                                 "badgeOk": True, "rows": rows},
        "footer": "Źródło: GIOŚ · pomiary wstępne · czas Europe/Warsaw · odległość w linii prostej",
    }


def scene_przetargi() -> Dict[str, Any]:
    end = datetime.datetime.now(datetime.timezone.utc).date()
    start = end - datetime.timedelta(days=29)
    run = run_skill("przetargi", "search", "--cpv", "72413000-8",
                    "--from", start.isoformat(), "--to", end.isoformat(), "--limit", "3")
    o = run["output"]
    rows = []
    for item in o["notices"]:
        rows.append([item["id"], short(item["title"], 95)])
        rows.append(["Termin z ogłoszenia", item["offers_due_at"] or "Brak w odpowiedzi"])
    return {
        "id": "przetargi", "question": "Znajdź ogłoszenia BZP z kodem CPV projektowania stron WWW z ostatnich 30 dni",
        "skill": "przetargi", "source": "Urząd Zamówień Publicznych", "sourceShort": "BZP / e-Zamówienia",
        "runs": [run], "card": {"title": "CPV 72413000-8 — projektowanie stron WWW", "badge": f"{o['count']} wyniki",
                                 "badgeOk": True, "rows": rows},
        "footer": "Źródło: BZP · terminy mogą ulec zmianie · wyniki nie potwierdzają aktualnego przyjmowania ofert",
    }


SCENES = [scene_biala_lista, scene_krs, scene_nbp, scene_imgw, scene_nfz,
          scene_sejm, scene_inpost, scene_cert_pl, scene_smog, scene_przetargi]


# Additional scenes use the same real-command provenance as the original capture.
EXTRA_COMMANDS = {
    'adresy': ('Współrzędne adresu Marki, Andersa 1', ['search', 'Marki, Andersa 1']),
    'apteki': ('Znajdź apteki przy Grunwaldzkiej w Gdańsku', ['search', '--city', 'Gdańsk', '--street', 'Grunwaldzka', '--limit', '2']),
    'ceny-deweloperow': ('Pokaż archiwalną historię ceny lokalu 11.A — Spokojny Wilanów', ['history', '71532', 'Spokojny Wilanów::11.A', '--with-resource', '71531']),
    'dzialki': ('Znajdź granice działki 022602_1.0003.59', ['id', '022602_1.0003.59']),
    'energia': ('Znajdź najtańsze dwie godziny RCE z 12 listopada 2026', ['cheapest', '2026-11-12', '--minutes', '120']),
    'filmweb': ('Jaką ocenę ma Matrix na Filmwebie?', ['film', '628']),
    'leki': ('Jaki lek i ulotka odpowiadają kodowi 5909990296026?', ['barcode', '5909990296026']),
    'moja-gmina': ('Sprawdź definicję i lata wskaźnika ludności GUS dla gmin', ['indicator', 'ludnosc']),
    'nieruchomosci': ('Pokaż zapisane transakcje mieszkań w centrum Warszawy', ['search', '--lat', '52.2297', '--lon', '21.0122', '--function', 'mieszkalna', '--limit', '2', '--scan-limit', '20']),
    'odjazdy': ('Kiedy odjeżdżają autobusy i tramwaje z Bramy Portowej w Szczecinie?', ['departures', 'szczecin', '10822', '--limit', '3']),
    'ostrzezenia-gis': ('Pokaż najnowsze ostrzeżenia produktowe GIS', ['list', '--limit', '2']),
    'otwarte-dane': ('Znajdź zbiory otwartych danych o transporcie', ['search', 'transport', '--limit', '2']),
    'prawo': ('Sprawdź status i najnowszy tekst jednolity Kodeksu pracy', ['act', 'kp', '--limit', '2']),
    'produkty': ('Sprawdź etykietę produktu po kodzie 5901432003117', ['barcode', '5901432003117']),
    'solid-jobs': ('Pokaż oferty Python i widełki z SOLID.Jobs', ['search', 'Python', '--limit', '2']),
    'terminy': ('Jaki wymiar czasu pracy przypada na grudzień 2026?', ['month', '2026-12']),
}


def extra_scene(name, run):
    o = run['output']
    r = o.get('result', o)
    rows, notes = [], []
    title, source = name, o.get('source', name)
    if name == 'adresy':
        a = r['results'][0]; title = a['city'] + ', ' + a['street'] + ' ' + a['number']; source = 'GUGiK — UUG'
        rows = [['Szerokość', str(a['latitude'])], ['Długość', str(a['longitude'])], ['Układ', r['crs']]]
        notes = ['Punkt adresowy; nie granice ani własność działki.']
    elif name == 'apteki':
        title = 'Gdańsk · Grunwaldzka'; source = 'Rejestr Aptek / CeZ / WIF'
        for a in r['items']:
            rows.append([a['name'] or a['id'], a['address']['nazwa_ulicy'] + ' ' + a['address']['numer_budynku']])
            rows.append(['Telefon', a['contact']['telefon'] or 'Brak w rejestrze'])
        notes = ['Stan rejestru: ' + str(o['snapshot']['source_as_of']) + '. Nie potwierdza otwarcia ani stanu leków.']
    elif name == 'ceny-deweloperow':
        title = 'Spokojny Wilanów · 11.A'; source = 'dane.gov.pl / wydawca cennika'
        for p in r['price_points'][:3]:
            rows.append([str(p.get('first_observed', p.get('date', ''))), str(p.get('price_total_pln')) + ' PLN'])
        rows.extend([['Zakres obserwacji', r['first_observed'] + ' → ' + r['last_observed']], ['Zmiana w próbie', r['first_to_last_change']['percent'] + '%']])
        notes = ['Archiwalne ceny ofertowe wydawcy. Nie ceny transakcyjne ani dowód aktualnej dostępności.']
    elif name == 'dzialki':
        a = o['records'][0]; title = a['id']; source = 'GUGiK — ULDK'
        rows = [['Gmina', a['commune']], ['Powiat', a['county']], ['Obręb', a['district']], ['Geometria', a['geometry']['geojson']['type'] + ' · ' + a['geometry']['crs']]]
        notes = ['Źródło: Główny Urząd Geodezji i Kartografii. Bez danych własności.']
    elif name == 'energia':
        w = o['window']; title = o['date'] + ' · najtańsze 120 minut'; source = 'PSE — RCE'
        rows = [['Od', w['start_local']], ['Do', w['end_local']], ['Średnia RCE', f"{w['mean_pln_kwh']:.4f} PLN/kWh"]]
        notes = ['Cena rynkowa; nie pełny koszt rachunku. Europe/Warsaw.']
    elif name == 'filmweb':
        title = o['title'] + ' (' + str(o['year']) + ')'; source = 'Filmweb — nieoficjalne API'
        rows = [['Ocena', f"{o['rating']:.1f}/10"], ['Liczba ocen', str(o['votesCount'])], ['Gatunki', ', '.join(o['genres'])]]
    elif name == 'leki':
        a = r['items'][0]; p = a['product']; title = p['name'] + ' · ' + p['strength']; source = 'RPL / URPL / CeZ'
        rows = [['Postać', p['form']], ['Substancja', p['common_name']], ['Opakowanie', ' · '.join((u['pojemnosc'] or '') + ' ' + (u['jednostkaPojemnosci'] or '') for u in a['package']['units'])], ['Ulotka', p['documents']['ulotka']]]
        notes = ['Stan RPL: ' + o['snapshot']['source_as_of'] + '. Link do dokumentu; bez doboru leczenia.']
    elif name == 'moja-gmina':
        title = 'Ludność ogółem · GUS BDL'; source = 'GUS, Bank Danych Lokalnych'
        rows = [['Wskaźnik', str(r['id'])], ['Jednostka', r['measureUnitName']], ['Poziom', str(r['level']) + ' — gminy'], ['Dostępne lata', str(min(r['years'])) + '–' + str(max(r['years']))]]
        notes = ['Źródło: GUS BDL · CC BY 4.0. Definicja serii, nie bieżący pomiar.']
    elif name == 'nieruchomosci':
        title = 'RCN · próbka wokół centrum Warszawy'; source = 'GUGiK — RCN'
        for a in o['records'][:2]:
            rows.append([short(a['address'], 65), str(a['object_price_pln']) + ' PLN · obiekt'])
            rows.append(['Data aktu / powierzchnia', a['deed_date'] + ' · ' + str(a['area_m2']) + ' m²'])
        notes = [f"Przejrzano {o['scanned_records']} rekordów. Cena obiektu; nie wycena ani pełny rynek."]
    elif name == 'odjazdy':
        title = 'Szczecin · ' + o['stop']['name']; source = 'ZDiTM Szczecin'
        from zoneinfo import ZoneInfo
        for a in o['departures'][:3]:
            t = a['estimated_at'] or a['scheduled_at']
            local = datetime.datetime.fromisoformat(t.replace('Z', '+00:00')).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')
            rows.append([a['line'] + ' → ' + short(a['destination'], 45), local + ' · ' + a['status']])
        notes = ['Zapis tablicy z chwili nagrania; prognoza nie gwarantuje przyjazdu. CC0 1.0.']
    elif name == 'ostrzezenia-gis':
        title = 'Najnowsze komunikaty GIS'; source = 'Główny Inspektorat Sanitarny'
        rows = [[n['published_at'], short(n['title'], 145)] for n in r['notices'][:2]]
        notes = ['Źródło: GIS / Gov.pl · CC BY-SA 4.0 · HTML → tekst. Ograniczona lista; brak wpisu nie dowodzi bezpieczeństwa.']
    elif name == 'otwarte-dane':
        title = 'Zbiory danych · transport'; source = 'dane.gov.pl'
        rows = [[a['id'], short(a['attributes']['title'].replace('<mark>', '').replace('</mark>', ''), 125)] for a in r['data'][:2]]
        notes = ['Metadane katalogu; aktualność i warunki użycia sprawdzaj dla każdego źródła.']
    elif name == 'prawo':
        title = 'Kodeks pracy · tekst jednolity'; source = 'Kancelaria Sejmu — ELI'
        a = o['latestConsolidatedText']
        rows = [['Status aktu', o['status']], ['Tekst jednolity', a['displayAddress']], ['Publikacja', a['promulgation']], ['Dokument', a['links']['pdf']]]
        notes = [f"Późniejsze zmiany: {len(o['amendmentsAfterLatestConsolidatedText'])}. Tekst źródłowy, nie porada prawna."]
    elif name == 'produkty':
        title = r['name']['text']; source = 'Open Food Facts contributors'
        rows = [['Marka', r['brands']], ['Opakowanie', r['quantity']], ['Skład', r['ingredients']['text'] or 'Brak danych'], ['Alergeny', r['allergens']['status']]]
        notes = ['Dane społecznościowe · ODbL / DbCL. Brak wpisu o alergenie nie oznacza jego braku.']
    elif name == 'solid-jobs':
        title = 'Python · oferty SOLID.Jobs'; source = 'SOLID.Jobs'
        for a in r['jobs'][:2]:
            pay = a.get('salary') or {}
            rows.append([short(a['title'], 60), a['company']])
            rows.append(['Widełki z ogłoszenia', ' – '.join(str(pay.get(k)) for k in ('from', 'to')) + ' ' + str(pay.get('currency')) + '/' + str(pay.get('period')) + ' · ' + str(pay.get('employmentType'))])
        notes = ['Jedna tablica ofert. Nie łącz wynagrodzeń B2B i UoP.']
    elif name == 'terminy':
        title = 'Grudzień 2026 · pełny etat'; source = 'Polskie przepisy · obliczenie offline'
        rows = [['Wymiar czasu pracy', str(o['workingTimeNormHours']) + ' h'], ['Dni robocze kalendarza', str(o['workingDays'])], ['Obliczenie', o['calculation']]]
        notes = ['art. 130 KP · 1-miesięczny okres · reguły sprawdzone: ' + o['rulesVerified']]
    return dict(id=name, skill=name, question=EXTRA_COMMANDS[name][0], source=source, sourceShort=source,
                runs=[run], card=dict(title=title, rows=rows, notes=notes),
                footer='Źródło: ' + source)


def make_extra(name):
    def capture():
        return extra_scene(name, run_skill(name, *EXTRA_COMMANDS[name][1]))
    capture.__name__ = 'scene_' + name.replace('-', '_')
    return capture


SCENES.extend(make_extra(name) for name in EXTRA_COMMANDS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture live skill outputs for the demo video.")
    parser.add_argument("--out", default=str(Path(__file__).with_name("demo_data.json")))
    parser.add_argument("--only", nargs="+", metavar="SCENE",
                        help="re-capture only these scenes and merge them into an existing --out file")
    args = parser.parse_args()
    names = {fn.__name__.replace("scene_", "").replace("_", "-") for fn in SCENES}
    if args.only and not set(args.only) <= names:
        parser.error("Unknown scene in --only; available: " + ", ".join(sorted(names)))

    previous: Dict[str, Any] = {}
    if args.only:
        try:
            previous = {s["id"]: s for s in json.loads(Path(args.out).read_text(encoding="utf-8"))["scenes"]}
        except (OSError, ValueError, KeyError):
            previous = {}

    scenes = []
    failed = []
    for fn in SCENES:
        name = fn.__name__.replace("scene_", "").replace("_", "-")
        if args.only and name not in args.only and name in previous:
            scenes.append(previous[name])
            continue
        print(f"• capturing {name} …", file=sys.stderr)
        try:
            scenes.append(fn())
        except (CaptureError, json.JSONDecodeError, KeyError, IndexError, subprocess.TimeoutExpired) as exc:
            print(f"✗ {name}: {exc}", file=sys.stderr)
            failed.append(name)

    scenes.sort(key=lambda scene: scene["skill"])
    destination = args.out if not failed else str(Path(args.out).with_suffix('.incomplete.json'))
    write(destination, scenes, complete=not failed)
    if failed:
        print(f"Capture incomplete. Retry only the missing scenes with: --only {' '.join(failed)}", file=sys.stderr)
        print("The demo is rendered only from real skill output — no fallback data.", file=sys.stderr)
        return 69
    return 0


def write(out: str, scenes: List[Dict[str, Any]], complete: bool) -> None:
    registry = json.loads((ROOT / "registry/registry.json").read_text())
    expected = {skill["name"] for skill in registry["skills"]}
    covered = {scene["skill"] for scene in scenes}
    if complete and (covered != expected or len(scenes) != len(expected)):
        raise CaptureError("Demo must contain exactly one scene for every registered skill.")
    data = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "complete": complete and len(scenes) == len(SCENES),
        "note": "Real skill output; each run retains its own capturedAt timestamp. Regenerate with python3 docs/demo/capture.py.",
        "scenes": scenes,
    }
    destination = Path(out)
    temporary = destination.with_suffix(destination.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    print(f"✓ wrote {Path(out).resolve()} ({len(scenes)}/{len(SCENES)} scenes)", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
