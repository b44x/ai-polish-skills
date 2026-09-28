#!/usr/bin/env python3
"""Shared manifest parser and schema definitions for ai-polish-skills.

Zero external dependencies (Python 3.8+ standard library only).
Acts as the single source of truth for parsing and validating SKILL.md frontmatters.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ALLOWED_CATEGORIES = {
    "finance",
    "logistics",
    "legal",
    "entertainment",
    "public_data",
    "utilities",
    "e-commerce",
    "health",
    "general",
}

ALLOWED_SOURCE_TYPES = {
    "official_api",
    "public_api",
    "unofficial_api",
    "scraping",
    "static_data",
}

ALLOWED_AUTHENTICATIONS = {
    "none",
    "api_key",
    "oauth",
    "credentials",
}

REQUIRED_FIELDS = [
    "name",
    "display_name",
    "version",
    "description",
    "category",
    "language",
    "country",
    "license",
    "network",
    "authentication",
    "source",
    "source_type",
    "official",
    "homepage",
    "documentation",
    "tags",
]


def parse_frontmatter(text: str) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter enclosed in --- delimiters from SKILL.md.
    
    Handles scalars, booleans, folded/literal multiline strings, and simple lists.
    No PyYAML dependency.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None

    header = text[3:end].strip("\r\n")
    data: Dict[str, Any] = {}
    current_key: Optional[str] = None
    multiline_mode: Optional[str] = None
    list_items: List[str] = []
    text_buffer: List[str] = []

    def flush_current():
        nonlocal current_key, multiline_mode, list_items, text_buffer
        if current_key is None:
            return
        if multiline_mode in ("folded", "literal"):
            val = "\n".join(text_buffer).strip()
            if multiline_mode == "folded":
                val = re.sub(r"\s+", " ", val)
            data[current_key] = val
        elif multiline_mode == "list":
            data[current_key] = list(list_items)
        text_buffer = []
        list_items = []
        multiline_mode = None

    for raw_line in header.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if key_match and not line.startswith((" ", "\t")):
            flush_current()
            current_key = key_match.group(1)
            raw_val = key_match.group(2).strip()

            # Strip inline comment outside quotes
            if " #" in raw_val and not (raw_val.startswith('"') or raw_val.startswith("'")):
                raw_val = raw_val.split(" #", 1)[0].strip()

            if raw_val in (">", ">-"):
                multiline_mode = "folded"
            elif raw_val in ("|", "|-"):
                multiline_mode = "literal"
            elif raw_val == "":
                multiline_mode = None
            elif raw_val.lower() == "true":
                data[current_key] = True
                current_key = None
            elif raw_val.lower() == "false":
                data[current_key] = False
                current_key = None
            else:
                data[current_key] = raw_val.strip("\"'")
                current_key = None
            continue

        if current_key:
            stripped = line.strip()
            if stripped.startswith("- "):
                multiline_mode = "list"
                item_val = stripped[2:].strip().strip("\"'")
                list_items.append(item_val)
            else:
                if multiline_mode is None:
                    multiline_mode = "folded"
                text_buffer.append(stripped)

    flush_current()
    return data


def load_skill_manifest(skill_dir: Path) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Load and parse SKILL.md from a skill directory. Returns (manifest, errors)."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None, ["missing SKILL.md"]

    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        return None, [f"failed to read SKILL.md: {e}"]

    manifest = parse_frontmatter(content)
    if manifest is None:
        return None, ["missing or malformed YAML frontmatter (must start with ---)"]

    return manifest, []


def validate_manifest(manifest: Dict[str, Any], skill_name: str) -> Tuple[List[str], List[str]]:
    """Validate manifest dictionary against the official skill specification.
    
    Returns (errors, warnings).
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in manifest:
            errors.append(f"missing required field: '{field}'")
        elif manifest[field] is None or (isinstance(manifest[field], str) and not manifest[field].strip()):
            errors.append(f"field '{field}' cannot be empty")

    name = manifest.get("name", "")
    if name:
        if name != skill_name:
            errors.append(f"name '{name}' does not match directory '{skill_name}'")
        if not NAME_RE.match(name) or len(name) > 64:
            errors.append(f"name '{name}' must be kebab-case and <= 64 chars")

    version = manifest.get("version", "")
    if version:
        if not SEMVER_RE.match(str(version)):
            errors.append(f"version '{version}' is not valid semantic versioning (X.Y.Z)")

    category = manifest.get("category", "")
    if category and category not in ALLOWED_CATEGORIES:
        errors.append(f"invalid category '{category}', must be one of: {sorted(ALLOWED_CATEGORIES)}")

    source_type = manifest.get("source_type", "")
    if source_type and source_type not in ALLOWED_SOURCE_TYPES:
        errors.append(f"invalid source_type '{source_type}', must be one of: {sorted(ALLOWED_SOURCE_TYPES)}")

    authentication = manifest.get("authentication", "")
    if authentication and authentication not in ALLOWED_AUTHENTICATIONS:
        errors.append(f"invalid authentication '{authentication}', must be one of: {sorted(ALLOWED_AUTHENTICATIONS)}")

    network = manifest.get("network")
    if network is not None and not isinstance(network, bool):
        errors.append(f"network must be a boolean (true/false), got {type(network).__name__}")

    official = manifest.get("official")
    if official is not None and not isinstance(official, bool):
        errors.append(f"official must be a boolean (true/false), got {type(official).__name__}")

    tags = manifest.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            errors.append("tags must be a list of strings")
        elif len(tags) == 0:
            errors.append("tags list cannot be empty")
        else:
            for t in tags:
                if not isinstance(t, str) or not t.strip():
                    errors.append(f"invalid tag '{t}': must be non-empty string")

    homepage = manifest.get("homepage", "")
    if homepage and not (homepage.startswith("http://") or homepage.startswith("https://")):
        errors.append(f"homepage must be a valid http(s) URL: '{homepage}'")

    last_verified = manifest.get("last_verified")
    if last_verified and not DATE_RE.match(str(last_verified)):
        errors.append(f"last_verified must follow YYYY-MM-DD format, got '{last_verified}'")

    description = manifest.get("description", "")
    if description and len(description) > 1024:
        warnings.append(f"description is quite long ({len(description)} chars, recommend <= 1024)")

    return errors, warnings
