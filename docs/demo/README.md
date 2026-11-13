# Polskie Skille — complete catalogue demo

One canonical demo covers **all 26 registered skills**, once each, in alphabetical order. The current render is approximately **3 min 15 s**. Every scene uses actual successful script output captured on 2026-11-13; this is a recording, not a claim of continuously current results.

| File | Purpose |
|---|---|
| `demo.mp4` | H.264, 1920×1080, 30 fps, approximately 195 seconds |
| `demo.gif` | Full animated README preview, 960×540, 20 fps |
| `demo_data.json` | Exact commands, timings, capture timestamps, raw JSON and derived display cards |
| `capture.py` | Runs the unmodified skills and builds one scene for every registry entry |
| `scene.html` | Deterministic animation with overlapping transitions and content-based reading time |
| `render.mjs` | Playwright/Chromium frame rendering and ffmpeg encoding; rejects missing/duplicate skill coverage |
| `generate_demo.sh` | Live capture and render, or render saved observations |

## Regenerate

```bash
./docs/demo/generate_demo.sh
./docs/demo/generate_demo.sh --reuse-data
python3 docs/demo/capture.py --only apteki leki
```

Requirements: Python 3.9+, Node 18+, Playwright for Node and Chromium, and ffmpeg with libx264. A temporary Playwright installation can be supplied with `NODE_PATH`; use `DEMO_CHROMIUM_EXECUTABLE` for an existing browser and `DEMO_WORKERS` to control parallel rendering. These are media tools, not skill runtime dependencies.

Failed captures write a separate `demo_data.incomplete.json` and preserve the previous canonical capture. Retry the named failures with `--only`; the renderer never substitutes fixtures or fabricated success. Captures make at most two attempts for upstream errors and stop on reported throttling. The full capture can download the RPL XML and RA CSV; do not refresh these in a tight loop.

## Storyboard

Adjacent scenes overlap by 0.32 seconds. Reading holds vary with displayed content; actual runtime is recorded in the command line, while video execution waits are condensed for presentation. Intro: 0–3 seconds; outro follows the final scene.

| Start | End | Skill | Question |
|---|---|---|---|
| 0:03 | 0:10 | `adresy` | Współrzędne adresu Marki, Andersa 1 |
| 0:09 | 0:17 | `apteki` | Znajdź apteki przy Grunwaldzkiej w Gdańsku |
| 0:16 | 0:24 | `biala-lista` | Sprawdź firmę po NIP 5261040828 |
| 0:23 | 0:31 | `ceny-deweloperow` | Pokaż archiwalną historię ceny lokalu 11.A — Spokojny Wilanów |
| 0:30 | 0:37 | `cert-pl` | Sprawdź domenę cert.pl na liście CERT Polska |
| 0:37 | 0:44 | `dzialki` | Znajdź granice działki 022602_1.0003.59 |
| 0:44 | 0:51 | `energia` | Znajdź najtańsze dwie godziny RCE z 12 listopada 2026 |
| 0:51 | 0:57 | `filmweb` | Jaką ocenę ma Matrix na Filmwebie? |
| 0:57 | 1:05 | `imgw` | Jaka jest teraz pogoda w Zakopanem? |
| 1:05 | 1:12 | `inpost` | Gdzie odbiorę paczkę? Najbliższy Paczkomat przy dworcu Gdańsk Główny |
| 1:12 | 1:21 | `krs` | Kto reprezentuje spółkę o numerze KRS 0000006865? |
| 1:20 | 1:28 | `leki` | Jaki lek i ulotka odpowiadają kodowi 5909990296026? |
| 1:27 | 1:35 | `moja-gmina` | Sprawdź definicję i lata wskaźnika ludności GUS dla gmin |
| 1:35 | 1:42 | `nbp` | Jaki jest dzisiaj kurs EUR i ile to jest 25 000 EUR w PLN? |
| 1:42 | 1:51 | `nfz` | Gdzie w promieniu 50 km od Gdańska mogę zrobić rezonans na NFZ? |
| 1:51 | 1:58 | `nieruchomosci` | Pokaż zapisane transakcje mieszkań w centrum Warszawy |
| 1:58 | 2:05 | `odjazdy` | Kiedy odjeżdżają autobusy i tramwaje z Bramy Portowej w Szczecinie? |
| 2:05 | 2:12 | `ostrzezenia-gis` | Pokaż najnowsze ostrzeżenia produktowe GIS |
| 2:11 | 2:18 | `otwarte-dane` | Znajdź zbiory otwartych danych o transporcie |
| 2:18 | 2:26 | `prawo` | Sprawdź status i najnowszy tekst jednolity Kodeksu pracy |
| 2:25 | 2:33 | `produkty` | Sprawdź etykietę produktu po kodzie 5901432003117 |
| 2:32 | 2:41 | `przetargi` | Znajdź ogłoszenia BZP z kodem CPV projektowania stron WWW z ostatnich 30 dni |
| 2:41 | 2:49 | `sejm` | Jak głosowano w ostatnim głosowaniu Sejmu? |
| 2:49 | 2:56 | `smog` | Jaka jest jakość powietrza w pobliżu centrum Krakowa? |
| 2:56 | 3:04 | `solid-jobs` | Pokaż oferty Python i widełki z SOLID.Jobs |
| 3:03 | 3:10 | `terminy` | Jaki wymiar czasu pracy przypada na grudzień 2026? |

## Data interpretation

- Every display value is derived from captured JSON. The registry total and scene coverage are checked before rendering. New registry entries require new real capture adapters.
- `--reuse-data` rerenders observations without refreshing them. Every run retains its capture timestamp; source observation dates remain distinct.
- Developer prices deliberately show an archived 2025-08-11–12 sample, labelled historical and asking-price-only. It does not establish current availability or a complete price history.
- `moja-gmina` demonstrates actual indicator metadata and available years; it does not invent a population comparison.
- `terminy` is an offline calculation with a rule-verification date, not a fresh legal lookup.
- NFZ PCUŚ is a statistical waiting estimate, not an appointment date. Approximate city-centre distances are marked.
- Pharmacy status/hours do not confirm current opening, duty or stock. RPL supplies registry data and document links, not treatment recommendations.
- Open Food Facts is a community source with ODbL/DbCL attribution; missing allergen fields do not establish absence. GIS text is attributed under CC BY-SA 4.0. GUS and transport attribution is retained.
- GIOŚ shows measurement times, CERT absence is not proof of safety, and BZP dates do not confirm a tender is still open.
- Filmweb uses its unofficial interface; the flow strip says “data source”, without labelling every provider an official API.
- No private InPost tracking number is required. Without `DEMO_INPOST_TRACKING`, the capture shows nearby Paczkomaty.
