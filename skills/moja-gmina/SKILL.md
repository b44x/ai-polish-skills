---
name: moja-gmina
display_name: Moja gmina — statystyki GUS BDL
version: 1.0.0
description: >-
  Search official GUS BDL statistics and compare Polish municipalities, counties or voivodeships for a common year. Use for population, local demography, construction or unemployment comparisons, finding territorial units and statistical indicators. Preserves geographic levels, units of measure and missing-data attributes.
category: public_data
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: Główny Urząd Statystyczny — Bank Danych Lokalnych
source_type: official_api
official: true
homepage: https://bdl.stat.gov.pl/
documentation: https://api.stat.gov.pl/home/bdlapi
rate_limit: Anonymous 5 requests/s, 100/15 min, 1000/12 h, 10000/week; optional BDL_API_KEY increases limits.
last_verified: 2026-11-05
tags:
  - gus
  - bdl
  - gmina
  - powiat
  - demografia
  - ludnosc
  - statystyki
compatibility: Python 3.8+ (standard library only); internet access required.
---

# Statystyki lokalne GUS BDL

Uruchamiaj z katalogu skilla: `python3 scripts/moja_gmina.py <komenda>` (Windows: `py`).

| Komenda | Zastosowanie |
|---|---|
| `units "Piaseczno" --level 6` | Znajdź gminy; wynik zachowuje rodzaj jednostki i identyfikator rodzica |
| `indicators "ludność" --level 6` | Wyszukaj wskaźniki i ich wymiary |
| `indicators "bezrobotni" --level 5` | Znajdź odpowiednią serię dla powiatów |
| `indicator ludnosc` | Pełna definicja i lata wskaźnika ludności ogółem (BDL 72305) |
| `compare --units <ID_BDL_1> <ID_BDL_2> --indicators ludnosc --year 2024` | Porównaj jednostki znalezione przez `units`, w jednym roku |
| `compare --units <ID_BDL_1> <ID_BDL_2> --indicators <ID_WSKAŹNIKA>` | Dobierz najnowszy rok z danymi dla obu jednostek |

1. Ustal jednostki przez `units`; 12-cyfrowy identyfikator BDL różni się od skróconego TERYT. Przy zbieżnych nazwach sprawdź `level`, `kind` i `parentId`. Gmina miejsko-wiejska, samo miasto oraz część wiejska mogą występować osobno.
2. Wybierz wskaźnik przez `indicators`, a jego pełny opis sprawdź przez `indicator`. Nazwy `n1`…`n5`, jednostka miary, poziom i lata są częścią definicji. Dochód ogółem i na mieszkańca to różne serie; wynagrodzenia czy stopa bezrobocia nie muszą być dostępne na poziomie gmin.
3. `compare` przyjmuje do 10 jednostek tego samego poziomu i do 5 wskaźników. Bez `--year` wybiera najnowszy wspólny rok **osobno dla każdego wskaźnika**. `no_common_data` oznacza brak porównywalnych danych; nie podstawiaj najnowszego roku z innej jednostki.
4. W odpowiedzi podaj źródło **GUS, Bank Danych Lokalnych**, rok, jednostkę miary i opis wskaźnika. Zachowaj atrybuty, uwagi metodologiczne i zakres terytorialny. `null`, brak obserwacji i tajemnica statystyczna nie oznaczają zera. Liczba mieszkańców nie jest oceną jakości życia ani prognozą.

Cache: metadane 24 h, dane 1 h w `~/.cache/ai-polish-skills/moja-gmina`; `--no-cache` przed komendą wymusza odczyt. `requests` podaje URL, faktyczny czas pobrania i użycie cache. `fetched_at` w korzeniu to czas przygotowania odpowiedzi. Cache można przenieść przez `MOJA_GMINA_CACHE_DIR`. Nie ma fallbacku do przeterminowanych danych.

API działa anonimowo; opcjonalny klucz ustaw jako `BDL_API_KEY` (nagłówek `X-ClientId`). Przy 429 skill kończy się kodem 69 i przekazuje `retry_after`; respektuj ten czas przed kolejną próbą. Nie zwiększaj częstotliwości zapytań przy awarii. Podczas weryfikacji 2026-11-05 dokumentacja i schemat oficjalnego API były dostępne, ale próby odczytu danych REST kończyły się timeoutem; testy offline nie są potwierdzeniem dostępności usługi.

Sukces: JSON stdout, kod 0. Błędy JSON stderr: 2 — brak zasobu/wyników, 64 — walidacja, 69 — sieć/API/format/limit. `--help`: kod 0. Szczegóły: [references/api.md](references/api.md).
