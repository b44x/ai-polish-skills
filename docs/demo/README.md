# Polskie Skille — demo video

| File | What it is |
|---|---|
| [`demo.mp4`](demo.mp4) | Full demo: H.264, 1920×1080, 30 fps, ~95 s |
| [`demo.gif`](demo.gif) | README preview: 960×540, 10 fps |
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

If a public API is temporarily unavailable, the capture retries and then stops without
rendering. Re-capture only the missing scenes with:

```bash
python3 docs/demo/capture.py --only nfz sejm
```

## Storyboard (≈95 s)

| Time | Scene | Skill → source |
|---|---|---|
| 0–6 s | Intro | — |
| 6–18 s | "Sprawdź firmę po NIP 5261040828" | `biala-lista` → Ministerstwo Finansów |
| 18–30 s | "Kto reprezentuje spółkę o numerze KRS 0000006865?" | `krs` → Ministerstwo Sprawiedliwości |
| 30–40 s | EUR rate and 25 000 EUR in PLN | `nbp` → NBP |
| 40–52 s | Weather in Zakopane | `imgw` → IMGW-PIB |
| 52–68 s | MRI within 50 km of Gdańsk | `nfz` → NFZ |
| 68–80 s | Latest Sejm vote | `sejm` → Kancelaria Sejmu RP |
| 80–87 s | InPost | `inpost` → InPost ShipX |
| 87–95 s | Outro | — |

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
