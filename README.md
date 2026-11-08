<p align="center">
  🇵🇱 <b>Polski</b> | 🇬🇧 <a href="README_EN.md">English</a>
</p>

# ai-polish-skills 🇵🇱

Oficjalny rejestr i katalog otwartych skilli dla agentów sztucznej inteligencji, dostosowanych do **polskiego rynku, usług, urzędów i API**.

> 🌐 Warstwa discovery i katalog online: **[polskieskille.pl](https://polskieskille.pl)**  
> 📦 Open-source core i rejestr: **[github.com/b44x/ai-polish-skills](https://github.com/b44x/ai-polish-skills)**

---

## Demo

**See Polskie Skille in action** — jedno pytanie po polsku, agent wybiera skill, skill odpytuje oficjalne polskie źródło (MF, KRS, NBP, IMGW-PIB, NFZ, Sejm RP, InPost, CERT Polska, GIOŚ, BZP) i zwraca czytelny wynik. Wszystkie dane w filmie pochodzą z rzeczywistych uruchomień skilli.

<p align="center">
  <a href="docs/demo/demo.mp4"><img src="docs/demo/demo.gif" alt="Polskie Skille — demo: agent AI korzysta z polskich API i danych publicznych" width="960"></a>
</p>

<p align="center">
  ▶️ <a href="docs/demo/demo.mp4"><b>Obejrzyj pełne demo (MP4, 1080p, ≈84 s)</b></a> · 🌐 <a href="https://polskieskille.pl">polskieskille.pl</a> · 🛠 <a href="docs/demo/README.md">jak wygenerować demo</a>
</p>

---

## 💡 Czym są Polskie Skille?

**ai-polish-skills** to ekosystem modularnych rozszerzeń dla agentów AI, które dają modelom bezpośredni dostęp do polskich danych w czasie rzeczywistym. Zamiast halucynować dane o firmach, kursach czy przesyłkach, agent uruchamia deterministyczny skrypt i otrzymuje ustrukturyzowany JSON.

### Kluczowe zasady:
- **Zero zależności (pip-free):** Wszystkie skrypty działają na czystej bibliotece standardowej Pythona 3.8+.
- **Determinizm:** Czysty JSON na `stdout`, błędy na `stderr`, stabilne kody wyjścia.
- **Jedno źródło prawdy:** Wszystkie metadane skilla znajdują się w nagłówku YAML w `SKILL.md`.
- **Zweryfikowane źródła:** Jasna deklaracja czy API jest oficjalne (`official_api`), publiczne, czy nieoficjalne.

---

## 📄 Czym jest standard `SKILL.md`?

`SKILL.md` to otwarty format instrukcji dla agentów AI. Każdy folder w `skills/<nazwa>` zawiera plik `SKILL.md` złożony z:
1. **YAML Frontmatter (Manifest):** Metadane skilla (`name`, `version`, `category`, `source`, `network`, `tags`, itp.). Agent czyta ten nagłówek, aby zdecydować czy skill pasuje do zapytania użytkownika (*Progressive Disclosure*).
2. **Treść Markdown:** Konkretne instrukcje dla modelu, opis parametrów, przykłady użycia oraz tabela komend dla Linux/macOS/Windows.
3. **Skrypty w `scripts/`:** Narzędzia CLI uruchamiane przez agenta w terminalu.

---

## 📦 Dostępne skille w rejestrze

| Skill | Nazwa i kategoria | Opis | Źródło danych |
|---|---|---|---|
| [`adresy`](skills/adresy/SKILL.md) | **Adresy i GPS** `[public_data]` | Adres na GPS i pobliski adres dla współrzędnych; zachowuje warianty dopasowania | GUGiK UUG — oficjalne API |
| [`biala-lista`](skills/biala-lista/SKILL.md) | **Biała Lista VAT** `[finance]` | Weryfikacja statusu podatnika VAT, NIP, REGON, KRS i kont bankowych przed przelewem B2B (split payment). | Ministerstwo Finansów (🏛 oficjalne API) |
| [`ceny-deweloperow`](skills/ceny-deweloperow/SKILL.md) | **Historia ceny mieszkania** `[public_data]` | Zmiany opublikowanej ceny lokalu, daty i luki; obsługa wybranych schematów plików | dane.gov.pl / cenniki deweloperów |
| [`cert-pl`](skills/cert-pl/SKILL.md) | **CERT Polska — podejrzane linki** `[utilities]` | Sprawdzenie domeny lub linku z SMS na liście ostrzeżeń, z obsługą subdomen i IDN. Nie otwiera badanego adresu; brak wpisu nie potwierdza bezpieczeństwa. | CERT Polska (🏛 oficjalna lista) |
| [`dzialki`](skills/dzialki/SKILL.md) | **Działki — lokalizacja i granice** `[public_data]` | Działka po identyfikatorze, nazwie obrębu i numerze albo punkcie GPS; geometria i położenie administracyjne z jawnym układem współrzędnych. | GUGiK ULDK (🏛 oficjalna usługa) |
| [`energia`](skills/energia/SKILL.md) | **Energia — ceny rynkowe PSE** `[finance]` | Kwadransowe ceny RCE, podsumowania i najtańsze ciągłe okno. Uwzględnia kompletność danych i zmianę czasu; cena RCE nie obejmuje pełnego kosztu na rachunku. | Polskie Sieci Elektroenergetyczne (🏛 oficjalne API) |
| [`filmweb`](skills/filmweb/SKILL.md) | **Filmweb** `[entertainment]` | Baza filmów, seriali, ocen krytyków/widzów, obsada, daty premier oraz platformy VOD z cenami w PLN. | Filmweb.pl (🔗 reverse-engineered API) |
| [`imgw`](skills/imgw/SKILL.md) | **IMGW-PIB Pogoda i Alerty** `[public_data]` | Oficjalne dane pogodowe (temperatura, ciśnienie, wiatr, opady) z 62 stacji w Polsce, ostrzeżenia meteo/hydro oraz stany rzek. | IMGW-PIB (🏛 oficjalne API) |
| [`inpost`](skills/inpost/SKILL.md) | **InPost & Paczkomaty** `[logistics]` | Śledzenie paczek po 24-cyfrowym numerze, wyszukiwarka Paczkomatów po kodzie, ulicy, mieście lub GPS z odległością. | InPost ShipX (🔗 public API) |
| [`krs`](skills/krs/SKILL.md) | **Krajowy Rejestr Sądowy** `[legal]` | Odpisy spółek i fundacji, skład zarządu, prokurenci, kapitał zakładowy oraz zasady reprezentacji (kto może podpisać umowę). | Ministerstwo Sprawiedliwości (🏛 oficjalne API) |
| [`leki`](skills/leki/SKILL.md) | **Leki — rejestr i ulotki** `[health]` | Wyszukiwanie nazw i substancji, opakowania po GTIN/EAN oraz oficjalne ulotki i ChPL; z datą rejestru | RPL — URPL / Centrum e-Zdrowia (oficjalny eksport XML) |
| [`moja-gmina`](skills/moja-gmina/SKILL.md) | **Moja gmina — dane GUS BDL** `[public_data]` | Wyszukiwanie jednostek i wskaźników, porównania na wspólny rok i poziom terytorialny. Zachowuje jednostki miary i oznaczenia braków danych. | Główny Urząd Statystyczny (🏛 oficjalne API BDL) |
| [`nbp`](skills/nbp/SKILL.md) | **Narodowy Bank Polski** `[finance]` | Średnie kursy walut (tabela A i B), ceny złota oraz przeliczanie faktur walutowych na PLN wg art. 31a ustawy o VAT. | Narodowy Bank Polski (🏛 oficjalne API) |
| [`nfz`](skills/nfz/SKILL.md) | **NFZ Kolejki i Czas Oczekiwania (PCUŚ)** `[health]` | Oficjalne dane o czasie oczekiwania na świadczenia (rezonans, tomografia, poradnie), liczba oczekujących, tryb stabilny i pilny oraz wyszukiwanie placówek w promieniu km. | Narodowy Fundusz Zdrowia (🏛 oficjalne API) |
| [`nieruchomosci`](skills/nieruchomosci/SKILL.md) | **Ceny transakcyjne nieruchomości** `[public_data]` | Transakcje RCN w wybranej okolicy; rodzaj nieruchomości, ceny, powierzchnie i udziały. Porównania z jawnymi ograniczeniami danych. | GUGiK / Geoportal RCN (🏛 oficjalna usługa WFS) |
| [`odjazdy`](skills/odjazdy/SKILL.md) | **Odjazdy komunikacji miejskiej** `[utilities]` | Przystanki i odjazdy w Gdańsku, Poznaniu i Szczecinie. Rozróżnia prognozy na żywo od rozkładu; zakres danych zależy od miasta. | ZTM Gdańsk, ZTM Poznań / PEKA, ZDiTM Szczecin (🏛 źródła operatorów) |
| [`ostrzezenia-gis`](skills/ostrzezenia-gis/SKILL.md) | **Ostrzeżenia GIS** `[health]` | Przeglądanie i wyszukiwanie opublikowanych ostrzeżeń oraz odczyt treści z danymi partii. Wynik podaje zakres przeszukanych komunikatów; brak trafienia nie potwierdza bezpieczeństwa produktu. | GIS / gov.pl (🏛 oficjalne komunikaty HTML) |
| [`otwarte-dane`](skills/otwarte-dane/SKILL.md) | **Wyszukiwarka danych** `[public_data]` | Zbiory, zasoby, daty i warunki ponownego wykorzystania | dane.gov.pl — oficjalne API |
| [`prawo`](skills/prawo/SKILL.md) | **Prawo (ISAP / Dziennik Ustaw)** `[legal]` | Brzmienie artykułów kodeksów i ustaw z datą źródła i ostrzeżeniem o późniejszych zmianach, status aktu, teksty jednolite i nadchodzące zmiany. | Kancelaria Sejmu — ISAP/ELI (🏛 oficjalne API) |
| [`produkty`](skills/produkty/SKILL.md) | **Produkty — skład i wartości odżywcze** `[utilities]` | Wyszukiwanie żywności i odczyt etykiety po kodzie kreskowym: nazwa, skład, dane o alergenach i wartości odżywcze z jednostkami. Braki i jakość społecznościowej bazy są jawne. | Open Food Facts (🔗 publiczne API, dane społecznościowe) |
| [`przetargi`](skills/przetargi/SKILL.md) | **Przetargi — ogłoszenia BZP** `[public_data]` | Wyszukiwanie ogłoszeń o zamówieniu po frazie, CPV, województwie zamawiającego i datach publikacji; szczegóły z linkiem do źródła. | Urząd Zamówień Publicznych (🏛 oficjalne API) |
| [`sejm`](skills/sejm/SKILL.md) | **Sejm RP** `[legal]` | Baza posłów, komisji, wyniki głosowań imiennych i klubowych, druki sejmowe oraz etapy procesu legislacyjnego. | Kancelaria Sejmu (🏛 oficjalne API) |
| [`smog`](skills/smog/SKILL.md) | **Smog — jakość powietrza GIOŚ** `[public_data]` | Stacje po mieście lub GPS, indeks GIOŚ oraz ostatnie pomiary zanieczyszczeń z jednostkami i czasem pomiaru. | GIOŚ (🏛 oficjalne API) |
| [`solid-jobs`](skills/solid-jobs/SKILL.md) | **SOLID.Jobs — oferty i widełki** `[general]` | Oferty SOLID.Jobs, zdalność, osobne kwoty B2B/UoP i statystyki portalu | SOLID.Jobs — oficjalne API |
| [`terminy`](skills/terminy/SKILL.md) | **Terminy, dni robocze i święta** `[utilities]` | Dni robocze, święta (z Wigilią), wymiar czasu pracy (art. 130 KP), terminy płatności oraz terminy ZUS, PIT, CIT, VAT i PPK przesuwane z weekendów i świąt. Działa offline. | Przepisy prawa (📚 dane statyczne, z podstawą prawną) |

Nowe zastosowania: „znajdź działkę po GPS”, „wyszukaj ostrzeżenie o partii produktu” i „odczytaj skład po kodzie kreskowym”. [Prompty i scenariusze demo CERT / smog / przetargi](docs/demo/new-skills-launch.md) · [zapis rzeczywistych uruchomień](docs/demo/demo_data.json). Film pokazuje 10 przykładów; pełny katalog obejmuje 25 skilli.


## Nowe scenariusze: praca, adresy i dane

- **„Znajdź oferty Python zdalnie i pokaż osobno B2B/UoP”.** `solid-jobs` zwraca linki i zakres sprawdzonych stron; nie wysyła CV.
- **„Znajdź GPS adresu Marki, Andersa 1”.** `adresy` odczytuje GUGiK; wynik może zasilić wyszukiwanie stacji GIOŚ lub Paczkomatu. Niejednoznaczne miejsca pozostają do wyboru.
- **„Znajdź dane o transporcie i sprawdź daty oraz warunki użycia”.** `otwarte-dane` prowadzi od tematu do metadanych źródła.

Z checkoutu zawierającego nowe skille: `bash install.sh solid-jobs adresy otwarte-dane`.



---

## Historia ceny mieszkania

**„Jak zmieniała się cena mieszkania, które chcę kupić?”** Skill `ceny-deweloperow` pomaga przygotować się do rozmowy z deweloperem: pokazuje opublikowane ceny wybranego lokalu, zmiany w złotych i procentach oraz daty i luki w danych. Korzysta z cenników wydawców na dane.gov.pl. Ceny zawartych transakcji sprawdzisz osobnym skillem [`nieruchomosci`](skills/nieruchomosci/SKILL.md).

Z checkoutu zawierającego skill zainstaluj go przez `bash install.sh ceny-deweloperow`. Agentowi podaj nazwę inwestycji lub dewelopera oraz oznaczenie lokalu i budynku. Możesz też przejść przez przykład w terminalu — od wyszukania inwestycji do historii konkretnego mieszkania:

```bash
python3 skills/ceny-deweloperow/scripts/ceny_deweloperow.py search "Pogonowskiego" --limit 5
python3 skills/ceny-deweloperow/scripts/ceny_deweloperow.py resources 4863 --limit 5
python3 skills/ceny-deweloperow/scripts/ceny_deweloperow.py units 67625 --query "POGO2/A" --limit 5
python3 skills/ceny-deweloperow/scripts/ceny_deweloperow.py history 67625 "POGO2/A/2C"
```

Dla własnej inwestycji użyj identyfikatorów zwróconych przez kolejne komendy. **Pokrycie jest częściowe:** obsługiwane są wybrane schematy plików, a pojedynczy cennik może zawierać tylko jedną datę. Wtedy skill nie stwierdzi, czy cena się zmieniła; można porównać do trzech wskazanych plików. Zwrócona cena nie potwierdza dzisiejszej dostępności lokalu ani pełnej kwoty z dopłatami. [Instrukcja i zakres danych](skills/ceny-deweloperow/SKILL.md) wyjaśniają daty, formaty i porównywanie cenników. Przykładowe zasoby mogą się zmienić.

## Oficjalna ulotka właściwego leku

**„Znajdź ulotkę mojego leku — nazwa, moc i opakowanie muszą się zgadzać”.** Skill `leki` wyszukuje produkty w oficjalnym Rejestrze Produktów Leczniczych. Pokazuje osobne warianty preparatu, substancje czynne i linki do dokumentów; kod kreskowy pozwala dopasować opakowanie.

Z checkoutu zawierającego skill: `bash install.sh leki`. Przykłady w terminalu:

```bash
python3 skills/leki/scripts/leki.py search "Apap" --exact
python3 skills/leki/scripts/leki.py product 100006494
python3 skills/leki/scripts/leki.py barcode 5909990296026
```

Pierwsze użycie pobiera pełny rejestr (około 74 MB); kolejne zapytania korzystają z lokalnego indeksu przez 24 godziny. Wynik zawiera datę danych, rozróżnia moce i postacie, zachowuje brakujące ulotki oraz oznaczenia skasowanych opakowań. Rejestr nie potwierdza dostępności w aptece ani tego, jaki lek należy stosować. [Instrukcja, tryb offline i zakres danych](skills/leki/SKILL.md).

## 🔍 Jak znaleźć skill?

Możesz przeszukiwać rejestr bezpośrednio z poziomu wbudowanego CLI lub skryptu instalatora:

```bash
# Wyświetlenie wszystkich dostępnych skilli
./install.sh list
# lub
python3 scripts/cli.py list

# Wyszukiwanie po frazie kluczowej (np. podatki, faktury, przesyłki)
./install.sh search faktury
python3 scripts/cli.py search paczkomat

# Szczegółowe informacje, źródło i kontrakt danego skilla
./install.sh info biala-lista
python3 scripts/cli.py info krs
```

---

## ⚡ Jak zainstalować skill?

### 1. Automatyczny instalator (zalecany)

Zainstaluj wszystkie lub wybrane skille jednym poleceniem:

```bash
# Instalacja wszystkich skilli w bieżącym projekcie
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash

# Instalacja tylko wybranego skilla (np. inpost, biala-lista)
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s inpost biala-lista

# Instalacja globalna (dla Google Antigravity: ~/.gemini/config/skills)
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s -- --global
```

Wymagania: Bash, Python 3.8+ i curl (przy pobieraniu z sieci). Domyślny katalog to `.claude/skills`, gdy w bieżącym projekcie istnieje `.claude`; w przeciwnym razie `.agents/skills`. Możesz wybrać `--claude`, `--agents` albo `--dir <ścieżka>`. Historyczne `--global` nadal wskazuje `~/.gemini/config/skills`.

```bash
# Podgląd instalacji bez zapisu plików
./install.sh nbp --agents --dry-run --json

# Czysty JSON także przez instalator
./install.sh list --json
```

Pomoc, komunikaty narzędzia zarządzającego oraz instrukcje `SKILL.md` są po angielsku. Nazwy i opisy w polskim katalogu, przykłady pytań oraz dane źródłowe zachowują język polski. `update` zastępuje tylko rozpoznane skille w wybranym katalogu, używając bieżącego checkoutu; nie wykonuje `git pull`. Instalacja zastępuje lokalne zmiany wewnątrz wybranych skilli. [Kontrakt instalatora i CLI](docs/cli.md).

### 2. Instalacja jednym promptem (dla Twojego Agenta AI)

Wklej w oknie czatu ze swoim agentem (Claude Code, Cursor, Windsurf, Antigravity):

```text
Zainstaluj skille inpost oraz biala-lista z repozytorium https://github.com/b44x/ai-polish-skills w katalogu skilli naszego projektu.
```

Agent automatycznie pobierze wymagane pliki i natychmiast uzyska dostęp do nowych możliwości!

### 3. Za pomocą wbudowanego CLI

Jeśli masz sklonowane repozytorium:

```bash
python3 scripts/cli.py install inpost biala-lista
python3 scripts/cli.py update
```

### 4. Claude Code — marketplace pluginów

```bash
/plugin marketplace add b44x/ai-polish-skills
/plugin install polskie-skille@polskie-skille   # wszystkie skille
/plugin install nbp@polskie-skille              # albo pojedynczy skill
```

### 5. Gemini CLI — rozszerzenie

```bash
gemini extensions install https://github.com/b44x/ai-polish-skills
```

---

## 🚀 Jak uruchomić skill?

### Przez Agenta AI (naturalny język)
Po zainstalowaniu skilla agent automatycznie dobiera odpowiedni skrypt na podstawie Twojego pytania:
- *"Sprawdź czy kontrahent o NIP 5260250274 ma aktywne konto na Białej Liście"*
- *"Kto jest w zarządzie spółki o numerze KRS 0000006865 i jak wygląda reprezentacja?"*
- *"Przelicz fakturę na 1500 EUR z dnia 2026-09-25 na PLN zgodnie z kursem podatkowym NBP"*
- *"Gdzie jest najbliższy Paczkomat w Warszawie przy Chmielnej?"*

### Samodzielnie z poziomu terminala
Każdy skill posiada przewidywalny interfejs CLI:

```bash
# Sprawdzenie NIP w Białej Liście VAT
python3 skills/biala-lista/scripts/biala_lista.py nip 5260250274

# Weryfikacja reprezentacji spółki w KRS
python3 skills/krs/scripts/krs.py repr 0000006865

# Przeliczenie faktury walutowej wg Art. 31a VAT z tabeli NBP
python3 skills/nbp/scripts/nbp.py invoice 1500 EUR 2026-09-25

# Wyszukanie Paczkomatów w pobliżu współrzędnych GPS
python3 skills/inpost/scripts/inpost.py near 52.2297 21.0122 --limit 3
```

---

## 🤖 Wspierane agenty i narzędzia

| Środowisko | Obsługa `SKILL.md` | Katalog instalacji |
|---|:---:|---|
| **Claude Code** | Natywna | marketplace pluginów lub `.claude/skills/<skill>/` |
| **Gemini CLI** | Natywna (rozszerzenie) | `gemini extensions install …` |
| **GitHub Copilot (VS Code, CLI)** | Natywna | `.agents/skills/<skill>/`, `.github/skills/<skill>/` lub `.claude/skills/<skill>/` |
| **Google Antigravity (AGY)** | Natywna | `.agents/skills/<skill>/` lub `~/.gemini/config/skills/` |
| **Cursor** | Przez `.cursorrules` / context | `.agents/skills/<skill>/` |
| **Windsurf** | Przez `.windsurfrules` | `.agents/skills/<skill>/` |
| **OpenAI Codex** | Natywna | `.agents/skills/<skill>/` lub `~/.agents/skills/<skill>/` |
| **Inne agenty** | Standard CLI & JSON | Dowolny katalog ze skryptami |

---

## 🛠 Jak dodać własny skill?

Dodanie nowego skilla do oficjalnego rejestru odbywa się przez prosty, 8-krokowy proces w Pull Requeście:

1. Wybierz polską usługę lub rejestr publiczny.
2. Zweryfikuj oficjalność źródła i warunki korzystania.
3. Skopiuj szablon `templates/skill/` do `skills/<twoj-skill>/`.
4. Opisz instrukcje w `SKILL.md`.
5. Uzupełnij metadane w nagłówku YAML (manifest).
6. Napisz skrypt w `scripts/<twoj-skill>.py` (Python 3.8+ stdlib, JSON na stdout).
7. Uruchom walidator (`python3 scripts/validate_skills.py`) oraz testy (`python3 scripts/test_skills.py`).
8. Otwórz Pull Request do gałęzi `dev`.

Szczegółowy podręcznik contributorów oraz checklista PR znajduje się w pliku **[CONTRIBUTING.md](CONTRIBUTING.md)**.

---

## 🌐 polskieskille.pl & Rejestr

Projekt generuje deterministyczny, statyczny rejestr w formatach:
- `registry/registry.json` — pełny indeks skilli, metadanych, kategorii i plików.
- `registry/registry.min.json` — zminifikowana wersja dla szybkiego pobierania webowego.
- `registry/schema.json` — oficjalny JSON Schema dla walidacji.

Strona **polskieskille.pl** bezpośrednio konsumuje ten rejestr, prezentując interaktywny katalog, statystyki i dokumentację.

## Autor i licencja

Twórca i maintainer: **Michell Hoduń** ([@b44x](https://github.com/b44x)).  
Repozytorium: [github.com/b44x/ai-polish-skills](https://github.com/b44x/ai-polish-skills).  
Licencja: [MIT License](LICENSE).
