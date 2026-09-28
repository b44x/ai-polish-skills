---
name: sejm
display_name: Sejm Rzeczypospolitej Polskiej
version: 1.0.0
description: >-
  Oficjalne dane parlamentarne Sejmu RP z otwartego API (api.sejm.gov.pl). Baza posłów X kadencji
  (okręgi wyborcze, kluby parlamentarne, komisje sejmowe, kontakt), szczegółowe wyniki głosowań
  (głosowania imienne, podział głosów wg klubów: za/przeciw/wstrzymał się/nieobecny, sprawdzanie jak
  głosował dany poseł), baza druków sejmowych i przebieg procesu legislacyjnego (etapy prac nad
  projektami ustaw i uchwał) oraz interpelacje poselskie i odpowiedzi ministerstw. Zero kluczy API,
  w 100% oficjalne dane publiczne. Użyj, gdy użytkownik pyta o: "posłowie na Sejm", "kto jest posłem z
  okręgu X", "jak głosowano w Sejmie nad ustawą Y", "jak głosował poseł Kowalski", "na jakim etapie
  jest projekt ustawy", "druki sejmowe", "interpelacje poselskie".
category: legal
language: pl
country: PL
license: MIT
author: Michell Hoduń (https://github.com/b44x)
repository: https://github.com/b44x/ai-polish-skills
network: true
authentication: none
source: Kancelaria Sejmu Rzeczypospolitej Polskiej
source_type: official_api
official: true
homepage: https://sejm.gov.pl
documentation: https://api.sejm.gov.pl/
rate_limit: fair use
last_verified: 2026-09-28
tags:
  - sejm
  - poslowie
  - glosowania
  - druki
  - proces-legislacyjny
  - ustawy
  - interpelacje
  - prawo
  - parlament
compatibility: Python 3.8+ (standard library only); network access to api.sejm.gov.pl.
---

# Sejm Rzeczypospolitej Polskiej

Oficjalny skill integrujący otwarte API Sejmu RP za pomocą `scripts/sejm.py`.
Umożliwia agentom AI neutralny dostęp do oficjalnych danych o posłach, głosowaniach,
drukach sejmowych, procesie legislacyjnym i interpelacjach. Zwraca czysty format JSON na `stdout`.

## Uruchamianie

Uruchamiaj z katalogu skilla (lub ze ścieżki głównej repozytorium):

| System operacyjny | Komenda |
|---|---|
| Linux / macOS | `python3 scripts/sejm.py <komenda> …` |
| Windows | `py scripts/sejm.py <komenda> …` (lub `python`) |

Zero zewnętrznych bibliotek (standardowa biblioteka Pythona 3.8+).

## Główne scenariusze użycia

1. **Baza posłów i komisji:**
   - Wyszukiwanie posłów z danego okręgu wyborczego lub po nazwisku:
     `python3 scripts/sejm.py mps --district "Gdańsk"`
     `python3 scripts/sejm.py mps --search "Kowalski"`
     `python3 scripts/sejm.py mps --club "PiS"`
   - Sprawdzenie szczegółów posła i komisji, w których zasiada:
     `python3 scripts/sejm.py mps --id 133`

2. **Głosowania i weryfikacja głosu konkretnego posła:**
   - Sprawdzenie wyników głosowania i podziału głosów według klubów (za, przeciw, wstrzymał się):
     `python3 scripts/sejm.py voting 1 2`
   - Sprawdzenie jak głosował konkretny poseł w danym głosowaniu:
     `python3 scripts/sejm.py voting 1 2 --mp "Hołownia"`
   - Przegląd tematów głosowań na ostatnim posiedzeniu:
     `python3 scripts/sejm.py votings`
     `python3 scripts/sejm.py votings --sitting 1 --search "Wicemarszałków"`

3. **Druki sejmowe i proces legislacyjny:**
   - Sprawdzenie druku sejmowego po numerze:
     `python3 scripts/sejm.py prints --number 1`
   - Wyszukiwanie druków po temacie:
     `python3 scripts/sejm.py prints --search "podatku"`
   - Sprawdzenie etapów prac nad projektem ustawy (czy wpłynął, I/II/III czytanie, czy uchwalono):
     `python3 scripts/sejm.py process 1`

4. **Interpelacje poselskie:**
   - Wyszukiwanie interpelacji wg tematu lub po numerze:
     `python3 scripts/sejm.py interpellations --search "CPK"`
     `python3 scripts/sejm.py interpellations --number 1`

## Komendy

| Komenda | Opis | Zwracane dane |
|---|---|---|
| `mps [--search S] [--club C] [--district D]` | Lista i wyszukiwanie posłów | `id`, `firstLastName`, `club`, `districtName`, `email`, `profession` |
| `mps --id <id>` | Pełne dane posła i komisje sejmowe | `birthDate`, `profession`, `committees` (z pełnioną funkcją) |
| `voting <sitting> <number> [--mp MP]` | Szczegóły głosowania i głos posła | `results`, `clubSummary` (głosy wg klubów), `mpVote` |
| `votings [--sitting S] [--search Q]` | Lista głosowań na posiedzeniu | `votingNumber`, `date`, `title`, `topic`, `yes`, `no`, `abstain` |
| `prints [--number N] [--search Q]` | Wyszukiwanie druków sejmowych | `number`, `title`, `documentDate`, `attachments` |
| `process <numer_druku>` | Etapy procesu legislacyjnego ustawy | `documentType`, `passed`, `closureDate`, chronologiczne `stages` |
| `interpellations [--number N] [--search Q]` | Interpelacje i odpowiedzi | `number`, `title`, `sentDate`, `fromMpIds`, `replies` |
| `terms` | Wykaz kadencji Sejmu (I–X) | `terms` (daty, numer, flaga `current`) |

Szczegółowy opis schematów JSON: [references/output.md](references/output.md).

## Zasady neutralności

- To narzędzie dostarcza obiektywnych danych parlamentarnych, a nie opinii politycznych.
- Nie formułuj ocen, rankingów moralnych ani politycznych interpretacji zachowań posłów.
- Każda odpowiedź powinna jednoznacznie wskazywać:
  * Źródło: **Sejm Rzeczypospolitej Polskiej** (`api.sejm.gov.pl`),
  * Numer kadencji (domyślnie **X kadencja**),
  * Numer posiedzenia i numer głosowania lub druku,
  * Datę zdarzenia.

## Kody wyjścia

Czysty JSON trafia na `stdout`; błędy na `stderr` jako `{"error": "...", "type": "..."}`.

| Kod | Znaczenie | Działanie |
|---|---|---|
| `0` | Sukces | Przetwórz dane JSON |
| `2` | Nie znaleziono | Poseł, głosowanie, druk lub proces nie istnieje |
| `64` | Błędne wywołanie / walidacja | Sprawdź parametry wywołania polecenia |
| `69` | Błąd serwera Sejmu RP / sieci | Chwilowy problem z API; spróbuj ponownie |
