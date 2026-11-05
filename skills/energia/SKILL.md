---
name: energia
display_name: Energia — ceny RCE z PSE
version: 1.0.0
description: >-
  Read official Polish PSE market electricity prices (RCE), find the cheapest continuous consumption window and summarize historical prices. Use for "ceny RCE", "ceny energii PSE", "najtańsze godziny prądu" or "kiedy ładować przy cenach rynkowych". Reports complete and missing intervals; retail tariffs depend on the user's contract.
category: finance
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: Polskie Sieci Elektroenergetyczne (PSE)
source_type: official_api
official: true
homepage: https://www.pse.pl/
documentation: https://api.raporty.pse.pl/
rate_limit: fair use; local cache 5 minutes; maximum 31 days per query
last_verified: 2026-11-05
tags:
  - energia
  - rce
  - pse
  - prad
  - ceny-energii
  - ladowanie
compatibility: Python 3.8+ (standard library only); internet access required.
---

# Ceny rynkowe energii z PSE

Uruchamiaj z katalogu skilla: `python3 scripts/energia.py <komenda> ...` (Windows: `py`). Bez klucza API i pakietów pip.

| Komenda | Wynik |
|---|---|
| `day 2026-11-04` | Ceny każdego przedziału, minimum, maksimum, średnia dostępnych danych i kompletność doby |
| `cheapest 2026-11-04 --minutes 120` | Najtańsze ciągłe dwie godziny w pełnej dobie, ze startem na granicy przedziału PSE |
| `cheapest 2026-11-04 --minutes 180 --kwh 12` | Także składnik RCE dla 12 kWh pobieranych przy stałej mocy przez trzy godziny |
| `summary --from 2026-11-01 --to 2026-11-04` | Podsumowanie maksymalnie 31 dni, brakujące daty i kompletność poszczególnych dób |

`day` i `cheapest` bez daty wybierają dzisiejszą datę w Polsce. Każda komenda obsługuje `--no-cache` oraz `--cache-dir <katalog>`. Cache jest aktualny przez 5 minut; błąd odświeżenia kończy odczyt błędem.

## Interpretacja

- Podawaj źródło **PSE**, datę, cenę w PLN/MWh lub PLN/kWh oraz czas publikacji. 1000 PLN/MWh = 1 PLN/kWh. To rynkowe RCE; rachunek zależy od umowy i zawiera dodatkowe składniki. Ujemna RCE nie gwarantuje ujemnego rachunku. Nie dodawaj samodzielnie założonej stawki VAT ani nie obiecuj oszczędności na konkretnej taryfie.
- O wyborze daty decyduje użytkownik; danych dla jutra może jeszcze nie być. Brak danych to błąd `not_found`, a nie prognoza lub cena zero.
- `complete: false` oznacza niepełny zakres. `mean_available_pln_mwh` opisuje wyłącznie opublikowane przedziały; w podsumowaniu `mean_full_period_pln_mwh` pozostaje wtedy `null`. `cheapest` wymaga pełnej doby, aby porównać wszystkie możliwe okna.
- Każdy przedział ma granice UTC oraz lokalne ISO z przesunięciem UTC. Używaj ich przy zmianie czasu — doba może mieć 23, 24 lub 25 godzin, a lokalna godzina może się powtarzać.
- `--minutes` oznacza rzeczywisty czas trwania, nie różnicę między wskazaniami zegara. Ostatni przedział może zostać wykorzystany częściowo, proporcjonalnie do czasu; pozwala to wybrać np. 90 minut także dla historycznych cen godzinowych. Przy `--kwh` zakładana jest stała moc poboru. Wynik `rce_component_pln` jest wyłącznie składnikiem RCE. Skill nie steruje ładowarką ani urządzeniami.

Sukces: JSON stdout, kod `0`. Błędy JSON stderr: `2` brak danych/okna, `64` walidacja, `69` API/sieć/niepełna doba przy wyszukiwaniu okna. `--help`/`-h`: kod `0`.

Szczegóły pól i źródła: [references/api.md](references/api.md).
