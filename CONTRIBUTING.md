# Contributing to ai-polish-skills (polskieskille.pl)

Dziękujemy za chęć współtworzenia polskiego rejestru skilli AI!

Rejestr `ai-polish-skills` gromadzi modularne skille dla agentów AI (Claude Code, Cursor, Windsurf, Antigravity i innych systemów zgodnych ze standardem `SKILL.md`), pozwalające modelom korzystać z polskich usług, rejestrów publicznych i API.

---

## Konwencje narzędzi projektu

Instalator i CLI zarządzające używają angielskich nazw komend, pomocy, komunikatów technicznych i kluczy JSON. Polskie opisy skilli, frazy wyszukiwania i treść danych źródłowych zachowują swój język. Nie tłumacz identyfikatorów ani istniejących pól JSON przy poprawkach dokumentacji.

`install.sh` jest cienkim bootstrapem; logikę instalacji utrzymujemy wyłącznie w `scripts/installer.py`, a argumenty w `scripts/cli.py`. Zmiany zachowania muszą zachować opisane aliasy, czysty stdout dla `--json` oraz kody wyjścia. [Pełny kontrakt CLI](docs/cli.md) opisuje ścieżki, aktualizacje, podgląd i podmianę plików.

## 8-krokowy proces dodawania nowego skilla

Każdy nowy skill dodawany jest w przewidywalnym procesie:

```
1. Wybierz polską usługę / API
   ↓
2. Sprawdź źródło i warunki użycia (licencja, limity, oficjalność)
   ↓
3. Utwórz katalog skilla (skills/<nazwa-skilla>/)
   ↓
4. Dodaj SKILL.md z instrukcjami dla agenta
   ↓
5. Dodaj kompletny manifest w YAML frontmatter
   ↓
6. Przygotuj skrypt (scripts/<nazwa>.py) i testy kontraktu
   ↓
7. Uruchom validator (scripts/validate_skills.py) oraz testy (scripts/test_skills.py)
   ↓
8. Otwórz Pull Request z wypełnioną checklistą
```

### Krok 1: Wybór polskiej usługi / API
Wybierz konkretne źródło danych lub usługę (np. rejestr państwowy, system logistyczny, serwis e-commerce, finanse, prawo, pogoda, dane publiczne). Preferowane są usługi stabilne, z jasnym modelem dostępu.

### Krok 2: Źródło i warunki użycia
Określ jednoznacznie charakter źródła:
- `official_api`: oficjalny endpoint instytucji publicznej lub firmy (np. KAS, NBP, KRS, GUS).
- `public_api`: publicznie otwarty interfejs (np. InPost ShipX widget).
- `unofficial_api`: wewnętrzne API serwisu.
- `scraping`: ekstrakcja danych HTML.
- `static_data`: zrzut danych offline lub zaszyte tablice referencyjne.

*Zasada uczciwości:* Nie zgaduj danych. Jeżeli rate limit lub dokumentacja nie są publicznie znane, wpisz `fair use` lub `none`. Nie wprowadzaj fikcyjnych informacji.

### Krok 3: Utwórz katalog skilla
Skopiuj szablon z `templates/skill`:
```bash
git switch dev && git pull
git switch -c skill/<nazwa-skilla>
cp -r templates/skill skills/<nazwa-skilla>
```
Nazwa skilla **musi** być w formacie `kebab-case` (np. `ceidg`, `pogoda-imgw`, `otodom`).

### Krok 4: Instrukcje w SKILL.md
`description` i instrukcje dla agenta pisz **po angielsku**. To konwencja tego projektu, a nie wymóg językowy formatu `SKILL.md`. Zachowaj po polsku przykładowe pytania użytkownika, nazwy instytucji, cytaty oraz parametry wyszukiwania wymagane przez źródło. Odpowiedź dla użytkownika dopasuj do języka jego pytania.

