<p align="center">
  🇬🇧 <b>English</b> | 🇵🇱 <a href="README.md">Polski</a>
</p>

# ai-polish-skills 🇵🇱

Official open-source registry and catalog of AI agent skills tailored for the **Polish market, public registers, services, and APIs**.

> 🌐 Discovery layer & web catalog: **[polskieskille.pl](https://polskieskille.pl)**  
> 📦 Open-source core & registry: **[github.com/b44x/ai-polish-skills](https://github.com/b44x/ai-polish-skills)**

---

## Demo

**See Polskie Skille in action** — one question in Polish, the agent picks a skill, the skill queries an official Polish source (Ministry of Finance, KRS, NBP, IMGW-PIB, NFZ, Sejm RP, InPost) and returns a human-readable result. Every value in the video comes from real runs of the skills.

<p align="center">
  <a href="docs/demo/demo.mp4"><img src="docs/demo/demo.gif" alt="Polskie Skille demo: an AI agent using Polish APIs and public data" width="960"></a>
</p>

<p align="center">
  ▶️ <a href="docs/demo/demo.mp4"><b>Watch the full demo (MP4, 1080p, 95 s)</b></a> · 🌐 <a href="https://polskieskille.pl">polskieskille.pl</a> · 🛠 <a href="docs/demo/README.md">how to regenerate the demo</a>
</p>

---

## 💡 What are Polish Skills?

**ai-polish-skills** is an ecosystem of modular extensions for AI agents that provide models with direct, real-time access to Polish services. Rather than hallucinating information about VAT numbers, exchange rates, or parcel tracking, the agent executes a deterministic script and parses structured JSON output.

### Key Principles:
- **Zero dependencies (pip-free):** All scripts use Python 3.8+ standard library only.
- **Deterministic output:** Clean JSON on `stdout`, errors on `stderr`, standardized exit codes.
- **Single source of truth:** All skill metadata is stored directly in the `SKILL.md` YAML frontmatter.
- **Verified sources:** Explicit declaration whether the data source is an official API (`official_api`), public API, or unofficial API.

---

## 📄 What is the `SKILL.md` standard?

`SKILL.md` is an open instruction format for AI agents. Each directory in `skills/<name>` contains a `SKILL.md` file featuring:
1. **YAML Frontmatter (Manifest):** Skill metadata (`name`, `version`, `category`, `source`, `network`, `tags`, etc.). The agent inspects this header to determine whether the skill fits the user's intent (*Progressive Disclosure*).
2. **Markdown Body:** Detailed instructions for the model, parameters, workflows, and command reference tables for Linux, macOS, and Windows.
3. **Scripts in `scripts/`:** CLI utilities executed directly by the agent.

---

## 📦 Available Skills in Registry

| Skill | Name & Category | Description | Data Source |
|---|---|---|---|
| [`biala-lista`](skills/biala-lista/SKILL.md) | **Biała Lista VAT** `[finance]` | Verify Polish VAT status, NIP, REGON, KRS, and registered bank accounts before B2B transfers (split payment). | Ministry of Finance (🏛 official API) |
| [`nbp`](skills/nbp/SKILL.md) | **Narodowy Bank Polski** `[finance]` | Average exchange rates (Tables A & B), gold prices, and tax invoice calculation according to Art. 31a Polish VAT Act. | Narodowy Bank Polski (🏛 official API) |
| [`krs`](skills/krs/SKILL.md) | **Krajowy Rejestr Sądowy** `[legal]` | Court register extracts for companies and foundations, board members, share capital, and signing authority rules. | Ministry of Justice (🏛 official API) |
| [`inpost`](skills/inpost/SKILL.md) | **InPost & Paczkomaty** `[logistics]` | Parcel tracking by 24-digit tracking number, locker locator by code, address, city, or GPS coordinates with distance. | InPost ShipX (🔗 public API) |
| [`filmweb`](skills/filmweb/SKILL.md) | **Filmweb** `[entertainment]` | Polish film and series database, ratings, cast, premiere dates, and VOD streaming providers with prices in PLN. | Filmweb.pl (🔗 reverse-engineered API) |
| [`imgw`](skills/imgw/SKILL.md) | **IMGW-PIB Weather & Alerts** `[public_data]` | Official Polish weather observations (temp, pressure, wind, rain) from 62 synoptic stations, meteo/hydro alerts, and river levels. | IMGW-PIB (🏛 official API) |
| [`sejm`](skills/sejm/SKILL.md) | **Sejm RP** `[legal]` | Polish parliamentary open data: MPs, committees, roll-call and club voting results, prints, and legislative stages. | Chancellery of the Sejm (🏛 official API) |
| [`nfz`](skills/nfz/SKILL.md) | **NFZ Healthcare Queues (PCUŚ)** `[health]` | Official data on estimated waiting times (MRI, CT, clinics), awaiting patients count, urgent/stable cases, and radius clinic search. | National Health Fund (NFZ) (🏛 official API) |

---

## 🔍 How to Find Skills?

Browse and query the registry using the built-in CLI or installer:

```bash
# List all available skills
./install.sh list
# or
python3 scripts/cli.py list

# Search skills by keyword
./install.sh search faktury
python3 scripts/cli.py search paczkomat

# Detailed skill info, source, and contract
./install.sh info biala-lista
python3 scripts/cli.py info krs
```

---

## ⚡ How to Install Skills?

### 1. Automatic Installer (Recommended)

Install all or selected skills with a single command:

```bash
# Install all skills into your current AI project
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash

# Install specific skills only (e.g. inpost, biala-lista)
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s inpost biala-lista

# Global install (for Google Antigravity: ~/.gemini/config/skills)
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s -- --global
```

The installer **automatically detects** your environment (Claude Code, Antigravity, Cursor, Windsurf) and places files in the right path.

### 2. Install by Prompting your AI Agent

Paste this prompt into your agent's chat:

```text
Install the inpost and biala-lista skills from https://github.com/b44x/ai-polish-skills into our project's skills directory.
```

Your agent will fetch the required directories and gain immediate access.

### 3. Using the Built-in CLI

If you have cloned the repository locally:

```bash
python3 scripts/cli.py install inpost biala-lista
python3 scripts/cli.py update
```

### 4. Claude Code — Plugin Marketplace

```bash
/plugin marketplace add b44x/ai-polish-skills
/plugin install polskie-skille@polskie-skille   # every skill
/plugin install nbp@polskie-skille              # or a single skill
```

### 5. Gemini CLI — Extension

```bash
gemini extensions install https://github.com/b44x/ai-polish-skills
```

---

## 🚀 How to Run Skills?

### Via AI Agent (Natural Language)
Once installed, your agent automatically executes the appropriate script based on your question:
- *"Check if contractor with NIP 5260250274 is an active VAT payer on the White List"*
- *"Who can sign contracts on behalf of company KRS 0000006865?"*
- *"Calculate PLN tax amount for a 1500 EUR invoice dated 2026-09-25 using official NBP rates"*
- *"Find the nearest Paczkomat in Warsaw near Chmielna street"*

### Standalone CLI Execution
Every skill can be executed directly from terminal:

```bash
# Verify NIP in Polish VAT White List
python3 skills/biala-lista/scripts/biala_lista.py nip 5260250274

# Verify signing authority in court register (KRS)
python3 skills/krs/scripts/krs.py repr 0000006865

# Convert foreign currency invoice according to Art. 31a VAT law
python3 skills/nbp/scripts/nbp.py invoice 1500 EUR 2026-09-25

# Locate parcel lockers near GPS coordinates
python3 skills/inpost/scripts/inpost.py near 52.2297 21.0122 --limit 3
```

---

## 🤖 Supported Agents and IDEs

| Environment | `SKILL.md` Support | Installation Directory |
|---|:---:|---|
| **Claude Code** | Native | plugin marketplace or `.claude/skills/<skill>/` |
| **Gemini CLI** | Native (extension) | `gemini extensions install …` |
| **GitHub Copilot (VS Code, CLI)** | Native | `.agents/skills/<skill>/`, `.github/skills/<skill>/` or `.claude/skills/<skill>/` |
| **Google Antigravity (AGY)** | Native | `.agents/skills/<skill>/` or `~/.gemini/config/skills/` |
| **Cursor** | Via `.cursorrules` / context | `.agents/skills/<skill>/` |
| **Windsurf** | Via `.windsurfrules` | `.agents/skills/<skill>/` |
| **OpenAI Codex** | Native | `.agents/skills/<skill>/` or `~/.agents/skills/<skill>/` |
| **Other agents** | Standard CLI & JSON | Any directory with Python scripts |

---

## 🛠 How to Add a New Skill?

Contributing a skill follows a simple, 8-step Pull Request process:

1. Select a Polish service or public register.
2. Verify source authenticity and usage terms.
3. Copy `templates/skill/` to `skills/<your-skill>/`.
4. Write instructions in `SKILL.md`.
5. Populate metadata in the YAML frontmatter header (manifest).
6. Implement Python script in `scripts/<your-skill>.py` (Python 3.8+ stdlib, clean JSON on stdout).
7. Run the validator (`python3 scripts/validate_skills.py`) and test harness (`python3 scripts/test_skills.py`).
8. Open a Pull Request to branch `dev`.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for detailed instructions and the PR checklist.

---

## 🌐 polskieskille.pl & Registry Layer

The repository generates deterministic, static registry files:
- `registry/registry.json` — Complete index of skills, metadata, categories, and file lists.
- `registry/registry.min.json` — Minified version for fast web fetching.
- `registry/schema.json` — Official JSON Schema for validation.

The **polskieskille.pl** platform directly consumes this registry to serve an interactive web catalog and discovery layer.

## Support the project

Polskie Skille is an open-source initiative providing AI agents with reliable tools and real-time data from Polish services, registers, and APIs. Your sponsorship directly supports:

- Building new Polish integrations (CEIDG, GUS/BIR, IMGW weather alerts, KSeF e-invoicing).
- Refining the `SKILL.md` standard, test harness, validator, and static registry.
- Ensuring ongoing compatibility with emerging AI agents (Claude Code, Cursor, Windsurf, Antigravity).
- API maintenance, uptime checks, and security audits.

Support the project via **[GitHub Sponsors (github.com/sponsors/b44x)](https://github.com/sponsors/b44x)** (monthly or one-time):

| Tier | Amount | Type | Focus |
|---|---|---|---|
| **Supporter** | **$3** / mo | Monthly | General open-source maintenance & community support |
| **AI Builder** | **$10** / mo | Monthly | Accelerating development of new Polish skills & APIs |
| **Polish AI** | **$25** / mo | Monthly | Sustaining test infrastructure, registry updates & agent benchmarks |
| **Company** | **$100** / mo | Monthly | Organization sponsorship for building on the Polish AI ecosystem |
| **Coffee** | **$10** | One-time | One-time coffee contribution supporting the maintainer |

Every contribution helps keep the project independent, well-tested, and actively maintained.

---

## Author & License

Created and maintained by: **Michell Hoduń** ([@b44x](https://github.com/b44x)).  
Repository: [github.com/b44x/ai-polish-skills](https://github.com/b44x/ai-polish-skills).  
License: [MIT License](LICENSE).

