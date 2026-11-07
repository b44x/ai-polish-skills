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
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from manifest import load_skill_manifest
from installer import InstallError, install, target_directory

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
    print(f"{DIM}Available Polish AI skills ({len(skills)} in registry):{RESET}\n")

    for name, s in skills.items():
        if getattr(args, "category", None) and s.get("category") != args.category:
            continue
        if getattr(args, "tag", None) and args.tag not in s.get("tags", []):
            continue

        category = f"[{s.get('category', 'general')}]"
        version = f"v{s.get('version', '1.0.0')}"
        display = s.get("display_name", name)
        network = "network" if s.get("network") else "offline"
        official = "official source" if s.get("official") else f"🔗 {s.get('source_type', 'api')}"

        print(f"  {BOLD}{name:<14}{RESET} {GREEN}{version:<8}{RESET} {CYAN}{category:<15}{RESET} {display}")
        print(f"    {DIM}Source: {s.get('source')} ({official}) • {network} • auth: {s.get('authentication')}{RESET}")
        desc = s.get("description", "")
        short_desc = desc[:110] + ("..." if len(desc) > 110 else "")
        print(f"    {desc_line(short_desc)}\n")

    return 0


def desc_line(text: str) -> str:
    return f"{DIM}{text}{RESET}"


def score_skill(query: str, skill_name: str, s: Dict[str, Any]) -> int:
    """Calculate relevance score for a skill based on query tokens, stems, and fields."""
    query_clean = re.sub(r"[^\w\s-]", " ", query.lower()).strip()
    if not query_clean:
        return 0

    tokens = [w for w in query_clean.split() if len(w) > 1]
    if not tokens:
        return 0

    stems = [t[:4] if len(t) >= 4 else t for t in tokens]

    name = skill_name.lower()
    display = s.get("display_name", "").lower()
    category = s.get("category", "").lower()
    tags = [t.lower() for t in s.get("tags", [])]
    desc = s.get("description", "").lower()
    source = s.get("source", "").lower()

    score = 0

    # Exact full match
    if query_clean == name or query_clean in name:
        score += 100
    if query_clean in display:
        score += 50
    if any(query_clean in t for t in tags):
        score += 50
    if query_clean in desc:
        score += 40

    # Token and stem matching
    for token, stem in zip(tokens, stems):
        # Match against name
        if token == name:
            score += 80
        elif token in name or stem in name:
            score += 35

        # Match against tags
        for t in tags:
            if token == t:
                score += 50
            elif token in t or stem in t:
                score += 25

        # Match against display name
        if token in display:
            score += 30
        elif stem in display:
            score += 15

        # Match against category
        if token in category:
            score += 25

        # Match against source
        if token in source or stem in source:
            score += 15

        # Match against description
        if token in desc:
            score += 15
        elif stem in desc:
            score += 8

    return score


def cmd_search(args: argparse.Namespace) -> int:
    query = args.query.strip()
    skills = get_all_skills()
    matches = {}

    for name, s in skills.items():
        score = score_skill(query, name, s)
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
        print(f"\nNo skills match: {BOLD}'{query}'{RESET}")
        print("Run 'python3 scripts/cli.py list' to see available skills.\n")
        return 0

    print(f"\nFound {len(sorted_matches)} skill(s) matching {BOLD}'{query}'{RESET}:\n")
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
        raise InstallError(f"Skill '{skill_name}' was not found in the registry.", 2)

    s = skills[skill_name]

    if getattr(args, "json", False):
        clean = {k: v for k, v in s.items() if not k.startswith("_")}
        print(json.dumps(clean, indent=2, ensure_ascii=False))
        return 0

    print(f"\n{BOLD}═══════════════════════════════════════════════════════════════{RESET}")
    print(f" {BOLD}{s.get('display_name', skill_name)} ({skill_name}){RESET}")
    print(f"{BOLD}═══════════════════════════════════════════════════════════════{RESET}\n")

    print(f"  {BOLD}Version:{RESET}         {s.get('version')}")
    print(f"  {BOLD}Category:{RESET}      {s.get('category')}")
    print(f"  {BOLD}License:{RESET}       {s.get('license')}")
    print(f"  {BOLD}Author:{RESET}          {s.get('author', 'Michell Hoduń')}")
    print(f"  {BOLD}Network:{RESET}   {'Yes (Internet access)' if s.get('network') else 'No (offline)'}")
    print(f"  {BOLD}Authentication:{RESET} {s.get('authentication')}")
    print(f"  {BOLD}Data source:{RESET}  {s.get('source')} ({s.get('source_type')})")
    print(f"  {BOLD}Official source:{RESET}  {'Yes' if s.get('official') else 'No'}")
    print(f"  {BOLD}Homepage:{RESET}     {s.get('homepage')}")
    print(f"  {BOLD}Documentation:{RESET}   {s.get('documentation')}")
    print(f"  {BOLD}Rate limit:{RESET}  {s.get('rate_limit', 'fair use')}")
    print(f"  {BOLD}Last verified:{RESET}    {s.get('last_verified', 'unknown')}")
    print(f"  {BOLD}Tags:{RESET}           {', '.join(s.get('tags', []))}")
    print(f"  {BOLD}Compatibility:{RESET} {s.get('compatibility', 'Python 3.8+')}")

    print(f"\n{BOLD}Description:{RESET}")
    print(f"  {s.get('description')}\n")

    skill_path = Path(s["_dir"])
    skill_md = skill_path / "SKILL.md"
    if skill_md.is_file():
        print(f"{BOLD}SKILL.md instructions:{RESET}")
        print(f"  ➔ {skill_md.resolve()}\n")

    return 0


