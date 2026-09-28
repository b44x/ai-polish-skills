---
name: imgw
display_name: IMGW-PIB Pogoda i Ostrzeżenia
version: 1.0.0
description: >-
  Pobieraj oficjalne dane meteorologiczne i hydrologiczne dla Polski z Instytutu Meteorologii
  i Gospodarki Wodnej (IMGW-PIB). Sprawdzaj aktualną temperaturę, ciśnienie atmosferyczne,
  wilgotność, prędkość i kierunek wiatru oraz sumę opadów ze stacji synoptycznych (Warszawa,
  Kraków, Gdańsk, Zakopane i 58 innych). Wyszukuj najbliższą stację pogodową po współrzędnych GPS.
  Pobieraj oficjalne ostrzeżenia meteorologiczne (burze, wichury, upały, mrozy) oraz hydrologiczne
  (susza hydrologiczna, stany wód rzek, stany alarmowe i ostrzegawcze na Wiśle, Odrze itp.). Zero
  kluczy API, w 100% oficjalne dane publiczne. Użyj, gdy użytkownik pyta o: "pogoda IMGW", "jaka jest
  temperatura w Warszawie", "ostrzeżenia IMGW", "stan Wisły", "stan wody", "alerty pogodowe",
  "ciśnienie", "wiatr", "opady w Polsce".
category: public_data
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: Instytut Meteorologii i Gospodarki Wodnej (IMGW-PIB)
source_type: official_api
official: true
homepage: https://imgw.pl
documentation: https://danepubliczne.imgw.pl/
rate_limit: fair use
last_verified: 2026-09-28
tags:
  - imgw
  - pogoda
  - synop
  - temperatura
  - cisnienie
  - wiatr
  - opady
  - ostrzezenia
  - alerty
  - hydro
  - rzeki
compatibility: Python 3.8+ (standard library only); network access to danepubliczne.imgw.pl.
---

# IMGW-PIB Pogoda, Alerty i Hydrologia

Oficjalny skill integrujący publiczne dane Instytutu Meteorologii i Gospodarki Wodnej (IMGW-PIB)
za pomocą `scripts/imgw.py`. Działa bez kluczy API, korzysta wyłącznie z biblioteki standardowej Pythona
i zwraca ustrukturyzowany format JSON na `stdout`.

## Uruchamianie

Uruchamiaj z katalogu skilla (lub ze ścieżki głównej repozytorium):

| System operacyjny | Komenda |
|---|---|
| Linux / macOS | `python3 scripts/imgw.py <komenda> …` |
| Windows | `py scripts/imgw.py <komenda> …` (lub `python`) |

Zero zewnętrznych bibliotek (Python 3.8+ stdlib).

## Główne scenariusze użycia

1. **Aktualna pogoda dla konkretnego miasta / stacji:**
   - Gdy użytkownik pyta np. „Jaka jest teraz temperatura w Warszawie?”, „Pokaż pogodę z IMGW dla Zakopanego”:
     `python3 scripts/imgw.py weather Warszawa`
     `python3 scripts/imgw.py weather Kraków`
     `python3 scripts/imgw.py weather Zakopane`
   - Skrypt automatycznie radzi sobie z polskimi znakami diakrytycznymi (np. `Kraków` -> `krakow`),
     oraz bezpiecznie obsługuje stacje górskie, gdzie ciśnienie na poziomie morza jest `null`.

2. **Wyszukanie najbliższej stacji IMGW po współrzędnych GPS:**
   - Gdy użytkownik pyta o pogodę w miejscowości bez stacji synoptycznej (np. Sopot, Gdynia, Piaseczno)
     lub podaje koordynaty GPS:
     `python3 scripts/imgw.py near 54.44 18.56`
   - Oblicza odległość ortodromiczną (Haversine) do wszystkich 62 stacji w Polsce i automatycznie
     pobiera bieżącą pogodę z najbliższej stacji (w tym przykładzie: Gdańsk, 7 km).

