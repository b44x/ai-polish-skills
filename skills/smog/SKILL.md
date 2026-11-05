---
name: smog
display_name: Smog — jakość powietrza GIOŚ
version: 1.0.0
description: >-
  Read official GIOŚ air quality measurements and the Polish air quality index. Find stations by city or the nearest station by GPS. Use for "smog", "jakość powietrza", "PM2.5", "PM10", "najbliższa stacja GIOŚ". Shows measurement times and missing data; does not provide forecasts or medical advice.
category: public_data
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: Główny Inspektorat Ochrony Środowiska (GIOŚ)
source_type: official_api
official: true
homepage: https://powietrze.gios.gov.pl/
documentation: https://powietrze.gios.gov.pl/pjp/content/api
rate_limit: Endpoint-specific limits; see GIOŚ documentation
last_verified: 2026-11-04
tags:
  - smog
  - powietrze
  - pm10
  - pm25
  - gios
  - jakosc-powietrza
compatibility: Python 3.8+ (standard library only); internet access required.
---

# Jakość powietrza z GIOŚ

## Uruchomienie

| System | Komenda z katalogu skilla |
|---|---|
| Linux / macOS | `python3 scripts/smog.py <komenda> ...` |
| Windows | `py scripts/smog.py <komenda> ...` |

| Komenda | Działanie |
|---|---|
| `stations --city Kraków` | Wszystkie stacje w mieście; działa też zapis `Krakow` |
| `stations` | Katalog stacji GIOŚ |
| `near 50.06 19.94` | Najbliższa stacja, odległość w linii prostej, indeks i pomiary |
| `station 400` | Indeks i ostatnie dostępne pomiary wskazanej stacji |

## Dobór stacji i odpowiedź

1. Dla miasta najpierw wywołaj `stations --city`. Przy wielu stacjach przedstaw wybór; nie przedstawiaj jednej stacji jako średniej dla całego miasta. Dla podanych współrzędnych użyj `near`.
2. Podaj nazwę stacji, źródło **GIOŚ**, wartość, jednostkę i czas pomiaru dla każdego zanieczyszczenia. Wszystkie stężenia z tego API, także CO, są w µg/m³. Czasy pomiarów i indeksu to lokalny czas Europe/Warsaw; `fetched_at` jest UTC.
3. `latest_slot_missing` oznacza, że ostatni przedział nie ma pomiaru, a wynik pochodzi z wcześniejszego przedziału. `no_current_data` i `null` to brak danych, nigdy zero. Pomiary różnych czujników mogą pochodzić z różnych godzin.
4. Pokazuj kategorię indeksu podaną przez GIOŚ; nie obliczaj własnego indeksu ani nie podmieniaj go na amerykański AQI. Uwzględnij brak lub niepełny status indeksu. Dane są wstępne i mogą być później korygowane.
5. Skill nie obejmuje prognoz, porad zdrowotnych ani uruchamiania stałego monitoringu. Najbliższa stacja nie musi odzwierciedlać warunków pod dokładnym adresem użytkownika.

## Kontrakt i API

Aktualne API: `https://api.gios.gov.pl/pjp-api/v1/rest/`. Obsługiwane jest stronicowanie JSON-LD, bez zależności pip i kluczy API. Nie używaj wycofanego `/pjp-api/rest/`.

Sukces: JSON na stdout, kod `0`. Błędy JSON na stderr: `2` — brak stacji, `64` — walidacja, `69` — API/sieć. Brak pomiarów istniejącej stacji to poprawny wynik z polami `null`. Błąd sieci przy pobieraniu czujnika przerywa odczyt, nie udaje braku pomiaru. `--help` i `-h`: kod `0`.

Szczegóły: [references/output.md](references/output.md). [Dokumentacja GIOŚ](https://powietrze.gios.gov.pl/pjp/content/api).
