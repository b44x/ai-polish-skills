# ai-polish-skills

A curated collection of modular, production-ready AI agent skills (`SKILL.md` format) tailored for Polish services, APIs, and workflows.

Every skill provides:
- A standardized `SKILL.md` definition with YAML frontmatter (progressive disclosure).
- Dependency-free Python 3 helper scripts that communicate via clean JSON.
- Output references, schema documentation, and error specifications.

---

## Available Skills

| Skill | Description | Triggers / Keywords |
|---|---|---|
| [`biala-lista`](skills/biala-lista/SKILL.md) | Official Polish Ministry of Finance White List (*Biała Lista Podatników VAT*). Verify active VAT payer status, company registry details, and registered settlement bank accounts before B2B transfers. | NIP, REGON, VAT status, "sprawdź NIP", "biała lista", "rachunek na białej liście", split payment |
| [`inpost`](skills/inpost/SKILL.md) | InPost parcel tracking and Paczkomat parcel locker finder across Poland. Lookup locker details (address, 24/7 access, Strefa Łatwego Dostępu, photos) and find nearest lockers by GPS coordinates. | InPost, Paczkomat, "gdzie moja paczka", "status przesyłki InPost", "najbliższy paczkomat" |
| [`filmweb`](skills/filmweb/SKILL.md) | Polish film and TV series database (Filmweb.pl). Search titles, ratings, user reviews, cast, premiere dates, and VOD availability with prices in PLN. | Filmweb, ocena filmu, "gdzie obejrzę", "kto grał w", polskie recenzje, seriale |

---

## Installation & Setup

Skills in this repository follow the open agent skill standard (`skills/<name>/SKILL.md`). They can be mounted into any AI coding assistant or agent framework.

### 1. Google Antigravity (AGY)

#### Workspace-level (Recommended for project repos):
Symlink or copy the desired skill directory into your project's `.agents/skills/` directory:

```bash
mkdir -p .agents/skills
ln -s /path/to/ai-polish-skills/skills/biala-lista .agents/skills/biala-lista
ln -s /path/to/ai-polish-skills/skills/inpost .agents/skills/inpost
```

#### Global-level (Available across all projects):
Symlink or copy into the global Antigravity config directory:

```bash
mkdir -p ~/.gemini/config/skills
ln -s /path/to/ai-polish-skills/skills/biala-lista ~/.gemini/config/skills/biala-lista
ln -s /path/to/ai-polish-skills/skills/inpost ~/.gemini/config/skills/inpost
```

### 2. Claude Code

Copy or symlink into your project's `.claude/skills/` or user-wide `~/.claude/skills/`:

```bash
mkdir -p .claude/skills
ln -s /path/to/ai-polish-skills/skills/inpost .claude/skills/inpost
```

### 3. Cursor / Windsurf / Custom Agents

Reference the skill folder in your project's system rules or prompt configuration (e.g., in `.cursorrules` or `.windsurfrules`):

```markdown
When dealing with Polish VAT or companies, follow the instructions in skills/biala-lista/SKILL.md.
When dealing with InPost parcels or Paczkomaty, follow skills/inpost/SKILL.md.
```

### 4. Direct CLI Execution (Standalone)

All skill scripts are standalone Python 3 utilities using only the standard library:

```bash
# Verify contractor in Polish VAT White List
python3 skills/biala-lista/scripts/biala_lista.py nip 5252344078

# Check bank account assignment
python3 skills/biala-lista/scripts/biala_lista.py check 5252344078 93103015080000000504162006

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
