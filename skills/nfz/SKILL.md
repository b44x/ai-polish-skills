---
name: nfz
display_name: NFZ Kolejki i Czas Oczekiwania (PCUŚ)
version: 1.0.0
description: >-
  Oficjalne dane Narodowego Funduszu Zdrowia (NFZ) dotyczące kolejek, placówek medycznych i prognozowanego
  czasu oczekiwania na świadczenia (PCUŚ). Wyszukuj świadczenia medyczne (rezonans magnetyczny, tomografia,
  kolonoskopia, gastroskopia, poradnia kardiologiczna, ortopeda, okulista), sprawdzaj prognozowany czas oczekiwania
  (w dniach i miesiącach) oraz liczbę oczekujących pacjentów w trybie stabilnym i pilnym. Znajduj najbliższe placówki
  w zadanym promieniu kilometrów (Haversine) i porównuj czas oczekiwania w szpitalach oraz przychodniach.
  Zero kluczy API, w 100% oficjalne dane publiczne z API Terminy Leczenia NFZ. Użyj, gdy użytkownik pyta o:
  "kolejki NFZ", "czas oczekiwania do kardiologa", "gdzie na rezonans na NFZ", "terminy leczenia",
  "poradnia NFZ w Gdańsku", "najkrótsza kolejka do endokrynologa", "NFZ czas oczekiwania".
category: health
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: Narodowy Fundusz Zdrowia (NFZ)
source_type: official_api
official: true
homepage: https://terminyleczenia.nfz.gov.pl/
documentation: https://apinfz.nfz.gov.pl/app-itl-api-pcus/
rate_limit: fair use
last_verified: 2026-09-28
tags:
  - nfz
  - zdrowie
  - kolejki
  - pcus
  - lekarz
  - przychodnia
  - szpital
  - rezonans
  - tomografia
  - kardiolog
  - stomatolog
  - terminy
compatibility: Python 3.8+ (standard library only); network access to apinfz.nfz.gov.pl.
---

# NFZ Kolejki i Czas Oczekiwania (PCUŚ)

Oficjalny skill integrujący otwarte dane Narodowego Funduszu Zdrowia (NFZ) z API Terminy Leczenia / PCUŚ v1.4
za pomocą narzędzia `scripts/nfz.py`. Działa bez rejestracji i bez kluczy API, korzysta wyłącznie ze standardowej
biblioteki Pythona i zwraca ustrukturyzowany format JSON na `stdout`.

## Uruchamianie

Uruchamiaj z katalogu skilla (lub ze ścieżki głównej repozytorium):

| System operacyjny | Komenda |
|---|---|
| Linux / macOS | `python3 scripts/nfz.py <komenda> …` |
| Windows | `py scripts/nfz.py <komenda> …` (lub `python`) |

Zero zewnętrznych bibliotek (Python 3.8+ stdlib).

## Główne Scenariusze Użycia

1. **Wyszukiwanie oficjalnej nazwy świadczenia:**
   - Gdy użytkownik pyta ogólnie o badanie lub specjalizację (np. „rezonans”, „kardiolog”, „kolonoskopia”):
     `python3 scripts/nfz.py benefits rezonans`
     `python3 scripts/nfz.py benefits kardiolog`
     `python3 scripts/nfz.py benefits kolonoskopia`
   - Zwraca listę oficjalnych nazw świadczeń NFZ, które można podać w dalszych zapytaniach.

2. **Kolejki i czas oczekiwania w danym mieście / województwie:**
   - Sprawdzenie czasu oczekiwania na świadczenie w konkretnym mieście:
     `python3 scripts/nfz.py queues --benefit "REZONANS MAGNETYCZNY" --locality Gdańsk`
     `python3 scripts/nfz.py queues --benefit "ŚWIADCZENIA Z ZAKRESU KARDIOLOGII" --locality Warszawa`
   - Filtrowanie dla przypadku pilnego (skierowanie na cito):
     `python3 scripts/nfz.py queues --benefit "REZONANS MAGNETYCZNY" --locality Gdańsk --urgent`

