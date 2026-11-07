---
name: _template
display_name: Example Polish Skill Name
version: 1.0.0
description: >-
  Describe WHAT the skill does and WHEN to use it in concise English.
  Include representative Polish trigger phrases, e.g. "sprawdź ...".
  Add a scope boundary only when it prevents likely misuse.
category: utilities # Allowed: finance, logistics, legal, entertainment, public_data, utilities, e-commerce, health
language: pl # Target locale, not the language of agent instructions
country: PL
license: MIT
author: Your Name (https://github.com/your-username)
repository: https://github.com/b44x/ai-polish-skills
network: true # true if script makes HTTP/network calls, false if offline only
authentication: none # none, api_key, oauth, or credentials
source: Official Service or Provider Name
source_type: official_api # Allowed: official_api, public_api, unofficial_api, scraping, static_data
official: false # true if provided directly by the public institution or company
homepage: https://example.gov.pl
documentation: https://example.gov.pl/api/docs
rate_limit: fair use # e.g. "300 req/day", "10 req/s", "fair use", or "none"
last_verified: 2026-09-28 # YYYY-MM-DD
tags:
  - przyklad
  - usługa
compatibility: Python 3.8+ (standard library only).
---

# Skill name

Briefly explain what this skill does. Write agent-facing guidance and headings in English.
Keep Polish user examples, official names and source text in their original language.
Answer users in the language of their request; preserve CLI identifiers and JSON keys.

## When to use

- situation 1
- situation 2

## When NOT to use

- a situation that looks similar but needs something else

## Running the script

Run from this skill's directory with `python3 scripts/<script>.py <command>`
(`py` on Windows). Replace placeholders with actual supported commands.

## Workflow

1. First step.
2. Second step.
3. For details see [references/details.md](references/details.md).

## Output format

Describe the important output fields, units, timestamps and missing-data semantics.
State source attribution, coverage limits and applicable exit codes. Do not duplicate
large schemas here; link to the maintained reference when needed.

## Examples

**Input:** ...

**Output:** ...
