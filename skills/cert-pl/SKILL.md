---
name: cert-pl
display_name: CERT Polska — podejrzane linki
version: 1.0.0
description: >-
  Check a domain or HTTP(S) URL against the active CERT Polska warning list, including matching subdomains. Use for "sprawdź link", "podejrzany SMS", "dopłata do paczki", "czy domena jest na liście CERT". Does not visit the submitted URL or certify that an unlisted site is safe.
category: utilities
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: CERT Polska (NASK-PIB)
source_type: official_api
official: true
homepage: https://cert.pl/lista-ostrzezen/
documentation: https://cert.pl/lista-ostrzezen/
rate_limit: "Local cache: 5 minutes; no published request quota"
last_verified: 2026-11-04
tags:
  - cert
  - phishing
  - oszustwa
  - podejrzane-linki
  - sms
  - bezpieczenstwo
compatibility: Python 3.8+ (standard library only); internet access required.
---

# Sprawdzanie linków w CERT Polska

## Uruchomienie

| System | Komenda z katalogu skilla |
|---|---|
| Linux / macOS | `python3 scripts/cert_pl.py check <domena-lub-url>` |
| Windows | `py scripts/cert_pl.py check <domena-lub-url>` |

Przykład: `python3 scripts/cert_pl.py check https://cert.pl/`.

## Interpretacja

- Przekaż domenę albo pełny adres HTTP(S). Skrypt lokalnie wyodrębnia nazwę hosta, normalizuje IDN i sprawdza listę CERT. Nie otwiera badanego adresu, nie sprawdza przekierowań i nie rozwija skróconych linków.
- `listed: true` oznacza wpis domeny lub jej domeny nadrzędnej na aktywnej liście. Cytuj `matched_domain` i `list_fetched_at`.
- `listed: false` oznacza wyłącznie brak wpisu. Zawsze powiedz, że nie potwierdza to bezpieczeństwa strony. Lista nie jest kompletnym wykazem zagrożeń.
- Nie przyjmuj adresów IP, danych logowania w URL ani innych protokołów. Nie przesyłaj treści SMS do zewnętrznych usług.
- Cache znajduje się w `$XDG_CACHE_HOME/ai-polish-skills/cert-pl/` albo `~/.cache/ai-polish-skills/cert-pl/`. Lista jest ważna do 5 minut. Przy nieudanym odświeżeniu zwracany jest błąd, bez użycia starej listy. Brak możliwości zapisu cache nie blokuje sprawdzenia online.

## Kontrakt

Sukces (również brak wpisu): JSON na stdout, kod `0`. Błędy: JSON na stderr z `error` i `type`, kod `64` (dane wejściowe) lub `69` (źródło/sieć). `--help` i `-h`: kod `0`.

Pola i przykład: [references/output.md](references/output.md).
Źródło i warunki ponownego użycia: [CERT Polska](https://cert.pl/lista-ostrzezen/).
