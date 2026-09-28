#!/usr/bin/env python3
"""Polskie Skille — local MCP server (stdio) exposing the skills in ../skills as MCP tools.

Runs on the user's machine, so upstream APIs see the user's own IP address (some Polish
public APIs block cloud IP ranges). Every tool call runs the unmodified skill script with a
fixed argument list (no shell) and returns its JSON output.

Protocol: Model Context Protocol over stdio, newline-delimited JSON-RPC 2.0.
Zero external dependencies (Python 3.8+ standard library only).

Usage (Claude Desktop, Cursor, VS Code, …):
    {"command": "python3", "args": ["/path/to/ai-polish-skills/mcp/server.py"]}

Copyright (c) 2026 Michell Hoduń <mhodun@gmail.com> (https://github.com/b44x)
Licensed under the MIT License.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

SERVER_NAME = "polskie-skille"
SERVER_VERSION = "0.9.0"
SUPPORTED_PROTOCOLS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
SKILLS_DIR = Path(os.environ.get("POLSKIE_SKILLE_DIR") or Path(__file__).resolve().parent.parent / "skills")
CALL_TIMEOUT_S = 90
EXIT_MEANING = {2: "not found", 64: "invalid arguments", 69: "upstream API or network error"}

INSTRUCTIONS = (
    "Tools for Polish services, official APIs and public data. Answer the user in their language "
    "(usually Polish). Always name the source returned in the tool output. For legal texts (prawo_*) "
    "state the date of the source document and pass on any warning about later amendments. "
    "NFZ waiting times are statistical forecasts (PCUŚ), not appointment dates."
)

S = {"type": "string"}
N = {"type": "number"}
I = {"type": "integer"}
DATE = {"type": "string", "description": "Date YYYY-MM-DD", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
MONTH = {"type": "string", "description": "Month YYYY-MM", "pattern": r"^\d{4}-\d{2}$"}


def opt(args: Dict[str, Any], key: str, flag: str) -> List[str]:
    """Optional '--flag value' pair when the argument is present."""
    value = args.get(key)
    return [] if value is None or value == "" else [flag, str(value)]


def tool(name: str, title: str, skill: str, description: str, props: Dict[str, Any], required: List[str],
         argv: Callable[[Dict[str, Any]], List[str]], network: bool = True) -> Dict[str, Any]:
    return {
        "name": name, "title": title, "skill": skill, "argv": argv,
        "description": description,
        "inputSchema": {"type": "object", "properties": props, "required": required, "additionalProperties": False},
        "annotations": {"title": title, "readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": network},
    }


TOOLS: List[Dict[str, Any]] = [
    # --- biala-lista (Ministry of Finance VAT white list)
    tool("biala_lista_nip", "Biała Lista VAT: podmiot po NIP", "biala-lista",
         "Company data and VAT status (Czynny/Zwolniony) from the Ministry of Finance White List by NIP: name, REGON, KRS, address, registered bank accounts. E.g. 'sprawdź NIP', 'status VAT kontrahenta'.",
         {"nip": {**S, "description": "10-digit NIP"}, "date": DATE}, ["nip"],
         lambda a: ["nip", str(a["nip"])] + opt(a, "date", "--date")),
    tool("biala_lista_check_account", "Biała Lista VAT: czy konto należy do NIP", "biala-lista",
         "Check whether a 26-digit bank account is registered for a NIP on the VAT White List (split payment, B2B transfers above 15 000 PLN).",
         {"nip": S, "account": {**S, "description": "26-digit account number (NRB)"}, "date": DATE}, ["nip", "account"],
         lambda a: ["check", str(a["nip"]), str(a["account"])] + opt(a, "date", "--date")),
    # --- krs
    tool("krs_company", "KRS: dane spółki", "krs",
         "Official National Court Register (KRS) extract summary: name, legal form, NIP, REGON, address, share capital, board, proxies.",
         {"krs": {**S, "description": "KRS number, e.g. 0000006865"}}, ["krs"], lambda a: ["info", str(a["krs"])]),
    tool("krs_representation", "KRS: kto może podpisać umowę", "krs",
         "Representation rules (sposób reprezentacji), board members and commercial proxies: who can sign a contract for the company.",
         {"krs": S}, ["krs"], lambda a: ["repr", str(a["krs"])]),
    # --- nbp
    tool("nbp_rate", "NBP: kurs średni waluty", "nbp",
         "Official NBP average exchange rate (tables A/B) for a currency, optionally for a date. E.g. 'kurs euro', 'kurs dolara'.",
         {"currency": {**S, "description": "ISO code, e.g. EUR, USD"}, "date": DATE}, ["currency"],
         lambda a: ["rate", str(a["currency"])] + opt(a, "date", "--date")),
    tool("nbp_invoice", "NBP: przeliczenie faktury walutowej (art. 31a VAT)", "nbp",
         "Convert a foreign-currency invoice to PLN using the NBP rate from the last business day before the invoice date (art. 31a VAT Act).",
         {"amount": N, "currency": S, "date": {**DATE, "description": "Invoice date YYYY-MM-DD"}}, ["amount", "currency", "date"],
         lambda a: ["invoice", str(a["amount"]), str(a["currency"]), str(a["date"])]),
    tool("nbp_convert", "NBP: przelicz walutę", "nbp",
         "Convert an amount between currencies (including PLN) with official NBP rates.",
         {"amount": N, "from_currency": S, "to_currency": S, "date": DATE}, ["amount", "from_currency", "to_currency"],
         lambda a: ["convert", str(a["amount"]), str(a["from_currency"]), str(a["to_currency"])] + opt(a, "date", "--date")),
    # --- imgw
    tool("imgw_weather", "IMGW-PIB: aktualna pogoda", "imgw",
         "Current official observations from an IMGW-PIB synoptic station: temperature, pressure, wind, humidity, rainfall. E.g. 'pogoda w Zakopanem'.",
         {"station": {**S, "description": "Station or city, e.g. Warszawa, Zakopane"}}, ["station"],
         lambda a: ["weather", str(a["station"])]),
    tool("imgw_warnings", "IMGW-PIB: ostrzeżenia", "imgw",
         "Official IMGW-PIB meteorological and hydrological warnings, optionally for one voivodeship.",
         {"type": {"type": "string", "enum": ["meteo", "hydro", "all"]}, "voivodeship": {**S, "description": "e.g. pomorskie"}}, [],
         lambda a: ["warnings"] + opt(a, "type", "--type") + opt(a, "voivodeship", "--voivodeship")),
    # --- nfz
    tool("nfz_near", "NFZ: placówki i prognozowany czas oczekiwania", "nfz",
         "Clinics providing an NFZ-funded service within a radius of a city, with the forecast waiting time (PCUŚ — a statistical estimate, not an appointment date). E.g. 'gdzie na rezonans na NFZ'.",
         {"location": {**S, "description": "City, e.g. Gdańsk"}, "benefit": {**S, "description": "Service, e.g. rezonans, kardiolog"},
          "radius_km": N, "urgent": {"type": "boolean"}, "limit": I}, ["location", "benefit"],
         lambda a: ["near", str(a["location"]), "--benefit", str(a["benefit"])] + opt(a, "radius_km", "--radius-km")
         + (["--urgent"] if a.get("urgent") else []) + opt(a, "limit", "--limit")),
    tool("nfz_benefits", "NFZ: nazwy świadczeń", "nfz",
         "Official NFZ service names matching a phrase (min. 3 characters).",
         {"query": S}, ["query"], lambda a: ["benefits", str(a["query"])]),
    # --- sejm
    tool("sejm_votings", "Sejm RP: lista głosowań", "sejm",
         "Votings of a Sejm sitting (default: the latest), optionally filtered by a phrase.",
         {"sitting": I, "search": S, "limit": I}, [],
         lambda a: ["votings"] + opt(a, "sitting", "--sitting") + opt(a, "search", "--search") + opt(a, "limit", "--limit")),
    tool("sejm_voting", "Sejm RP: wynik głosowania", "sejm",
         "Result of one Sejm voting: yes/no/abstain/not voting, club breakdown, optionally how one MP voted. Report data only, without political evaluation.",
         {"sitting": I, "number": I, "mp": {**S, "description": "MP name or ID"}}, ["sitting", "number"],
         lambda a: ["voting", str(a["sitting"]), str(a["number"])] + opt(a, "mp", "--mp")),
    tool("sejm_mps", "Sejm RP: posłowie", "sejm",
         "Search Members of Parliament by name, club or district.",
         {"search": S, "club": S, "district": S, "limit": I}, [],
         lambda a: ["mps"] + opt(a, "search", "--search") + opt(a, "club", "--club") + opt(a, "district", "--district") + opt(a, "limit", "--limit")),
    # --- prawo
    tool("prawo_article", "Prawo: brzmienie artykułu", "prawo",
         "Wording of an article of a Polish code or statute from ISAP, with the source document date and a warning about later amendments. Act: shortcut (kp, kc, kk, vat, pit, ksh…), 'DU/2023/1465' or 'Dz.U. 2023 poz. 1465'.",
         {"act": S, "article": {**S, "description": "e.g. 30, 22a, 67^18"}}, ["act", "article"],
         lambda a: ["article", str(a["act"]), str(a["article"])]),
    tool("prawo_act", "Prawo: status aktu i zmiany", "prawo",
         "Status of a Polish legal act, its latest consolidated text (PDF link) and amendments with entry-into-force dates, including upcoming ones.",
         {"act": S}, ["act"], lambda a: ["act", str(a["act"])]),
    tool("prawo_search", "Prawo: wyszukaj akt", "prawo",
         "Search Polish legal acts (Dziennik Ustaw) by words in the title.",
         {"query": S, "in_force": {"type": "boolean"}, "type": {**S, "description": "e.g. Ustawa, Rozporządzenie"}, "limit": I}, ["query"],
         lambda a: ["search", str(a["query"])] + (["--in-force"] if a.get("in_force") else []) + opt(a, "type", "--type") + opt(a, "limit", "--limit")),
    # --- terminy (offline)
    tool("terminy_month", "Terminy: dni robocze i wymiar czasu pracy", "terminy",
         "Working days and full-time working-time norm (art. 130 Kodeksu pracy) for a month, with holidays.",
         {"month": MONTH}, ["month"], lambda a: ["month", str(a["month"])], network=False),
    tool("terminy_deadlines", "Terminy: ZUS, PIT, CIT, VAT, PPK", "terminy",
         "Monthly ZUS, PIT, CIT, VAT (JPK_V7M) and PPK deadlines for a settlement month, moved off weekends and holidays (art. 12 § 5 Ordynacji podatkowej).",
         {"month": {**MONTH, "description": "Settlement month YYYY-MM (deadlines fall in the next month)"}}, ["month"],
         lambda a: ["deadlines", str(a["month"])], network=False),
    tool("terminy_add_days", "Terminy: data + N dni", "terminy",
         "Deadline N calendar days after a date (e.g. invoice payment term), moved to the next working day (art. 115 KC), or N working days with workdays=true.",
         {"date": DATE, "days": I, "workdays": {"type": "boolean"}}, ["date", "days"],
         lambda a: ["add", str(a["date"]), str(a["days"])] + (["--workdays"] if a.get("workdays") else []), network=False),
    tool("terminy_holidays", "Terminy: święta", "terminy",
         "Polish statutory public holidays of a year (including Wigilia from 2025).",
         {"year": I}, [], lambda a: ["holidays"] + opt(a, "year", "--year"), network=False),
    # --- inpost
    tool("inpost_track", "InPost: śledzenie przesyłki", "inpost",
         "Status and history of an InPost parcel by its 24-digit number.",
         {"number": S}, ["number"], lambda a: ["track", str(a["number"])]),
    tool("inpost_near", "InPost: najbliższe Paczkomaty", "inpost",
         "Nearest InPost Paczkomat lockers to GPS coordinates, with distance and opening hours.",
         {"latitude": N, "longitude": N, "limit": I}, ["latitude", "longitude"],
         lambda a: ["near", str(a["latitude"]), str(a["longitude"])] + opt(a, "limit", "--limit")),
    # --- filmweb (unofficial API)
    tool("filmweb_search", "Filmweb: wyszukaj film lub serial", "filmweb",
         "Search Filmweb.pl for films or series by title (unofficial API).",
         {"query": S, "type": {"type": "string", "enum": ["film", "serial", "game"]}}, ["query"],
         lambda a: ["search", str(a["query"])] + ([f"--type={a['type']}"] if a.get("type") else [])),
    tool("filmweb_film", "Filmweb: szczegóły i oceny", "filmweb",
         "Filmweb title details: year, ratings, genres, duration, directors, main cast, plot.",
         {"id": {**S, "description": "Filmweb ID or URL"}}, ["id"], lambda a: ["film", str(a["id"])]),
]
TOOLS_BY_NAME = {t["name"]: t for t in TOOLS}


def script_path(skill: str) -> Path:
    return SKILLS_DIR / skill / "scripts" / f"{skill.replace('-', '_')}.py"


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    spec = TOOLS_BY_NAME[name]
    missing = [k for k in spec["inputSchema"]["required"] if arguments.get(k) in (None, "")]
    if missing:
        return {"content": [{"type": "text", "text": f"Missing required arguments: {', '.join(missing)}"}], "isError": True}
    unknown = sorted(set(arguments) - set(spec["inputSchema"]["properties"]))
    if unknown:
        return {"content": [{"type": "text", "text": f"Unknown arguments: {', '.join(unknown)}"}], "isError": True}
    cmd = [sys.executable, str(script_path(spec["skill"]))] + spec["argv"](arguments)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=CALL_TIMEOUT_S,
                              cwd=str(SKILLS_DIR / spec["skill"]))
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": f"Timeout after {CALL_TIMEOUT_S} s"}], "isError": True}
    if proc.returncode == 0:
        return {"content": [{"type": "text", "text": proc.stdout.strip()}], "isError": False}
    detail = (proc.stderr or proc.stdout).strip() or "no details"
    meaning = EXIT_MEANING.get(proc.returncode, "error")
    return {"content": [{"type": "text", "text": f"{spec['skill']} failed ({meaning}, exit {proc.returncode}): {detail}"}],
            "isError": True}


def public_tool(spec: Dict[str, Any]) -> Dict[str, Any]:
    return {k: spec[k] for k in ("name", "title", "description", "inputSchema", "annotations")}


def handle(msg: Any) -> Optional[Dict[str, Any]]:
    """Handle one JSON-RPC message; returns a response, or None for notifications."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
        return {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None,
                "error": {"code": -32600, "message": "Invalid Request"}}
    method, mid, params = msg["method"], msg.get("id"), msg.get("params") or {}
    if "id" not in msg:
        return None  # notification (notifications/initialized, notifications/cancelled, …)

    def ok(result: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
        return ok({"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": SERVER_NAME, "title": "Polskie Skille", "version": SERVER_VERSION},
                   "instructions": INSTRUCTIONS})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [public_tool(t) for t in TOOLS]})
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOLS_BY_NAME:
            return err(-32602, f"Unknown tool: {name}")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return err(-32602, "arguments must be an object")
        return ok(call_tool(name, arguments))
    return err(-32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply: Any = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            if isinstance(msg, list):
                reply = [r for r in (handle(m) for m in msg) if r is not None] or None
            else:
                reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