- `description` krótko opisuje możliwości i moment użycia; dodaj reprezentatywne polskie frazy, które pomagają wybrać skill.
- W treści podaj sposób uruchomienia z katalogu skilla, komendy, interpretację wyniku oraz istotne ograniczenia. Nagłówki i objaśnienia pisz po angielsku; oficjalne nazwy mogą pozostać w oryginale.
- Zachowaj identyfikatory skilli, nazwy flag, wartości enum i klucze JSON. Tłumaczenie dokumentacji nie zmienia interfejsu skryptu ani danych źródła.
- Dłuższe schematy i szczegóły umieszczaj w `references/`; linkuj je z informacją, kiedy należy je przeczytać. Nie wymuszamy identycznego zestawu sekcji w każdym skillu.
- `display_name` i treści katalogu dla użytkowników są po polsku. Pole `language: pl` określa docelowy język/locale skilla, nie język instrukcji dla agenta.
- Przy przeglądzie sprawdź sens instrukcji: zakres danych, daty, jednostki, brakujące wartości i atrybucja muszą pozostać poprawne. Sam test obecności angielskich nagłówków nie weryfikuje jakości skilla.

### Krok 5: Manifest metadanych (YAML frontmatter)
Frontmatter w `SKILL.md` jest **jedynym źródłem prawdy** dla metadanych skilla. Wypełnij wszystkie wymagane pola:

```yaml
---
name: moja-usluga
display_name: Czytelna Nazwa Usługi
version: 1.0.0
description: >-
  Describe what the skill does and when to use it in English.
  Include representative Polish trigger phrases, such as "sprawdź firmę" or "kurs walut".
category: finance # finance | logistics | legal | entertainment | public_data | utilities | e-commerce | health | general
language: pl
country: PL
license: MIT
author: Imię Nazwisko (https://github.com/twoj-login)
repository: https://github.com/b44x/ai-polish-skills
network: true # true = wymaga sieci, false = działa offline
authentication: none # none | api_key | oauth | credentials
source: Nazwa Instytucji lub Dostawcy
source_type: official_api # official_api | public_api | unofficial_api | scraping | static_data
official: true # true jeśli dostarczane przez oficjalny podmiot
homepage: https://usluga.gov.pl
documentation: https://usluga.gov.pl/api/docs
rate_limit: fair use
last_verified: 2026-09-28 # Data ostatniej weryfikacji YYYY-MM-DD
tags:
  - tag1
  - tag2
compatibility: Python 3.8+ (standard library only).
---
```

### Krok 6: Kod skryptu i kontrakt CLI
W katalogu `skills/<nazwa>/scripts/<nazwa>.py`:
- Używaj **wyłącznie biblioteki standardowej Pythona 3.8+** (zero zewnętrznych zależności pip!).
- **Kontrakt CLI:**
  - Obsługa `--help` oraz `-h` — zawsze zwraca kod wyjścia `0` i czytelną pomoc na stdout.
  - Sukces — wyłącznie czysty **JSON na stdout** (żadnych printów debugowych!).
  - Błąd — czytelny komunikat lub błąd JSON na **stderr**, kod wyjścia różny od zera (np. `2` dla braku wyników, `64` błąd walidacji, `69` błąd sieciowy).

### Krok 7: Walidacja i testy lokalne
Przed otwarciem PR uruchom pełny zestaw weryfikacyjny:
```bash
# 1. Walidacja manifestu, ścieżek, semver, składni AST i sekretów
python3 scripts/validate_skills.py

# 2. Uruchomienie automatycznego test harnessu
python3 scripts/test_skills.py

# 3. Wygenerowanie registry i sprawdzenie spójności
python3 scripts/build_registry.py
python3 scripts/build_registry.py --check
```

### Krok 8: Otwórz Pull Request
Wypchnij gałąź i otwórz PR do gałęzi `dev`:
```bash
git add skills/<nazwa-skilla> registry/
git commit -m "feat(<nazwa-skilla>): add new skill"
git push -u origin skill/<nazwa-skilla>
gh pr create --base dev --fill
```

