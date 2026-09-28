#!/usr/bin/env python3
"""Build and verify static registry/registry.json from skills/*/SKILL.md.

Standard library only.
Generates:
- registry/registry.json (formatted)
- registry/registry.min.json (compact)

Usage:
  python3 scripts/build_registry.py
  python3 scripts/build_registry.py --check
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

# Ensure scripts/ directory is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from manifest import load_skill_manifest, validate_manifest


def build_registry_data(skills_dir: Path) -> Dict[str, Any]:
    """Inspect all skills and build deterministic registry dictionary."""
    skill_dirs = sorted(
        d for d in skills_dir.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    )

    skills_list: List[Dict[str, Any]] = []
    category_counter = Counter()

    for sdir in skill_dirs:
        manifest, errs = load_skill_manifest(sdir)
        if errs or manifest is None:
            print(f"ERROR: Cannot load manifest for {sdir.name}: {errs}", file=sys.stderr)
            sys.exit(1)

        val_errs, _ = validate_manifest(manifest, sdir.name)
        if val_errs:
            print(f"ERROR: Invalid manifest for {sdir.name}: {val_errs}", file=sys.stderr)
            sys.exit(1)

        # Collect files relative to skill directory
        files: List[str] = sorted(
            str(p.relative_to(sdir))
            for p in sdir.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        )

        entrypoint = None
        expected_script = sdir / "scripts" / f"{sdir.name.replace('-', '_')}.py"
        alt_script = sdir / "scripts" / f"{sdir.name}.py"
        if expected_script.is_file():
            entrypoint = str(expected_script.relative_to(sdir))
        elif alt_script.is_file():
            entrypoint = str(alt_script.relative_to(sdir))
        else:
            py_scripts = sorted(sdir.glob("scripts/*.py"))
            if py_scripts:
                entrypoint = str(py_scripts[0].relative_to(sdir))

        skill_data = dict(manifest)
        if entrypoint:
            skill_data["entrypoint"] = entrypoint
        skill_data["files"] = files

        skills_list.append(skill_data)
        category_counter[manifest.get("category", "general")] += 1

    categories = [
        {"name": cat, "count": count}
        for cat, count in sorted(category_counter.items(), key=lambda x: (-x[1], x[0]))
    ]

    registry_obj = {
        "schema_version": "1.0.0",
        "name": "ai-polish-skills",
        "description": "Oficjalny rejestr polskich skilli dla agentów AI (Claude Code, Cursor, Windsurf, Antigravity)",
        "homepage": "https://polskieskille.pl",
        "repository": "https://github.com/b44x/ai-polish-skills",
        "skills_count": len(skills_list),
        "categories": categories,
        "skills": skills_list,
    }
    return registry_obj


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or check registry.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if registry.json is up-to-date with skills/ without modifying it",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "registry",
        help="Target directory for registry files (default: registry/)",
    )
    args = parser.parse_args()

    skills_dir = ROOT_DIR / "skills"
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    target_json = output_dir / "registry.json"
    target_min = output_dir / "registry.min.json"

    registry_data = build_registry_data(skills_dir)
    generated_pretty = json.dumps(registry_data, indent=2, ensure_ascii=False) + "\n"
    generated_min = json.dumps(registry_data, separators=(",", ":"), ensure_ascii=False) + "\n"

    if args.check:
        if not target_json.is_file():
            print(f"FAIL: {target_json} does not exist. Run 'python3 scripts/build_registry.py' to generate.", file=sys.stderr)
            return 1
        current_content = target_json.read_text(encoding="utf-8")
        if current_content != generated_pretty:
            print(f"FAIL: {target_json} is out of date. Run 'python3 scripts/build_registry.py' and commit.", file=sys.stderr)
            return 1
        print("OK: registry.json is up to date.")
        return 0

    target_json.write_text(generated_pretty, encoding="utf-8")
    target_min.write_text(generated_min, encoding="utf-8")

    print(f"Successfully generated registry with {registry_data['skills_count']} skills:")
    for skill in registry_data["skills"]:
        print(f"  • {skill['name']} (v{skill['version']}) [{skill['category']}] - {skill['display_name']}")
    print(f"\nWrote:\n  ➔ {target_json}\n  ➔ {target_min}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
