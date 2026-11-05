#!/usr/bin/env python3
"""Comprehensive validator for ai-polish-skills.

Validates:
1. YAML frontmatter schema & required fields (single source of truth).
2. Naming conventions (kebab-case, directory match, uniqueness).
3. Semver versioning (X.Y.Z).
4. Required files and paths (SKILL.md, scripts/<name>.py).
5. Python syntax integrity via AST parsing.
6. CLI contract: --help exits with code 0.
7. Secret leak scanning (AWS, GitHub, OpenAI, private keys).
8. Markdown relative link integrity.

Zero external dependencies (Python 3.8+ standard library only).
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from manifest import load_skill_manifest, validate_manifest

SKILLS_DIR = ROOT_DIR / "skills"
MAX_LINES = 500

# Secret leak patterns
SECRET_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{82}"), "GitHub Fine-Grained Token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "OpenAI API Key"),
    (re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY"), "Private Key"),
    (re.compile(r"(?:api[_-]?key|secret[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}['\"]", re.IGNORECASE), "Generic hardcoded API Secret"),
]

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def check_secrets(skill_dir: Path) -> List[str]:
    """Scan all files in skill_dir for potential leaked secrets."""
    errors = []
    for path in skill_dir.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, desc in SECRET_PATTERNS:
            if pattern.search(content):
                rel_path = path.relative_to(ROOT_DIR)
                errors.append(f"potential secret detected in {rel_path} ({desc})")
    return errors


def check_markdown_links(skill_md: Path, skill_dir: Path) -> List[str]:
    """Verify that all relative local markdown links point to existing files."""
    errors = []
    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        return [f"failed to read {skill_md.name}: {e}"]

    for match in MARKDOWN_LINK_RE.finditer(content):
        link_target = match.group(2).strip()
        # Ignore external links, mailto, and anchors
        if link_target.startswith(("http://", "https://", "mailto:", "#", "file://", "conversation://")):
            continue

        # Strip optional anchor
        target_path_str = link_target.split("#", 1)[0].strip()
        if not target_path_str:
            continue

        target_path = (skill_dir / target_path_str).resolve()
        if not target_path.exists():
            errors.append(f"broken markdown link in SKILL.md: '{link_target}' (file not found)")
    return errors


def check_python_syntax(skill_dir: Path) -> Tuple[List[str], List[Path]]:
    """Parse all .py files in scripts/ to ensure valid Python syntax."""
    errors = []
    py_files = []
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return [f"missing 'scripts/' directory in {skill_dir.name}"], py_files

    for py_file in sorted(scripts_dir.glob("*.py")):
        py_files.append(py_file)
        try:
            content = py_file.read_text(encoding="utf-8")
            ast.parse(content, filename=str(py_file))
        except SyntaxError as e:
            rel = py_file.relative_to(ROOT_DIR)
            errors.append(f"syntax error in {rel} line {e.lineno}: {e.msg}")
        except Exception as e:
            rel = py_file.relative_to(ROOT_DIR)
            errors.append(f"cannot read/parse {rel}: {e}")

    if not py_files:
        errors.append(f"no Python scripts found in {skill_dir.name}/scripts/")

    return errors, py_files


def check_cli_contract(py_file: Path) -> List[str]:
    """Test --help exit code for primary CLI script."""
    errors = []
    rel = py_file.relative_to(ROOT_DIR)
    try:
        res = subprocess.run(
            [sys.executable, str(py_file), "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode != 0:
            errors.append(f"{rel} --help exited with non-zero code {res.returncode}: {res.stderr.strip()}")
        elif not res.stdout.strip():
            errors.append(f"{rel} --help returned empty stdout")
    except subprocess.TimeoutExpired:
        errors.append(f"{rel} --help timed out after 5s")
    except Exception as e:
        errors.append(f"failed to run {rel} --help: {e}")

    return errors


def validate_skill(skill_dir: Path) -> Tuple[List[str], List[str]]:
    """Validate a single skill directory."""
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Manifest
    manifest, load_errs = load_skill_manifest(skill_dir)
    if load_errs or manifest is None:
        return load_errs, warnings

    val_errs, val_warns = validate_manifest(manifest, skill_dir.name)
    errors.extend(val_errs)
    warnings.extend(val_warns)

    # 2. Markdown line count
    skill_md = skill_dir / "SKILL.md"
    try:
        lines = skill_md.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_LINES:
            warnings.append(f"SKILL.md has {len(lines)} lines (exceeds recommended {MAX_LINES}); consider references/")
    except Exception:
        pass

    # 3. Markdown links
    link_errs = check_markdown_links(skill_md, skill_dir)
    errors.extend(link_errs)

    # 4. Python scripts & syntax
    syntax_errs, py_files = check_python_syntax(skill_dir)
    errors.extend(syntax_errs)

    # 5. CLI contract (--help)
    if py_files:
        # Test the main entrypoint
        primary = None
        expected_name = skill_dir.name.replace("-", "_") + ".py"
        for pf in py_files:
            if pf.name == expected_name or pf.name == f"{skill_dir.name}.py":
                primary = pf
                break
        if not primary:
            primary = py_files[0]

        help_errs = check_cli_contract(primary)
        errors.extend(help_errs)

    # 6. Secrets scan
    secret_errs = check_secrets(skill_dir)
    errors.extend(secret_errs)

    return errors, warnings


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"ERROR: Skills directory not found at {SKILLS_DIR}", file=sys.stderr)
        return 1

    skill_dirs = sorted(
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    )

    if not skill_dirs:
        print("ERROR: No skills found in skills/ directory", file=sys.stderr)
        return 1

    # Check for duplicates or collisions
    seen_names: Set[str] = set()
    total_errors = 0
    total_warnings = 0

    print("═══════════════════════════════════════════════════════════════")
    print(" ai-polish-skills Validator")
    print("═══════════════════════════════════════════════════════════════")

    for sdir in skill_dirs:
        if sdir.name in seen_names:
            print(f"ERROR: Duplicate skill name detected: {sdir.name}")
            total_errors += 1
            continue
        seen_names.add(sdir.name)

        errors, warnings = validate_skill(sdir)
        total_errors += len(errors)
        total_warnings += len(warnings)

        if not errors and not warnings:
            print(f"  ✓ {sdir.name} (OK)")
        elif not errors:
            print(f"  ⚠ {sdir.name} (OK with warnings)")
            for w in warnings:
                print(f"      WARN: {w}")
        else:
            print(f"  ✗ {sdir.name} (FAILED)")
            for e in errors:
                print(f"      ERROR: {e}")
            for w in warnings:
                print(f"      WARN:  {w}")

    print("───────────────────────────────────────────────────────────────")
    print(f"Summary: {len(skill_dirs)} skill(s) evaluated. Errors: {total_errors}, Warnings: {total_warnings}")

    if total_errors > 0:
        print("Result: FAILED", file=sys.stderr)
        return 1

    print("Result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
