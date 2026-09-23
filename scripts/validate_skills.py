#!/usr/bin/env python3
"""Validate skills/<name>/SKILL.md files. Directories starting with '_' are skipped."""

import re
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_LINES = 500


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fields, key = {}, None
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            fields[key] = "" if value in (">", ">-", "|", "|-") else value.strip("\"'")
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def validate(skill_dir):
    errors, warnings = [], []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return ["missing SKILL.md"], warnings

    text = skill_md.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    if fields is None:
        return ["missing or malformed YAML frontmatter"], warnings

    name = fields.get("name", "")
    description = fields.get("description", "")
    if not name:
        errors.append("frontmatter: 'name' is required")
    elif name != skill_dir.name:
        errors.append(f"frontmatter: name '{name}' must match directory '{skill_dir.name}'")
    elif not NAME_RE.match(name) or len(name) > MAX_NAME:
        errors.append(f"frontmatter: name must be kebab-case, max {MAX_NAME} chars")
    if not description:
        errors.append("frontmatter: 'description' is required")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"frontmatter: description exceeds {MAX_DESCRIPTION} chars")

    if len(text.splitlines()) > MAX_LINES:
        warnings.append(f"SKILL.md has more than {MAX_LINES} lines; move details to references/")
    return errors, warnings


def main():
    skill_dirs = sorted(
        d for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))
    )
    failed = False
    for skill_dir in skill_dirs:
        errors, warnings = validate(skill_dir)
        for w in warnings:
            print(f"WARN  {skill_dir.name}: {w}")
        for e in errors:
            print(f"ERROR {skill_dir.name}: {e}")
        failed = failed or bool(errors)
    print(f"Checked {len(skill_dirs)} skill(s): {'FAILED' if failed else 'OK'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