3. **Geograficzne wyszukiwanie placówek w promieniu kilometrów (`near`):**
   - Wyszukanie placówek wykonujących dane świadczenie w promieniu od zadanego miasta lub współrzędnych:
     `python3 scripts/nfz.py near Gdańsk --benefit "rezonans" --radius-km 50`
     `python3 scripts/nfz.py near 54.35 18.64 --benefit "kolonoskopia" --radius-km 30`
   - Sortowanie wg najkrótszego czasu oczekiwania (`--sort time`) lub najmniejszej odległości (`--sort distance`).

4. **Porównanie placówek i najkrótsze kolejki (`compare`):**
   - Zestawienie placówek obok siebie ze wskazaniem placówki o najkrótszym czasie oczekiwania:
     `python3 scripts/nfz.py compare --benefit "rezonans" --locality Gdańsk`
     `python3 scripts/nfz.py compare --benefit "kardiolog" --province pomorskie`

5. **Lista kodów województw NFZ (`provinces`):**
   - Przegląd 16 kodów NFZ (np. `11` dla pomorskiego, `07` dla mazowieckiego):
     `python3 scripts/nfz.py provinces`

## Komendy

| Komenda | Opis | Zwracane dane |
|---|---|---|
| `benefits <query>` | Słownik oficjalnych nazw świadczeń | `query`, `count`, `benefits` |
| `queues [--benefit B] [--province P] [--locality L] [--urgent]` | Czas oczekiwania i lista placówek | `place`, `provider`, `locality`, `address`, `phone`, `waitingTime` (`pcus`, `averagePeriodDays`, `awaiting`), `accessibility` |
| `near <lokacja\|lat> [lon] --benefit <B> [--radius-km R]` | Placówki w promieniu km z odległościami | Obiekty placówek z wyliczonym `distanceKm`, posortowane wg wybranego kryterium |
| `compare --benefit <B> [--locality L] [--province P]` | Zestawienie porównawcze placówek | `highlights` (`shortestWaitClinic`, `fewestAwaitingClinic`, `closestClinic`), lista placówek |
| `provinces` | Słownik 16 województw i kodów NFZ | Kody dwucyfrowe i nazwy województw (offline) |

Szczegółowy opis schematów JSON: [references/output.md](references/output.md).

## Kody Wyjścia

Czysty JSON trafia na `stdout`; błędy na `stderr` jako `{"error": "...", "type": "..."}`.

| Kod | Znaczenie | Działanie |
|---|---|---|
| `0` | Sukces | Użyj danych JSON z `stdout` |
| `2` | Nie znaleziono | Brak placówek lub brak świadczenia w rejestrze NFZ |
| `64` | Błędne wywołanie / walidacja | Sprawdź parametry (min. 3 znaki frazy, poprawny kod województwa) |
| `69` | Błąd serwera NFZ / sieci | Błąd API `apinfz.nfz.gov.pl` lub problem sieciowy |

## Zasady i Dobre Praktyki

- **Zawsze podawaj źródło danych:** Narodowy Fundusz Zdrowia (NFZ / Terminy Leczenia).
- **Rozróżniaj PCUŚ od daty wizyty:** Dane NFZ prezentują *Prognozowany Czas Oczekiwania na Świadczenie* (statystyczny czas wyliczany przez NFZ na podstawie ostatnich miesięcy), a nie gwarantowany pierwszy wolny termin. Wyjaśnij to użytkownikowi.
- **Medyczna neutralność:** Narzędzie udostępnia dane administracyjno-kolejkowe. Nie stawiaj diagnoz medycznych ani nie oceniaj jakości opieki w danej placówce.
- **Rekomendacja kontaktu telefonicznego:** Sugeruj użytkownikowi bezpośredni kontakt telefoniczny z rejestracją placówki (telefon podany w polu `phone`) przed udaniem się na miejsce.