3. **Oficjalne ostrzeżenia i alerty IMGW:**
   - Gdy użytkownik pyta np. „Czy IMGW wydało ostrzeżenia dla województwa pomorskiego?”, „Czy są alerty pogodowe?”:
     `python3 scripts/imgw.py warnings --type all`
     `python3 scripts/imgw.py warnings --voivodeship pomorskie`
     `python3 scripts/imgw.py warnings --type meteo`

4. **Stany rzek i zagrożenie powodziowe / suszą (Hydrologia):**
   - Gdy użytkownik pyta np. „Jaki jest stan wody na Wiśle?”, „Czy gdzieś w Polsce przekroczono stan alarmowy?”:
     `python3 scripts/imgw.py hydro --river Wisła`
     `python3 scripts/imgw.py hydro --alarm-only`
     `python3 scripts/imgw.py hydro --station Warszawa`

5. **Przegląd całej Polski (Synop) lub lista stacji:**
   - Gdzie jest teraz najcieplej / najzimniej w Polsce:
     `python3 scripts/imgw.py synop --sort temp_desc --limit 5`
     `python3 scripts/imgw.py synop --sort wind_desc --limit 5`
   - Sprawdzenie dostępnych stacji offline:
     `python3 scripts/imgw.py stations --search Poznań`

## Komendy

| Komenda | Opis | Zwracane dane |
|---|---|---|
| `weather <stacja>` | Aktualna pogoda ze stacji synoptycznej | `temperatureC`, `pressureHpa`, `windSpeedMs`, `windDirectionDeg`, `relativeHumidityPercent`, `rainfallMm`, `formatted`, `coordinates` |
| `near <lat> <lon> [--limit N]` | Najbliższa stacja synoptyczna do GPS | `closestStation` (z odległością w km i pogodą), `nearbyStations` |
| `warnings [--type meteo\|hydro\|all] [--voivodeship V]` | Oficjalne ostrzeżenia meteo i hydro | Lista aktywnych alertów: `event`, `level`, `published`, `validFrom`, `validTo`, `course`, `voivodeships` |
| `hydro [--river R] [--station S] [--alarm-only]` | Pomiary ze stacji wodowskazowych | `river`, `stationName`, `status`, `waterLevelCm`, `warningLevelCm`, `alarmLevelCm`, `waterTemperatureC` |
| `synop [--sort S] [--limit N]` | Przegląd wszystkich 62 stacji w Polsce | Zbiorcza lista stacji posortowana wg temperatury, wiatru, ciśnienia lub nazwy |
| `stations [--search Q]` | Katalog stacji synoptycznych (offline) | `stationId`, `stationName`, `slug`, `coordinates` |

Szczegółowy opis schematów i pól: [references/output.md](references/output.md).

## Kody wyjścia

Czysty JSON trafia na `stdout`; błędy na `stderr` jako `{"error": "...", "type": "..."}`.

| Kod | Znaczenie | Działanie |
|---|---|---|
| `0` | Sukces | Użyj danych JSON |
| `2` | Nie znaleziono | Stacja lub rzeka nie istnieje w bazie IMGW |
| `64` | Błędne wywołanie / walidacja | Sprawdź parametry polecenia lub współrzędne |
| `69` | Błąd serwera IMGW / sieci | Chwilowy błąd sieciowy; spróbuj ponownie |

## Zasady i Dobre Praktyki

- Zawsze podawaj źródło danych: **IMGW-PIB**.
- Na stacjach górskich (np. Kasprowy Wierch, Śnieżka, Zakopane) ciśnienie jest często pomijane (`null`), ponieważ nie redukuje się go do poziomu morza w standardowy sposób — informuj o tym użytkownika.
- W odpowiedziach dla użytkownika korzystaj z gotowych sformatowanych pól w obiekcie `formatted` (`20.4 °C`, `1028.5 hPa`, `3.0 m/s (100°)`).
