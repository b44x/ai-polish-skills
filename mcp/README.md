# Polskie Skille — MCP server

A local [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the skills in
this repository as MCP tools. One file, Python 3.8+ standard library only, no `pip install`.

- **Local (stdio):** it runs on your machine, so the Polish APIs see your IP address. Some of them
  (Ministry of Finance, NFZ) block cloud IP ranges, which is why this is not a hosted server.
- **Read-only:** every tool only reads public data; nothing is written anywhere.
- **Same code as the skills:** each tool runs the unmodified `skills/<name>/scripts/<name>.py`
  with a fixed argument list (no shell) and returns its JSON.

## Install

Clone the repository (or use the plugin/extension below):

```bash
git clone https://github.com/b44x/ai-polish-skills.git
```

In the configs below, replace `/path/to/ai-polish-skills` with the absolute path of the clone.
On Windows use `py` (or `python`) instead of `python3`.

### Claude Code

```bash
# via the plugin marketplace (no clone needed)
/plugin marketplace add b44x/ai-polish-skills
/plugin install polskie-skille-mcp@polskie-skille

# or from a clone
claude mcp add polskie-skille -- python3 /path/to/ai-polish-skills/mcp/server.py
```

### Claude Desktop

`claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "polskie-skille": {
      "command": "python3",
      "args": ["/path/to/ai-polish-skills/mcp/server.py"]
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project): the same `mcpServers` block as for
Claude Desktop.

### VS Code (GitHub Copilot agent mode)

`.vscode/mcp.json`:

```json
{
  "servers": {
    "polskie-skille": {
      "type": "stdio",
      "command": "python3",
      "args": ["/path/to/ai-polish-skills/mcp/server.py"]
    }
  }
}
```

### Gemini CLI

`gemini extensions install https://github.com/b44x/ai-polish-skills` installs the skills and this
server together (see `gemini-extension.json`).

## Tools

| Tool | Skill | What it returns |
|---|---|---|
| `biala_lista_nip`, `biala_lista_check_account` | biala-lista | VAT status by NIP; whether a bank account is on the VAT White List |
| `krs_company`, `krs_representation` | krs | KRS extract summary; who can sign contracts |
| `nbp_rate`, `nbp_invoice`, `nbp_convert` | nbp | NBP rates; invoice conversion per art. 31a VAT; currency conversion |
| `imgw_weather`, `imgw_warnings` | imgw | Current IMGW-PIB observations; official warnings |
| `nfz_near`, `nfz_benefits` | nfz | Clinics and forecast waiting times (PCUŚ); official service names |
| `sejm_votings`, `sejm_voting`, `sejm_mps` | sejm | Sejm votings, voting results, MPs |
| `prawo_article`, `prawo_act`, `prawo_search` | prawo | Article wording with source date; act status and amendments; search |
| `terminy_month`, `terminy_deadlines`, `terminy_add_days`, `terminy_holidays` | terminy | Working days and norm; ZUS/PIT/CIT/VAT/PPK deadlines; payment terms; holidays (offline) |
| `inpost_track`, `inpost_near` | inpost | Parcel tracking; nearest Paczkomat lockers |
| `filmweb_search`, `filmweb_film` | filmweb | Film/series search and details (unofficial API) |

A failed call returns `isError: true` with the skill's error message and exit meaning
(`not found`, `invalid arguments`, `upstream API or network error`).

## Test

```bash
python3 scripts/test_mcp.py        # offline handshake, schema and tool-call checks (also run in CI)
```

Set `POLSKIE_SKILLE_DIR` to use a skills directory other than `../skills`.
