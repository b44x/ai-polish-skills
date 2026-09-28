#!/usr/bin/env python3
"""Unified CLI for ai-polish-skills (polskieskille.pl).

Commands:
  list                          List all available Polish AI skills
  search <query>                Search skills by keyword, category, or tag
  info <skill>                  Display detailed metadata and contract for a skill
  install [skills...] [options] Install skills into your AI assistant environment
  update [options]              Update installed skills to latest versions
  validate                      Run registry validation suite
  test                          Run test contract harness

Zero external dependencies (Python 3.8+ standard library only).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from manifest import load_skill_manifest

REPO_URL = "https://github.com/b44x/ai-polish-skills"
TARBALL_URL = "https://github.com/b44x/ai-polish-skills/archive/refs/heads/main.tar.gz"

# ANSI colors
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def get_skills_dir() -> Path:
    """Locate local skills directory if running inside repo."""
    local = ROOT_DIR / "skills"
    if local.is_dir():
        return local
    raise FileNotFoundError("Local skills directory not found. Please run inside ai-polish-skills repository.")


def get_all_skills() -> Dict[str, Dict[str, Any]]:
    """Load all skills metadata from local skills directory."""
    skills_dir = get_skills_dir()
    result = {}
    for d in sorted(skills_dir.iterdir()):
        if d.is_dir() and not d.name.startswith((".", "_")):
            manifest, _ = load_skill_manifest(d)
            if manifest:
                manifest["_dir"] = str(d)
                result[d.name] = manifest
    return result


def determine_target_dir(args: argparse.Namespace) -> Path:
    """Determine installation target directory based on flags and environment."""
    if getattr(args, "dir", None):
        return Path(args.dir).expanduser().resolve()
    if getattr(args, "global_install", False):
        return Path.home() / ".gemini" / "config" / "skills"
    if getattr(args, "claude", False):
        return Path.cwd() / ".claude" / "skills"
    if getattr(args, "antigravity", False):
        return Path.cwd() / ".agents" / "skills"

    # Auto-detection
    if (Path.cwd() / ".claude").is_dir():
        return Path.cwd() / ".claude" / "skills"
    return Path.cwd() / ".agents" / "skills"


def cmd_list(args: argparse.Namespace) -> int:
    skills = get_all_skills()

    if getattr(args, "json", False):
        output = [
            {k: v for k, v in data.items() if not k.startswith("_")}
            for data in skills.values()
        ]
        if getattr(args, "category", None):
            output = [s for s in output if s.get("category") == args.category]
        if getattr(args, "tag", None):
            output = [s for s in output if args.tag in s.get("tags", [])]
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0

    print(f"\n{BOLD}{BLUE}ai-polish-skills • polskieskille.pl{RESET}")
    print(f"{DIM}Dostępne polskie skille AI ({len(skills)} w rejestrze):{RESET}\n")

    for name, s in skills.items():
        if getattr(args, "category", None) and s.get("category") != args.category:
            continue
        if getattr(args, "tag", None) and args.tag not in s.get("tags", []):
            continue

        category = f"[{s.get('category', 'general')}]"
        version = f"v{s.get('version', '1.0.0')}"
        display = s.get("display_name", name)
        network = "🌐 sieć" if s.get("network") else "⚡ offline"
        official = "🏛 oficjalne API" if s.get("official") else f"🔗 {s.get('source_type', 'api')}"

        print(f"  {BOLD}{name:<14}{RESET} {GREEN}{version:<8}{RESET} {CYAN}{category:<15}{RESET} {display}")
        print(f"    {DIM}Źródło: {s.get('source')} ({official}) • {network} • auth: {s.get('authentication')}{RESET}")
        desc = s.get("description", "")
        short_desc = desc[:110] + ("..." if len(desc) > 110 else "")
        print(f"    {desc_line(short_desc)}\n")

    return 0


def desc_line(text: str) -> str:
    return f"{DIM}{text}{RESET}"


def cmd_search(args: argparse.Namespace) -> int:
    query = args.query.lower().strip()
    skills = get_all_skills()
    matches = {}

    for name, s in skills.items():
        score = 0
        if query == name:
            score += 100
        elif query in name:
            score += 40
        if query in s.get("display_name", "").lower():
            score += 30
        if query in s.get("category", "").lower():
            score += 25
        if any(query in t.lower() for t in s.get("tags", [])):
            score += 20
        if query in s.get("description", "").lower():
            score += 10
        if query in s.get("source", "").lower():
            score += 10

        if score > 0:
            matches[name] = (score, s)

    sorted_matches = sorted(matches.items(), key=lambda x: -x[1][0])

    if getattr(args, "json", False):
        output = [
            {k: v for k, v in item[1][1].items() if not k.startswith("_")}
            for item in sorted_matches
        ]
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0

    if not sorted_matches:
        print(f"\nNie znaleziono skilli pasujących do zapytania: {BOLD}'{query}'{RESET}")
        print("Wpisz 'python3 scripts/cli.py list' aby zobaczyć wszystkie dostępne skille.\n")
        return 0

    print(f"\nZnaleziono {len(sorted_matches)} skill(ów) dla zapytania {BOLD}'{query}'{RESET}:\n")
    for name, (_, s) in sorted_matches:
        category = f"[{s.get('category', 'general')}]"
        version = f"v{s.get('version', '1.0.0')}"
        display = s.get("display_name", name)
        print(f"  • {BOLD}{name:<14}{RESET} {GREEN}{version:<8}{RESET} {CYAN}{category:<15}{RESET} {display}")
        desc = s.get("description", "")
        print(f"    {DIM}{desc[:120]}...{RESET}\n")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    skill_name = args.skill.strip()
    skills = get_all_skills()

    if skill_name not in skills:
        print(f"ERROR: Skill '{skill_name}' nie został znaleziony w rejestrze.", file=sys.stderr)
        print(f"Dostępne: {', '.join(skills.keys())}", file=sys.stderr)
        return 1

    s = skills[skill_name]

    if getattr(args, "json", False):
        clean = {k: v for k, v in s.items() if not k.startswith("_")}
        print(json.dumps(clean, indent=2, ensure_ascii=False))
        return 0

    print(f"\n{BOLD}═══════════════════════════════════════════════════════════════{RESET}")
    print(f" {BOLD}{s.get('display_name', skill_name)} ({skill_name}){RESET}")
    print(f"{BOLD}═══════════════════════════════════════════════════════════════{RESET}\n")

    print(f"  {BOLD}Wersja:{RESET}         {s.get('version')}")
    print(f"  {BOLD}Kategoria:{RESET}      {s.get('category')}")
    print(f"  {BOLD}Licencja:{RESET}       {s.get('license')}")
    print(f"  {BOLD}Autor:{RESET}          {s.get('author', 'Michell Hoduń')}")
    print(f"  {BOLD}Wymaga sieci:{RESET}   {'Tak (dostęp do Internetu)' if s.get('network') else 'Nie (działa w pełni offline)'}")
    print(f"  {BOLD}Uwierzytelnienie:{RESET} {s.get('authentication')}")
    print(f"  {BOLD}Źródło danych:{RESET}  {s.get('source')} ({s.get('source_type')})")
    print(f"  {BOLD}Oficjalne API:{RESET}  {'Tak' if s.get('official') else 'Nie'}")
    print(f"  {BOLD}Strona www:{RESET}     {s.get('homepage')}")
    print(f"  {BOLD}Dokumentacja:{RESET}   {s.get('documentation')}")
    print(f"  {BOLD}Limit zapytań:{RESET}  {s.get('rate_limit', 'fair use')}")
    print(f"  {BOLD}Weryfikacja:{RESET}    {s.get('last_verified', 'nieznana')}")
    print(f"  {BOLD}Tagi:{RESET}           {', '.join(s.get('tags', []))}")
    print(f"  {BOLD}Kompatybilność:{RESET} {s.get('compatibility', 'Python 3.8+')}")

    print(f"\n{BOLD}Opis:{RESET}")
    print(f"  {s.get('description')}\n")

    skill_path = Path(s["_dir"])
    skill_md = skill_path / "SKILL.md"
    if skill_md.is_file():
        print(f"{BOLD}Instrukcja SKILL.md:{RESET}")
        print(f"  ➔ {skill_md.resolve()}\n")

    return 0


def cmd_install(args: argparse.Namespace) -> int:
    target_dir = determine_target_dir(args)
    selected_skills = args.skills

    target_dir.mkdir(parents=True, exist_ok=True)
    all_skills = get_all_skills()

    if not selected_skills:
        to_install = list(all_skills.keys())
    else:
        to_install = []
        for name in selected_skills:
            if name in all_skills:
                to_install.append(name)
            else:
                print(f"WARN: Skill '{name}' nie istnieje. Dostępne: {', '.join(all_skills.keys())}")

    if not to_install:
        print("ERROR: Brak skilli do zainstalowania.", file=sys.stderr)
        return 1

    print(f"\n{BOLD}Instalacja skilli do:{RESET} {GREEN}{target_dir}{RESET}")
    for name in to_install:
        src = Path(all_skills[name]["_dir"])
        dest = target_dir / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

        # Make scripts executable
        scripts_dir = dest / "scripts"
        if scripts_dir.is_dir():
            for script in scripts_dir.glob("*.py"):
                script.chmod(script.stat().st_mode | 0o111)

        print(f"  ✓ Zainstalowano: {GREEN}{name}{RESET} (v{all_skills[name].get('version')}) ➔ {dest}")

    print(f"\n{BOLD}{GREEN}✔ Pomyślnie zainstalowano {len(to_install)} skill(ów).{RESET}\n")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    target_dir = determine_target_dir(args)
    if not target_dir.is_dir():
        print(f"Katalog {target_dir} nie istnieje. Uruchom 'install' aby zainstalować skille.", file=sys.stderr)
        return 1

    installed = [
        d.name for d in target_dir.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    ]

    if not installed:
        print(f"Brak zainstalowanych skilli w {target_dir}.")
        return 0

    print(f"\nAktualizacja skilli w: {GREEN}{target_dir}{RESET}")
    args.skills = installed
    return cmd_install(args)


def cmd_validate(args: argparse.Namespace) -> int:
    script = SCRIPT_DIR / "validate_skills.py"
    res = subprocess.run([sys.executable, str(script)])
    return res.returncode


def cmd_test(args: argparse.Namespace) -> int:
    script = SCRIPT_DIR / "test_skills.py"
    res = subprocess.run([sys.executable, str(script)])
    return res.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-polish-skills",
        description="ai-polish-skills • Oficjalne narzędzie CLI polskiego rejestru skilli AI (polskieskille.pl)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # list
    p_list = subparsers.add_parser("list", help="Lista wszystkich dostępnych skilli")
    p_list.add_argument("--category", help="Filtruj po kategorii")
    p_list.add_argument("--tag", help="Filtruj po tagu")
    p_list.add_argument("--json", action="store_true", help="Format JSON")
    p_list.set_defaults(func=cmd_list)

    # search
    p_search = subparsers.add_parser("search", help="Wyszukaj skille po nazwie, opisie lub tagach")
    p_search.add_argument("query", help="Szukana fraza (np. faktury, nbp, paczkomat)")
    p_search.add_argument("--json", action="store_true", help="Format JSON")
    p_search.set_defaults(func=cmd_search)

    # info
    p_info = subparsers.add_parser("info", help="Szczegółowe metadane i kontrakt skilla")
    p_info.add_argument("skill", help="Nazwa skilla (np. biala-lista, inpost, nbp)")
    p_info.add_argument("--json", action="store_true", help="Format JSON")
    p_info.set_defaults(func=cmd_info)

    # install
    p_install = subparsers.add_parser("install", help="Zainstaluj skille w środowisku agenta AI")
    p_install.add_argument("skills", nargs="*", help="Nazwy skilli (domyślnie: wszystkie)")
    p_install.add_argument("--dir", "-d", help="Katalog docelowy")
    p_install.add_argument("--global", "-g", dest="global_install", action="store_true", help="Instalacja globalna (~/.gemini/config/skills)")
    p_install.add_argument("--claude", "-c", action="store_true", help="Instalacja dla Claude Code (.claude/skills)")
    p_install.add_argument("--antigravity", "-a", action="store_true", help="Instalacja dla Antigravity/Cursor (.agents/skills)")
    p_install.set_defaults(func=cmd_install)

    # update
    p_update = subparsers.add_parser("update", help="Zaktualizuj zainstalowane skille")
    p_update.add_argument("--dir", "-d", help="Katalog docelowy")
    p_update.add_argument("--global", "-g", dest="global_install", action="store_true", help="Instalacja globalna")
    p_update.add_argument("--claude", "-c", action="store_true", help="Instalacja dla Claude Code")
    p_update.add_argument("--antigravity", "-a", action="store_true", help="Instalacja dla Antigravity/Cursor")
    p_update.set_defaults(func=cmd_update)

    # validate
    p_val = subparsers.add_parser("validate", help="Uruchom walidator rejestru")
    p_val.set_defaults(func=cmd_validate)

    # test
    p_test = subparsers.add_parser("test", help="Uruchom test harness kontraktu")
    p_test.set_defaults(func=cmd_test)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
