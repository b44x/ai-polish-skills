# Walidacja i pliki cyklu discovery

**Korekta 2026-11-07:** przed mergem skill `praca` przemianowano na `solid-jobs`, aby nazwa odpowiadała pojedynczemu źródłu. Historyczny ranking i log live zachowują pierwotny identyfikator; nie oznaczają istnienia dwóch skilli. Ocena 90/100 przeszacowała zasięg integracji pojedynczego portalu i nie stanowi podstawy do promowania jej jako uniwersalnej wyszukiwarki pracy.

Research i smoke testy: 2026-11-06 UTC. Finalizacja: 2026-11-07 (Europe/Warsaw). Gałąź `skill/adresy-otwarte-dane`, baza `origin/dev` — `b10cab1` (zawiera PR #1 i #2). Osobny worktree: `../ai-polish-skills-discovery`.

## Wymagane kontrole

| Polecenie | Wynik |
|---|---|
| `python3 scripts/validate_skills.py` | PASSED; 23 skille, 0 błędów, 0 ostrzeżeń |
| `python3 scripts/test_skills.py` | ALL TESTS PASSED; 322 testy na Pythonie 3.9.6 |
| `python3 scripts/build_registry.py` | Wygenerowano oba rejestry i marketplace; 23 skille |
| `python3 scripts/build_registry.py --check` | OK; kontroluje teraz także registry.min.json |

Dodatkowo cały harness przeszedł na Homebrew Pythonie 3.15.2 (322 testy). W liczbie 322 mieszczą się 256 testów jednostkowych/behawioralnych; nie należy dodawać tych liczb do siebie. Nowy plik testowy wnosi 30 metod testowych i wiele podprzypadków parametrów/HTTP/formatów.

Dwa błędy starych fixture HTTP ujawniono przed rebase, kolejne po włączeniu PR #1. Poprawiono łącznie pięć plików testów, przekazując `io.BytesIO()` zamiast pustego `fp=None` do `HTTPError`. Następnie ponownie uruchomiono pełne kontrole na obu interpreterach. Nie zmieniano logiki produkcyjnej istniejących integracji.

## Dodatkowe sprawdzenia

- 11/11 wywołań nowych CLI do rzeczywistych API: kod 0, poprawny JSON, pusty stderr. [Dokładne komendy i obserwacje](2026-11-06-live.json).
- 12 prób istniejących klientów: 11 poprawnych odpowiedzi, jeden kontrolowany timeout BDL. [Wyniki](2026-11-06-existing-live.json). Dostępność BDL pozostaje ograniczeniem upstreamu, nie sukcesem testu live.
- Instalacja `bash install.sh install solid-jobs adresy otwarte-dane --dir <katalog-tymczasowy> --json`: poprawny JSON, trzy foldery; wszystkie trzy zainstalowane entrypointy uruchomione z katalogu poza repo i poprawne `--help`.
- Składnia nowych skryptów sprawdzona przez `ast.parse(feature_version=(3,8))`. Nie wykonano runtime testu na Pythonie 3.8 ani na Windows; nie utożsamiać kontroli gramatyki z takim testem.
- Wszystkie 25 sum punktów przeliczone automatycznie; oba pliki rejestru dają ten sam JSON; 23 wpisy po integracji.
- `git diff --check`: brak błędów whitespace. Lista zmienionych plików sprawdzona względem aktualnego dev.

## Utworzone i zmodyfikowane pliki

15 nowych plików, 12 zmodyfikowanych. `A` — nowy, `M` — zmodyfikowany. Zmiany użytkownika w drugim worktree i osobny commit językowy nie wchodzą do tego zestawu.

| Status | Plik |
|---|---|
| M | [`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json) |
| M | [`AGENTS.md`](../../AGENTS.md) |
| M | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |
| M | [`README.md`](../../README.md) |
| M | [`README_EN.md`](../../README_EN.md) |
| M | [`docs/cli.md`](../../docs/cli.md) |
| A | [`docs/demo/discovery.md`](../../docs/demo/discovery.md) |
| A | [`docs/growth/2026-11-06-discovery.md`](../../docs/growth/2026-11-06-discovery.md) |
| A | [`docs/research/2026-11-06-audit.md`](../../docs/research/2026-11-06-audit.md) |
| A | [`docs/research/2026-11-06-candidates.json`](../../docs/research/2026-11-06-candidates.json) |
| A | [`docs/research/2026-11-06-discovery.md`](../../docs/research/2026-11-06-discovery.md) |
| A | [`docs/research/2026-11-06-existing-live.json`](../../docs/research/2026-11-06-existing-live.json) |
| A | [`docs/research/2026-11-06-live.json`](../../docs/research/2026-11-06-live.json) |
| A | [`docs/research/2026-11-06-validation.md`](../../docs/research/2026-11-06-validation.md) |
| M | [`registry/registry.json`](../../registry/registry.json) |
| M | [`registry/registry.min.json`](../../registry/registry.min.json) |
| M | [`scripts/build_registry.py`](../../scripts/build_registry.py) |
| A | [`scripts/test_discovery_skills.py`](../../scripts/test_discovery_skills.py) |
| M | [`scripts/test_dzialki.py`](../../scripts/test_dzialki.py) |
| M | [`scripts/test_nieruchomosci.py`](../../scripts/test_nieruchomosci.py) |
| M | [`scripts/test_odjazdy.py`](../../scripts/test_odjazdy.py) |
| M | [`scripts/test_ostrzezenia_gis.py`](../../scripts/test_ostrzezenia_gis.py) |
| M | [`scripts/test_produkty.py`](../../scripts/test_produkty.py) |
| A | [`skills/adresy/SKILL.md`](../../skills/adresy/SKILL.md) |
| A | [`skills/adresy/scripts/adresy.py`](../../skills/adresy/scripts/adresy.py) |
| M | [`skills/cert-pl/SKILL.md`](../../skills/cert-pl/SKILL.md) |
| M | [`skills/dzialki/SKILL.md`](../../skills/dzialki/SKILL.md) |
| M | [`skills/energia/SKILL.md`](../../skills/energia/SKILL.md) |
| M | [`skills/imgw/SKILL.md`](../../skills/imgw/SKILL.md) |
| M | [`skills/moja-gmina/SKILL.md`](../../skills/moja-gmina/SKILL.md) |
| M | [`skills/nfz/SKILL.md`](../../skills/nfz/SKILL.md) |
| M | [`skills/nieruchomosci/SKILL.md`](../../skills/nieruchomosci/SKILL.md) |
| M | [`skills/odjazdy/SKILL.md`](../../skills/odjazdy/SKILL.md) |
| M | [`skills/ostrzezenia-gis/SKILL.md`](../../skills/ostrzezenia-gis/SKILL.md) |
| A | [`skills/otwarte-dane/SKILL.md`](../../skills/otwarte-dane/SKILL.md) |
| A | [`skills/otwarte-dane/scripts/otwarte_dane.py`](../../skills/otwarte-dane/scripts/otwarte_dane.py) |
| A | [`skills/solid-jobs/SKILL.md`](../../skills/solid-jobs/SKILL.md) |
| A | [`skills/solid-jobs/scripts/solid_jobs.py`](../../skills/solid-jobs/scripts/solid_jobs.py) |
| M | [`skills/produkty/SKILL.md`](../../skills/produkty/SKILL.md) |
| M | [`skills/przetargi/SKILL.md`](../../skills/przetargi/SKILL.md) |
| M | [`skills/sejm/SKILL.md`](../../skills/sejm/SKILL.md) |
| M | [`skills/smog/SKILL.md`](../../skills/smog/SKILL.md) |
| M | [`skills/terminy/SKILL.md`](../../skills/terminy/SKILL.md) |
| M | [`templates/skill/SKILL.md`](../../templates/skill/SKILL.md) |

## Materiały

[Ranking i 25 kart kandydatów](2026-11-06-discovery.md), [ranking JSON](2026-11-06-candidates.json), [audyt](2026-11-06-audit.md), [pakiet growth](../growth/2026-11-06-discovery.md), [scenariusze demo](../demo/discovery.md).

Pakiet growth: po 5 pytań, 3 demonstracje, opis marketingowy i korzyści, SEO, storyboard krótkiego filmu, propozycje postów X/LinkedIn/Reddit i instalacja dla każdego z trzech skilli. To 15 pytań, 9 scenariuszy, 3 storyboardy i 9 propozycji postów. Nie opublikowano postów, nie wysłano wiadomości, nie nagrano nowego filmu i nie podmieniono zastanych mediów.

PR jest przygotowany do przeglądu, bez automatycznego merge i bez wydania. Nowe skille są dostępne z gałęzi PR; standardowe pobieranie main udostępni je dopiero po odrębnym wydaniu.
