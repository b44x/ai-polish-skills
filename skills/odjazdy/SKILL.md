---
name: odjazdy
display_name: Odjazdy — Gdańsk, Poznań i Szczecin
version: 1.0.0
description: >-
  Find public transport stops and upcoming bus or tram departures in Gdańsk, Poznań and Szczecin using transport operators' public services. Use for "kiedy tramwaj", "odjazdy z przystanku", "opóźnienie autobusu". Distinguishes realtime predictions, schedules, canceled services and stale data. Coverage is limited to the three supported networks; no route planning or ticket purchases.
category: utilities
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: ZTM Gdańsk, ZTM Poznań (PEKA), ZDiTM Szczecin
source_type: official_api
official: true
homepage: https://www.zditm.szczecin.pl/pl/zditm/dla-programistow
documentation: https://www.zditm.szczecin.pl/pl/zditm/dla-programistow/api-tablice-odjazdow
rate_limit: Szczecin 100 requests/minute/IP; one-shot lookups, upstream HTTP cache honored
last_verified: 2026-11-05
tags:
  - odjazdy
  - komunikacja-miejska
  - autobus
  - tramwaj
  - gdansk
  - poznan
  - szczecin
compatibility: Python 3.8+ (standard library only); internet access required except cities.
---

# Odjazdy komunikacji miejskiej

Uruchamiaj `python3 scripts/odjazdy.py <komenda>` z katalogu skilla (`py` na Windows).

| Komenda | Działanie |
|---|---|
| `cities` | Lista obsługiwanych sieci, źródeł i funkcji; działa offline |
| `stops Gdańsk --query "Dworzec Główny"` | Wyszukaj słupki przystankowe po nazwie |
| `stops Szczecin --lat 53.4285 --lon 14.5528 --limit 5` | Najbliższe przystanki według odległości w linii prostej |
| `stops Poznań --query "Rondo Kaponiera"` | Słupki PEKA i kierunki; GPS w Poznaniu nie jest obsługiwany |
| `departures gdansk 2001 --limit 5` | Tablica odjazdów według identyfikatora zwróconego przez `stops` |
| `departures poznan RKAP71 --line 3` | Odjazdy jednej linii; używaj pola `id`, nie `public_code` |
| `departures szczecin 10822` | Odjazdy i komunikaty ZDiTM |

## Dobór przystanku i interpretacja

1. Ustal miasto, nazwę przystanku i kierunek. Najpierw `stops`, potem `departures` z polem `id`. Kilka wyników zwykle oznacza różne słupki lub kierunki — nie wybieraj arbitralnie przeciwnej strony ulicy. Nazwy miast przyjmują polskie znaki lub zapis ASCII. PEKA korzysta z podpowiedzi dostawcy i może wymagać polskich znaków w nazwie przystanku.
2. Pokazuj linię, kierunek, czas oraz status każdego kursu. `realtime` oznacza prognozę dostawcy, `scheduled` — rozkład, `canceled` — kurs odwołany. Nie obiecuj gwarantowanego czasu przyjazdu. Uwzględnij `messages` i `warnings`.
3. Czasy ISO z Gdańska/Szczecina są UTC i mają `Z`; przedstawiaj je użytkownikowi w Europe/Warsaw z uwzględnieniem daty i zmiany czasu. `fetched_at` jest czasem pobrania, a `source_updated_at` czasem źródła. Przy `freshness: stale` albo `measurement_stale: true` wyraźnie zaznacz nieaktualność. Brak czasu źródła daje `freshness: unknown`.
4. **PEKA ma specyficzny format:** `scheduled_local` zawiera lokalny czas Europe/Warsaw. Dostawca dopisuje `Z` do lokalnej godziny, dlatego `provider_departure_raw` nie wolno interpretować jako prawidłowego UTC. Dla kursu na żywo używaj przede wszystkim `minutes`; `estimated_at` to przybliżenie z tych minut i zegara serwera. PEKA nie publikuje czasu ostatniego pomiaru — świeżość jest nieznana, mimo flagi `realtime`.
5. `usable_realtime` jest prawdziwe tylko przy potwierdzonym aktualnym czasie tablicy, nieodwołanym kursie i braku wykrytej starej pozycji. Wartość false sama w sobie nie zmienia rozkładu w odwołany kurs.
6. Pusta tablica (`no_departures`) dotyczy zakresu czasu i filtrów dostawcy. Nie oznacza braku połączeń przez cały dzień. Najbliższy przystanek nie oznacza najlepszej trasy; skill nie planuje przesiadek ani nie kupuje biletów.

## Źródła i ograniczenia

Obsługiwane są **trzy sieci: Gdańsk, Poznań i Szczecin** wraz z przystankami podmiejskimi obecnymi u dostawców. Nie deklaruj dostępności w całej Polsce. Gdański katalog może zawierać przystanki innych organizatorów, dla których tablica ZTM jest pusta. Kraków i inne miasta nie mają w tej wersji adapterów.

Podawaj źródło i czas danych; wynik jest przetworzony (normalizacja pól, filtrowanie i ewentualne przeliczenie odległości/minut). Gdańsk: CC BY; Szczecin: CC0 1.0; Poznań: zasady ponownego wykorzystania wymagają informacji o źródle, aktualizacji i przetworzeniu. Szczegóły i odnośniki: [references/providers.md](references/providers.md).

Skrypt respektuje HTTP `Cache-Control` i `ETag`. Gdański katalog bez zaleceń HTTP jest buforowany godzinę; tablice bez zaleceń HTTP nie są buforowane. `ODJAZDY_CACHE_DIR` zmienia katalog cache. Błąd sieci nie zwraca starej tablicy jako aktualnej. Nie uruchamiaj częstego odpytywania w tle w ramach zwykłej prośby o odjazdy.

Sukces: JSON na stdout i kod `0`. Błędy JSON na stderr: `2` — brak przystanku/zasobu, `64` — nieprawidłowe argumenty lub nieobsługiwane miasto, `69` — błąd API/sieci/formatu. `--help` i `-h`: kod `0`.
