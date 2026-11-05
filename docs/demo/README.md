# Polskie Skille — demo video

One canonical demo includes the seven existing scenes plus CERT Polska, GIOŚ air quality and BZP procurement: 10 examples, approximately 84 seconds. Prompts and Polish post drafts for the new skills are in [new-skills-launch.md](new-skills-launch.md).

The outro distinguishes the total number of available skills from the examples shown. At render time, `render.mjs` reads the catalogue count from `registry/registry.json`, including when using `--reuse-data`; captured API observations remain unchanged.

| File | What it is |
|---|---|
| [`demo.mp4`](demo.mp4) | Full demo: H.264, 1920×1080, 30 fps, ≈84 s |
| [`demo.gif`](demo.gif) | README preview: 960×540, 20 fps |
| [`demo_data.json`](demo_data.json) | Captured output of the skills used in the video (commands, exit codes, timings, raw JSON) |
| [`capture.py`](capture.py) | Runs the real, unmodified skills and writes `demo_data.json` |
| [`scene.html`](scene.html) | Deterministic 1920×1080 animation (terminal session + flow strip) |
| [`render.mjs`](render.mjs) | Renders `scene.html` frame by frame with Playwright/Chromium and encodes via ffmpeg |
| [`generate_demo.sh`](generate_demo.sh) | One command that does everything |

## Regenerate

```bash
./docs/demo/generate_demo.sh               # live capture + MP4 + GIF
./docs/demo/generate_demo.sh --reuse-data  # re-render from the existing demo_data.json
```

Requirements (tools only, nothing is added to the project): Python 3.9+, Node 18+,
Playwright for Node with Chromium (`npm i -g playwright && npx playwright install chromium`)
and ffmpeg with libx264 (`ffmpeg` on `PATH`, `$FFMPEG`, or `pip install imageio-ffmpeg`).

Alternatively, set `DEMO_CHROMIUM_EXECUTABLE` to an existing Chrome/Chromium executable. A temporary Playwright installation can be provided through `NODE_PATH`; no project dependency is required.

If a public API is temporarily unavailable, the capture retries and then stops without
rendering. Re-capture only the missing scenes with:

```bash
python3 docs/demo/capture.py --only nfz sejm
```

## Storyboard (≈84 s)

| Time | Scene | Skill → source |
|---|---|---|
| 0–3 s | Intro | — |
| 3.0–10.4 s | Company VAT status | `biala-lista` → Ministerstwo Finansów |
| 10.1–19.1 s | Company representation | `krs` → Ministerstwo Sprawiedliwości |
| 18.8–26.2 s | EUR rate and invoice conversion | `nbp` → NBP |
| 25.8–33.6 s | Weather in Zakopane | `imgw` → IMGW-PIB |
| 33.3–42.3 s | MRI queues near Gdańsk | `nfz` → NFZ |
| 42.0–50.6 s | Latest captured Sejm vote | `sejm` → Kancelaria Sejmu RP |
| 50.3–57.5 s | Nearby Paczkomaty | `inpost` → InPost ShipX |
| 57.2–63.9 s | Domain check | `cert-pl` → CERT Polska |
| 63.5–71.1 s | Air quality near Kraków city centre | `smog` → GIOŚ |
| 70.8–79.3 s | Website design procurement notices | `przetargi` → BZP |
| 79.3–83.8 s | Outro | — |

Adjacent scenes overlap by 0.32 s. Prompt typing takes 0.85–1.6 s; reading time after the result reveal depends on the number of displayed items (3.6–5.8 s). The header shows the scene number and overall progress. The timeline is derived from the captured content, so duration can change when the data is refreshed.

## Data honesty

- Every value on screen comes from `demo_data.json`, which `capture.py` fills by running
  the scripts in `skills/`. It uses no offline fixtures and no fallback values.
- NIP 5261040828 belongs to Główny Urząd Statystyczny, a state office with no KRS entry.
  The KRS scene therefore uses KRS 0000006865, the example documented in the `krs` skill.
  The KRS API returns personal names already anonymised.
- NFZ shows PCUŚ, the forecast waiting time (a statistical estimate), not the first
  free appointment. Distances computed from approximate (city-centre) coordinates are
  marked with `≈` and `*`.
- The Sejm scene shows the latest vote on the most recent sitting that has any
  yes/no/abstain votes, which skips quorum checks. It shows only the source numbers, with no commentary.
- No InPost tracking number is published in this repository. Set
  `DEMO_INPOST_TRACKING=<24 digits>` to track your own parcel (it is masked on screen).
  Without it, the scene shows a live Paczkomat lookup near Gdańsk Główny.

- The combined capture retains the original timestamps of each run: the first seven scenes were captured in September 2026, and the three new scenes in November 2026. Rendering saved data does not refresh the source observations. Use the default generation command to capture all scenes again, or `capture.py --only cert-pl smog przetargi` to update selected scenes.
- CERT absence is not proof of safety; GIOŚ values carry individual measurement times; BZP notice deadlines do not guarantee a tender still accepts offers.
