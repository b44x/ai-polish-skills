#!/usr/bin/env bash
# Regenerate the Polskie Skille demo video from live skill output.
#
#   ./docs/demo/generate_demo.sh              capture live data, render MP4 + GIF
#   ./docs/demo/generate_demo.sh --reuse-data  render from the existing demo_data.json
#
# Requirements (not project dependencies):
#   python3 (3.9+), node (18+), Playwright for Node with Chromium, ffmpeg with libx264.
#   ffmpeg is taken from $FFMPEG, then PATH, then the Python package imageio-ffmpeg.
#
# Optional:
#   DEMO_INPOST_TRACKING=<24 digits>  track your own parcel in the InPost scene (masked on screen)
#   DEMO_WORKERS=<n>                  parallel render pages (default: CPU count, max 6)
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DEMO_DIR/../.." && pwd)"
DATA="$DEMO_DIR/demo_data.json"
MP4="$DEMO_DIR/demo.mp4"
GIF="$DEMO_DIR/demo.gif"
FPS=30
REUSE=0
[[ "${1:-}" == "--reuse-data" ]] && REUSE=1

say()  { printf '\033[1m▸ %s\033[0m\n' "$*"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 1. tools
say "Checking tools"
command -v python3 >/dev/null || fail "python3 not found"
command -v node >/dev/null    || fail "node not found (https://nodejs.org)"
node -e '
  const {createRequire}=require("module"); const r=createRequire(process.cwd()+"/");
  try { r("playwright"); } catch { r(require("child_process").execSync("npm root -g").toString().trim()+"/playwright"); }
' 2>/dev/null || fail "Playwright for Node not found (npm i -g playwright && npx playwright install chromium)"

find_ffmpeg() {
  local c
  for c in "${FFMPEG:-}" "$(command -v ffmpeg || true)" \
           "$(python3 -c 'import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())' 2>/dev/null || true)"; do
    if [[ -n "$c" && -x "$c" ]] && "$c" -hide_banner -encoders 2>/dev/null | grep libx264 >/dev/null; then
      echo "$c"; return 0
    fi
  done
  return 1
}
FFMPEG_BIN="$(find_ffmpeg)" || fail "ffmpeg with libx264 not found (install ffmpeg, or: pip install imageio-ffmpeg)"
echo "  python3: $(python3 --version 2>&1)  node: $(node --version)  ffmpeg: $FFMPEG_BIN"

# ---------------------------------------------------------------- 2. data
if [[ $REUSE -eq 1 ]]; then
  [[ -f "$DATA" ]] || fail "$DATA missing — run without --reuse-data first"
  say "Reusing captured data from $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["generatedAt"])' "$DATA")"
else
  say "Capturing live output of the skills (real API calls)"
  python3 "$DEMO_DIR/capture.py" --out "$DATA" || fail "capture failed — nothing rendered (no fake data fallback)"
fi

# ---------------------------------------------------------------- 3. MP4
say "Rendering 1920×1080 @ ${FPS} fps"
node "$DEMO_DIR/render.mjs" "$DATA" "$MP4" --fps "$FPS" --ffmpeg "$FFMPEG_BIN" ${DEMO_WORKERS:+--workers "$DEMO_WORKERS"}

# ---------------------------------------------------------------- 4. GIF
say "Encoding GIF preview"
"$FFMPEG_BIN" -hide_banner -loglevel error -y -i "$MP4" \
  -vf "fps=10,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  "$GIF"

# ---------------------------------------------------------------- 5. report
size() { du -h "$1" | cut -f1; }
duration="$({ "$FFMPEG_BIN" -hide_banner -i "$MP4" 2>&1 || true; } | sed -n 's/.*Duration: \([0-9:.]*\).*/\1/p')"
say "Done"
echo "  MP4: ${MP4#$ROOT/}  ($(size "$MP4"), $duration)"
echo "  GIF: ${GIF#$ROOT/}  ($(size "$GIF"))"
echo "  Data: ${DATA#$ROOT/}"
