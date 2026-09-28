// Render scene.html frame-by-frame with Playwright/Chromium and encode H.264 via ffmpeg.
//
//   node docs/demo/render.mjs <demo_data.json> <out.mp4> [--fps 30] [--workers 4] [--ffmpeg path]
//
// Every frame is produced by calling window.renderAt(t) with t = frame / fps, so the
// output is deterministic and independent of machine speed. Frames are split into
// contiguous chunks rendered in parallel pages; each chunk is piped as PNG into its own
// ffmpeg process and the chunks are concatenated losslessly at the end.

import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : def; };
const [dataPath, outPath] = args.filter((a, i) => !a.startsWith("--") && !(args[i - 1] || "").startsWith("--"));
if (!dataPath || !outPath) { console.error("usage: render.mjs <demo_data.json> <out.mp4> [--fps 30] [--workers N] [--ffmpeg path]"); process.exit(64); }
const FPS = Number(opt("--fps", 30));
const WORKERS = Number(opt("--workers", Math.max(1, Math.min(6, os.cpus().length))));
const FFMPEG = opt("--ffmpeg", "ffmpeg");

// Resolve Playwright from a local install or the global npm root (no project dependency).
function loadPlaywright() {
  const req = createRequire(import.meta.url);
  try { return req("playwright"); } catch { /* fall through */ }
  const globalRoot = execSync("npm root -g", { encoding: "utf8" }).trim();
  return req(path.join(globalRoot, "playwright"));
}
const { chromium } = loadPlaywright();

const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
if (!data.complete) { console.error(`${dataPath} is incomplete — finish the capture first (capture.py --only …).`); process.exit(65); }
const sceneUrl = pathToFileURL(path.join(here, "scene.html")).href;
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "demo-render-"));

function encoder(file) {
  const p = spawn(FFMPEG, [
    "-hide_banner", "-loglevel", "error", "-y",
    "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-",
    "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", "24",
    "-pix_fmt", "yuv420p", "-r", String(FPS), "-g", String(FPS * 4), file,
  ], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => p.on("close", (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))));
  return { stdin: p.stdin, done };
}

const write = (stream, buf) => new Promise((res) => (stream.write(buf) ? res() : stream.once("drain", res)));

const browser = await chromium.launch();
const probe = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await probe.addInitScript((d) => { window.DEMO_DATA = d; }, data);
await probe.goto(sceneUrl);
const duration = await probe.evaluate(() => window.DEMO_DURATION);
await probe.close();

const total = Math.round(duration * FPS);
const per = Math.ceil(total / WORKERS);
let rendered = 0;
const started = Date.now();

async function renderChunk(idx) {
  const from = idx * per, to = Math.min(total, from + per);
  const file = path.join(tmpDir, `part${String(idx).padStart(2, "0")}.mp4`);
  if (from >= to) return null;
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.addInitScript((d) => { window.DEMO_DATA = d; }, data);
  await page.goto(sceneUrl);
  await page.evaluate(() => document.fonts.ready);
  const enc = encoder(file);
  for (let f = from; f < to; f++) {
    await page.evaluate((t) => window.renderAt(t), f / FPS);
    await write(enc.stdin, await page.screenshot({ type: "png" }));
    rendered++;
    if (rendered % 150 === 0) {
      const s = (Date.now() - started) / 1000;
      process.stderr.write(`  frames ${rendered}/${total}  (${(rendered / s).toFixed(1)} fps)\n`);
    }
  }
  enc.stdin.end();
  await enc.done;
  await page.close();
  return file;
}

const parts = (await Promise.all(Array.from({ length: WORKERS }, (_, i) => renderChunk(i)))).filter(Boolean);
await browser.close();

const list = path.join(tmpDir, "list.txt");
fs.writeFileSync(list, parts.map((p) => `file '${p}'`).join("\n"));
await new Promise((res, rej) => {
  const p = spawn(FFMPEG, ["-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", list,
    "-c", "copy", "-movflags", "+faststart", outPath], { stdio: "inherit" });
  p.on("close", (c) => (c === 0 ? res() : rej(new Error(`ffmpeg concat exited ${c}`))));
});
fs.rmSync(tmpDir, { recursive: true, force: true });
process.stderr.write(`  ${total} frames rendered in ${((Date.now() - started) / 1000).toFixed(0)} s\n`);