---

## Tabela pól manifestu

| Pole | Typ | Wymagane | Opis |
|---|---|:---:|---|
| `name` | string | Tak | Identyfikator `kebab-case`, identyczny z nazwą folderu |
| `display_name` | string | Tak | Czytelna nazwa dla katalogu i UI |
| `version` | string | Tak | Semantyczna wersja `X.Y.Z` |
| `description` | string | Tak | Opis funkcji i fraz wyzwalających (max 1024 znaki) |
| `category` | string | Tak | Jedna z: `finance`, `logistics`, `legal`, `entertainment`, `public_data`, `utilities`, `e-commerce`, `health`, `general` |
| `language` | string | Tak | Docelowy język/locale skilla (zwykle `pl`), nie język instrukcji |
| `country` | string | Tak | Kod kraju (zwykle `PL`) |
| `license` | string | Tak | Identyfikator licencji SPDX (np. `MIT`, `Apache-2.0`) |
| `network` | bool | Tak | `true` jeśli skrypt łączy się z Internetem, `false` jeśli działa offline |
| `authentication` | string | Tak | Jedno z: `none`, `api_key`, `oauth`, `credentials` |
| `source` | string | Tak | Nazwa instytucji/dostawcy danych |
| `source_type` | string | Tak | `official_api`, `public_api`, `unofficial_api`, `scraping`, `static_data` |
| `official` | bool | Tak | `true` jeśli dostarczane oficjalnie przez instytucję |
| `homepage` | string | Tak | URL strony głównej usługi |
| `documentation` | string | Tak | URL dokumentacji technicznej lub `none` |
| `tags` | list[string] | Tak | Lista tagów ułatwiających wyszukiwanie |
| `rate_limit` | string | Nie | Znane limity zapytań (np. `300 req/day`, `fair use`) |
| `last_verified` | string | Nie | Data ostatniego potwierdzenia działania (`YYYY-MM-DD`) |
| `compatibility` | string | Nie | Wymagania środowiskowe |

---

## Checklista Pull Requesta

Przed scaleniem upewnij się, że:
- [ ] Folder w `skills/<name>` ma poprawną nazwę `kebab-case`.
- [ ] `SKILL.md` zawiera poprawny nagłówek YAML ze wszystkimi wymaganymi polami.
- [ ] `description` i instrukcje są po angielsku; polskie przykłady, nazwy oraz niezmienione identyfikatory zachowują sens i kontrakt skilla.
- [ ] Skrypt w `scripts/` korzysta wyłącznie z biblioteki standardowej Pythona 3.8+ (brak zależności w `pip`).
- [ ] Skrypt obsługuje `--help` i zwraca kod `0`.
- [ ] Skrypt wypisuje wyłącznie poprawny JSON na `stdout`.
- [ ] Komunikaty błędów trafiają na `stderr` z niezerowym kodem wyjścia.
- [ ] Kod przeszedł `python3 scripts/validate_skills.py` z wynikiem `PASSED`.
- [ ] Przeszedł `python3 scripts/test_skills.py` z wynikiem `ALL TESTS PASSED`.
- [ ] Wykonano `python3 scripts/build_registry.py` i zaktualizowano `registry/registry.json`.
- [ ] Brak przypadkowo pozostawionych tokenów, kluczy API lub prywatnych danych.
- [ ] PR jest skierowany do gałęzi `dev` (nie `main`).

---

## Automatyzacja wydań (dla maintainerów)

Wydania tworzone są za pomocą jednego polecenia:
```bash
python3 scripts/release.py --type minor
```
Skrypt automatycznie sprawdza walidację, testy, buduje registry, tworzy PR `dev -> main`, scala go, taguje wersję `vX.Y.Z` i publikuje GitHub Release.
