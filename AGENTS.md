# AI Agent Discovery & Execution Protocol (AGENTS.md)

Welcome, AI Agent (Claude Code, Cursor, Windsurf, Antigravity, Codex, etc.).
This document is your machine-readable entry point for discovering, installing, and executing Polish AI skills from `ai-polish-skills` (polskieskille.pl).

---

## 1. Quick Capability Routing Map

Match user prompt intent to the appropriate skill:

| User Intent / Capability | Skill Name | Primary Script | Sample Trigger |
|---|---|---|---|
| **Verify company by NIP / REGON, VAT whitelist, bank account split payment** | `biala-lista` | `scripts/biala_lista.py` | `"sprawdź NIP 5260250274"`, `"status VAT firmy"` |
| **Check court register (KRS), board members, proxies, contract signing rules** | `krs` | `scripts/krs.py` | `"kto może podpisać umowę w KRS 0000006865"` |
| **NBP exchange rates (EUR/USD...), Art. 31a VAT tax invoice calculation, gold** | `nbp` | `scripts/nbp.py` | `"kurs EUR z NBP do faktury z 2026-09-25"` |
| **Working days, public holidays, working-time norm, ZUS/PIT/CIT/VAT deadlines, payment terms (offline)** | `terminy` | `scripts/terminy.py` | `"ile dni roboczych w październiku"`, `"do kiedy ZUS"`, `"termin VAT"` |
| **Track InPost parcel, find Paczkomat lockers by code, address, or GPS** | `inpost` | `scripts/inpost.py` | `"gdzie jest moja paczka InPost"`, `"najbliższy paczkomat"` |
| **Search Polish film/series ratings, reviews, cast, premiere, VOD streaming** | `filmweb` | `scripts/filmweb.py` | `"jaka ocena filmu na Filmwebie"`, `"gdzie obejrzę"` |
| **IMGW weather (temperature, pressure, wind, rain), official alerts, river levels** | `imgw` | `scripts/imgw.py` | `"jaka jest temperatura w Warszawie"`, `"ostrzeżenia IMGW pomorskie"`, `"stan Wisły"` |
| **Sejm RP parliamentary data: MPs, roll-call votings, legislative bills, prints** | `sejm` | `scripts/sejm.py` | `"jak głosowano w Sejmie"`, `"jak głosował poseł"`, `"proces ustawy"` |
| **NFZ healthcare queues, estimated waiting times (PCUŚ), clinics, benefit search** | `nfz` | `scripts/nfz.py` | `"czas oczekiwania NFZ"`, `"gdzie na rezonans"`, `"kolejki NFZ"` |
| **Polish law: article wording, act status, consolidated texts (ISAP / Dziennik Ustaw)** | `prawo` | `scripts/prawo.py` | `"co mówi art. 30 Kodeksu pracy"`, `"czy ustawa obowiązuje"` |

---

## 2. Autonomous Discovery Protocol

### Step A: Read the Registry
If you are inside the cloned repository:
- Inspect `registry/registry.json` directly.
- Or run:
  ```bash
  python3 scripts/cli.py search "<user intent or keyword>" --json
  ```

If you are an external agent without repo checkout:
- Fetch registry via HTTP GET:
  ```
  https://raw.githubusercontent.com/b44x/ai-polish-skills/main/registry/registry.json
  ```
- Or minified:
  ```
  https://raw.githubusercontent.com/b44x/ai-polish-skills/main/registry/registry.min.json
  ```

### Step B: Install the Skill
Execute the one-line installer or copy the skill directory:
```bash
# In local repo:
./install.sh <skill_name>

# From remote (external agent):
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s <skill_name>
```
The installer automatically creates the directory in `.agents/skills/<skill_name>` (or `.claude/skills/<skill_name>`) and sets executable permissions on scripts.

### Step C: Read Tool Instructions
Load the skill's instruction file:
- Local path: `.agents/skills/<skill_name>/SKILL.md` (or `.claude/skills/...`)
- Remote URL: `https://raw.githubusercontent.com/b44x/ai-polish-skills/main/skills/<skill_name>/SKILL.md`

### Step D: Execute the CLI Tool
All scripts run with Python 3.8+ standard library (no pip packages):
```bash
python3 .agents/skills/<skill_name>/scripts/<skill_name>.py <command> [args]
```
Always read the structured JSON from `stdout`.

---

## 3. Strict Execution Contract

Every tool in this registry guarantees:
1. **Help flag:** `python3 <script> --help` exits with code `0` and prints human-readable usage.
2. **Stdout output:** Successful commands return **strictly valid JSON** on `stdout`. No debug logs, greetings, or warnings on `stdout`.
3. **Stderr on error:** Failures write structured error info (`{"error": "...", "type": "..."}`) or messages to `stderr`.
4. **Standard exit codes:**
   - `0` — Success
   - `2` — Not found
   - `64` — Validation or usage error
   - `69` — Upstream API error / network issue