def cmd_install(args: argparse.Namespace) -> int:
    result = install(get_all_skills(), getattr(args, "skills", []),
                     target_directory(args), args.dry_run,
                     update=args.subcommand == "update")
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        verb = "Would install" if args.dry_run else "Installed"
        print(f"{verb} {len(result['skills'])} skill(s) in {result['target']}")
        for name in result["skills"]:
            print(f"  {name}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    script = SCRIPT_DIR / "validate_skills.py"
    res = subprocess.run([sys.executable, str(script)])
    return res.returncode


def cmd_test(args: argparse.Namespace) -> int:
    script = SCRIPT_DIR / "test_skills.py"
    res = subprocess.run([sys.executable, str(script)])
    return res.returncode


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InstallError(message, 64)


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(
        prog="ai-polish-skills",
        description="Manage Polish AI skills from polskieskille.pl (Python 3.8+).",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # list
    p_list = subparsers.add_parser("list", aliases=["ls"], help="List available skills")
    p_list.add_argument("--category", help="Filter by category")
    p_list.add_argument("--tag", help="Filter by tag")
    p_list.add_argument("--json", action="store_true", help="Output JSON")
    p_list.set_defaults(func=cmd_list)

    # search
    p_search = subparsers.add_parser("search", aliases=["find"], help="Search names, descriptions and tags")
    p_search.add_argument("query", help="Search query (e.g. faktury, nbp, paczkomat)")
    p_search.add_argument("--json", action="store_true", help="Output JSON")
    p_search.set_defaults(func=cmd_search)

    # info
    p_info = subparsers.add_parser("info", aliases=["show"], help="Show skill metadata and contract")
    p_info.add_argument("skill", help="Skill name (e.g. biala-lista, inpost, nbp)")
    p_info.add_argument("--json", action="store_true", help="Output JSON")
    p_info.set_defaults(func=cmd_info)

    for command, help_text in (("install", "Install skills from this checkout"),
                               ("update", "Replace known installed skills from this checkout")):
        sub = subparsers.add_parser(command, help=help_text)
        if command == "install":
            sub.add_argument("skills", nargs="*", help="Skill names (default: all)")
        targets = sub.add_mutually_exclusive_group()
        targets.add_argument("--dir", "-d", help="Custom destination directory")
        targets.add_argument("--global", "-g", dest="global_install", action="store_true",
                             help="Legacy global target: ~/.gemini/config/skills")
        targets.add_argument("--claude", "-c", action="store_true",
                             help="Project target: .claude/skills")
        targets.add_argument("--agents", "--antigravity", "-a", dest="agents", action="store_true",
                             help="Project target: .agents/skills")
        sub.add_argument("--dry-run", action="store_true", help="Show changes without writing files")
        sub.add_argument("--json", action="store_true", help="Output one JSON result")
        sub.set_defaults(func=cmd_install)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate the skill registry")
    p_val.set_defaults(func=cmd_validate)

    # test
    p_test = subparsers.add_parser("test", help="Run the contract test suite")
    p_test.set_defaults(func=cmd_test)

    return parser


def main() -> int:
    # ANSI escapes are for interactive terminals only; honor NO_COLOR.
    if not sys.stdout.isatty() or "NO_COLOR" in os.environ:
        for name in ("BLUE", "GREEN", "YELLOW", "CYAN", "BOLD", "DIM", "RESET"):
            globals()[name] = ""
    try:
        args = build_parser().parse_args()
        return args.func(args)
    except InstallError as exc:
        print(json.dumps({"error": str(exc), "type": {2: "not_found", 64: "usage", 73: "filesystem"}.get(exc.code, "installation")}), file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(json.dumps({"error": str(exc), "type": "filesystem"}), file=sys.stderr)
        return 73



if __name__ == "__main__":
    sys.exit(main())
