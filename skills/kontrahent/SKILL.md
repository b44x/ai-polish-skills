---
name: kontrahent
display_name: Kontrahent przed przelewem — VAT, KRS i rachunek
version: 1.0.0
description: >-
  Cross-check a Polish contractor by NIP using the VAT White List and the current KRS extract. Optionally verify the NIP and bank account pair for a specified date. Use for "sprawdź kontrahenta przed przelewem", "czy NIP zgadza się z KRS", or "czy rachunek jest na białej liście".
category: finance
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: Ministerstwo Finansów (KAS) / Ministerstwo Sprawiedliwości
source_type: official_api
official: true
homepage: https://polskieskille.pl
documentation: https://www.gov.pl/web/kas/api-wykazu-podatnikow-vat
rate_limit: One MF search and optional account check per call; see MF documentation.
last_verified: 2026-11-18
tags:
  - kontrahent
  - przelew
  - nip
  - krs
  - vat
compatibility: Python 3.8+ (standard library only).
---

# Contractor register check

From the skill directory run `python3 scripts/kontrahent.py check 7342867148 --date 2026-11-18` (`py` on Windows). Use the user's intended VAT reference date. Add `--krs NUMBER` when an invoice or contract lists its own KRS number, and `--account NRB` only when the user asks to verify the account. The account is sent to the official MF endpoint and only its last four digits appear in the result.

1. Report the VAT status and date from `vat` with the MF request ID. Keep `not_found` separate from the explicit VAT status `Niezarejestrowany`. The script uses the KRS number returned by MF when none is supplied.
2. The KRS extract is current even for a historical VAT date. Report its own extraction and entry dates, preserve the exact representation text if present, and distinguish `no_krs_number` from a confirmed `not_found`. A business can exist outside KRS. For a known register, pass `--registry P` (companies) or `--registry S` (associations/foundations). The default tries S only after an official P response of HTTP 404.
3. Report each comparison separately. `false` means an identifier mismatch. `null` means a comparison could not be made. `accountAssigned` is the literal MF answer for the requested date. An unavailable check stays unavailable.
4. A consistent report does not establish payment safety, creditworthiness or authority of a particular signatory. Keep each result attributed to [MF / KAS](https://www.gov.pl/web/kas/api-wykazu-podatnikow-vat) or [KRS](https://prs.ms.gov.pl/krs/openApi).

Output is JSON on stdout with exit 0 when VAT lookup succeeds, including an explicit no-match or incomplete optional checks. Invalid input exits 64 and failure of the initial VAT lookup exits 69, with JSON on stderr. No automatic retries or persistent cache.
