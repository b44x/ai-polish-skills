<p align="center">
  🇬🇧 <b>English</b> | 🇵🇱 <a href="README.md">Polski</a>
</p>

# ai-polish-skills

A curated collection of modular, production-ready AI agent skills (`SKILL.md` format) tailored for Polish services, APIs, and workflows.

> 🌐 Official project site: [polskieskille.pl](https://polskieskille.pl)

Every skill provides:
- A standardized `SKILL.md` definition with YAML frontmatter (progressive disclosure).
- Dependency-free Python 3 helper scripts that communicate via clean JSON.
- Output references, schema documentation, and error specifications.

---

## Available Skills

| Skill | Description | Triggers / Keywords |
|---|---|---|
| [`biala-lista`](skills/biala-lista/SKILL.md) | Official Polish Ministry of Finance White List (*Biała Lista Podatników VAT*). Verify active VAT payer status, company registry details, and registered settlement bank accounts before B2B transfers. | NIP, REGON, VAT status, "sprawdź NIP", "biała lista", "rachunek na białej liście", split payment |
| [`nbp`](skills/nbp/SKILL.md) | **Narodowy Bank Polski**. Official currency exchange rates (Tables A & B), gold prices, and automated tax calculator converting foreign currency invoices to PLN according to Polish tax law (Art. 31a VAT). | NBP, exchange rates, "kurs do faktury", convert currency NBP, gold price NBP |
| [`krs`](skills/krs/SKILL.md) | **Krajowy Rejestr Sądowy** (Ministry of Justice). Official court registry extracts for companies (Sp. z o.o., S.A., P.S.A.) and foundations. Board members, proxies, share capital, and signing authority rules. | KRS, company registry, "kto może podpisać umowę", board members, representation rules |
| [`inpost`](skills/inpost/SKILL.md) | **InPost & Paczkomaty across Poland**. Parcel tracking by 24-digit tracking number, locker locator by code (e.g. WAW01M), street, city, or GPS coordinates with distance in meters, 24/7 access, and navigation. | InPost, Paczkomat, "gdzie moja paczka", "status przesyłki InPost", "najbliższy paczkomat" |
| [`filmweb`](skills/filmweb/SKILL.md) | Polish film and TV series database (Filmweb.pl). Search titles, ratings, user reviews, cast, premiere dates, and VOD availability with prices in PLN. | Filmweb, ocena filmu, "gdzie obejrzę", "kto grał w", polskie recenzje, seriale |

---

## ⚡ Quick Automatic Installation

Install all skills or select specific ones with a single terminal command:

```bash
# Install all skills into your current AI project
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash

# Install a specific skill (e.g. inpost)
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s inpost

# Install globally across all Antigravity projects
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s -- --global
```

The installer automatically detects whether you are using **Google Antigravity**, **Claude Code**, or other agent environments and sets up the correct paths.

### Install by prompting your AI Agent

You can also install skills simply by pasting this into your agent's chat (Antigravity, Claude Code, Cursor):

```text
Install the inpost and biala-lista skills from https://github.com/b44x/ai-polish-skills into our project's skills directory.
```

---

## Manual Setup

### 1. Google Antigravity (AGY)

#### Workspace-level:
```bash
mkdir -p .agents/skills
ln -s /path/to/ai-polish-skills/skills/biala-lista .agents/skills/biala-lista
ln -s /path/to/ai-polish-skills/skills/inpost .agents/skills/inpost
```

#### Global-level (Available across all projects):
```bash
mkdir -p ~/.gemini/config/skills
ln -s /path/to/ai-polish-skills/skills/biala-lista ~/.gemini/config/skills/biala-lista
ln -s /path/to/ai-polish-skills/skills/inpost ~/.gemini/config/skills/inpost
```

### 2. Claude Code

```bash
mkdir -p .claude/skills
ln -s /path/to/ai-polish-skills/skills/inpost .claude/skills/inpost
```

### 3. Cursor / Windsurf / Custom Agents

Reference the skill in your project's rules (`.cursorrules` or `.windsurfrules`):

```markdown
When dealing with Polish VAT or companies, follow skills/biala-lista/SKILL.md.
When dealing with InPost parcels or Paczkomaty, follow skills/inpost/SKILL.md.
```

### 4. Direct CLI Execution (Standalone)

All skill scripts are standalone Python 3 utilities using only the standard library:

```bash
# Verify contractor in Polish VAT White List
python3 skills/biala-lista/scripts/biala_lista.py nip 5252344078

# Convert foreign currency invoice to PLN using official NBP tax rates (Art. 31a VAT)
python3 skills/nbp/scripts/nbp.py invoice 1500 EUR 2026-09-28

# Verify company board and signing representation in Ministry of Justice KRS
python3 skills/krs/scripts/krs.py repr 0000006865

# Find nearest Paczkomat lockers
python3 skills/inpost/scripts/inpost.py near 52.2297 21.0122 --limit 3
```

---

## Best Practices

When authoring or contributing skills to this repository:

1. **Progressive Disclosure:** Keep the root `SKILL.md` concise (< 500 lines). Offload large schemas, payload references, and background theory to `references/` so models only load what they need.
2. **Deterministic Scripts Over Hallucination:** If a task involves APIs, calculations, or exact parsing, encapsulate it in a script (`scripts/<name>.py`). Models should execute the script rather than guessing.
3. **Zero External Dependencies:** Scripts must run on standard Python 3.8+ (`urllib`, `json`, `argparse`, etc.) without requiring `pip install`.
4. **Structured JSON Output:** CLI scripts must always emit valid JSON to `stdout` on success, and structured JSON error objects `{"error": "...", "type": "..."}` to `stderr` on failure.
5. **Standard Exit Codes:**
   - `0`: Success
   - `2`: Resource not found
   - `64`: Validation error / bad arguments
   - `69`: Upstream API / network error

---

## Quality & Validation

Every PR and commit is automatically checked via GitHub Actions:

```bash
python3 scripts/validate_skills.py
```

## Contributing & Releases

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy (`dev` -> `main`), semantic commit conventions, and release tagging procedures.

---

## Author & License

Created and maintained by **Michell Hoduń** ([@b44x](https://github.com/b44x) / [ai-polish-skills](https://github.com/b44x/ai-polish-skills)).

Distributed under the [MIT License](LICENSE).
