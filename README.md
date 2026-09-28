<p align="center">
  🇵🇱 <b>Polski</b> | 🇬🇧 <a href="README_EN.md">English</a>
</p>

# ai-polish-skills 🇵🇱

Oficjalny rejestr i katalog otwartych skilli dla agentów sztucznej inteligencji, dostosowanych do **polskiego rynku, usług, urzędów i API**.

> 🌐 Warstwa discovery i katalog online: **[polskieskille.pl](https://polskieskille.pl)**  
> 📦 Open-source core i rejestr: **[github.com/b44x/ai-polish-skills](https://github.com/b44x/ai-polish-skills)**

---

## Demo

**See Polskie Skille in action** — jedno pytanie po polsku, agent wybiera skill, skill odpytuje oficjalne polskie źródło (MF, KRS, NBP, IMGW-PIB, NFZ, Sejm RP, InPost) i zwraca czytelny wynik. Wszystkie dane w filmie pochodzą z rzeczywistych uruchomień skilli.

<p align="center">
  <a href="docs/demo/demo.mp4"><img src="docs/demo/demo.gif" alt="Polskie Skille — demo: agent AI korzysta z polskich API i danych publicznych" width="960"></a>
</p>

<p align="center">
  ▶️ <a href="docs/demo/demo.mp4"><b>Obejrzyj pełne demo (MP4, 1080p, 95 s)</b></a> · 🌐 <a href="https://polskieskille.pl">polskieskille.pl</a> · 🛠 <a href="docs/demo/README.md">jak wygenerować demo</a>
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
| [`biala-lista`](skills/biala-lista/SKILL.md) | **Biała Lista VAT** `[finance]` | Weryfikacja statusu podatnika VAT, NIP, REGON, KRS i kont bankowych przed przelewem B2B (split payment). | Ministerstwo Finansów (🏛 oficjalne API) |
| [`nbp`](skills/nbp/SKILL.md) | **Narodowy Bank Polski** `[finance]` | Średnie kursy walut (tabela A i B), ceny złota oraz przeliczanie faktur walutowych na PLN wg art. 31a ustawy o VAT. | Narodowy Bank Polski (🏛 oficjalne API) |
| [`terminy`](skills/terminy/SKILL.md) | **Terminy, dni robocze i święta** `[utilities]` | Dni robocze, święta (z Wigilią), wymiar czasu pracy (art. 130 KP), terminy płatności oraz terminy ZUS, PIT, CIT, VAT i PPK przesuwane z weekendów i świąt. Działa offline. | Przepisy prawa (📚 dane statyczne, z podstawą prawną) |
| [`krs`](skills/krs/SKILL.md) | **Krajowy Rejestr Sądowy** `[legal]` | Odpisy spółek i fundacji, skład zarządu, prokurenci, kapitał zakładowy oraz zasady reprezentacji (kto może podpisać umowę). | Ministerstwo Sprawiedliwości (🏛 oficjalne API) |
| [`inpost`](skills/inpost/SKILL.md) | **InPost & Paczkomaty** `[logistics]` | Śledzenie paczek po 24-cyfrowym numerze, wyszukiwarka Paczkomatów po kodzie, ulicy, mieście lub GPS z odległością. | InPost ShipX (🔗 public API) |
| [`filmweb`](skills/filmweb/SKILL.md) | **Filmweb** `[entertainment]` | Baza filmów, seriali, ocen krytyków/widzów, obsada, daty premier oraz platformy VOD z cenami w PLN. | Filmweb.pl (🔗 reverse-engineered API) |
| [`imgw`](skills/imgw/SKILL.md) | **IMGW-PIB Pogoda i Alerty** `[public_data]` | Oficjalne dane pogodowe (temperatura, ciśnienie, wiatr, opady) z 62 stacji w Polsce, ostrzeżenia meteo/hydro oraz stany rzek. | IMGW-PIB (🏛 oficjalne API) |
| [`sejm`](skills/sejm/SKILL.md) | **Sejm RP** `[legal]` | Baza posłów, komisji, wyniki głosowań imiennych i klubowych, druki sejmowe oraz etapy procesu legislacyjnego. | Kancelaria Sejmu (🏛 oficjalne API) |
| [`nfz`](skills/nfz/SKILL.md) | **NFZ Kolejki i Czas Oczekiwania (PCUŚ)** `[health]` | Oficjalne dane o czasie oczekiwania na świadczenia (rezonans, tomografia, poradnie), liczba oczekujących, tryb stabilny i pilny oraz wyszukiwanie placówek w promieniu km. | Narodowy Fundusz Zdrowia (🏛 oficjalne API) |

---

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

Instalator **automatycznie wykrywa** Twoje środowisko (Claude Code, Antigravity, Cursor, Windsurf) i instaluje skille we właściwej ścieżce.

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

## Support the project

Polskie Skille to projekt open source rozwijający ekosystem polskich narzędzi dla agentów AI. Wsparcie finansowe pomaga w utrzymaniu i ciągłym rozwoju projektu:

- Rozwoju kolejnych polskich integracji (GUS/BIR, CEIDG, IMGW, e-Doręczenia, KSeF).
- Rozbudowie standardu `SKILL.md` i kompatybilności z agentami AI (Claude Code, Cursor, Windsurf, Antigravity).
- Utrzymaniu infrastruktury testów, walidatora i publicznego rejestru na [polskieskille.pl](https://polskieskille.pl).
- Zapewnieniu bezpieczeństwa, stabilności i bieżącej weryfikacji API.

Możesz wesprzeć projekt bezpośrednio przez **[GitHub Sponsors (github.com/sponsors/b44x)](https://github.com/sponsors/b44x)** (wsparcie comiesięczne lub jednorazowe):

| Poziom | Kwota | Typ | Przeznaczenie |
|---|---|---|---|
| **Supporter** | **$3** / mies. | Monthly | Wsparcie bieżącego utrzymania projektu open source |
| **AI Builder** | **$10** / mies. | Monthly | Wsparcie tworzenia i weryfikacji nowych polskich skilli |
| **Polish AI** | **$25** / mies. | Monthly | Wsparcie infrastruktury testowej, rejestru i integracji z agentami |
| **Company** | **$100** / mies. | Monthly | Wsparcie ekosystemu przez firmy wdrażające agentów AI w Polsce |
| **Coffee** | **$10** | One-time | Jednorazowe docenienie pracy twórcy |

Każda forma wsparcia pozwala poświęcić więcej czasu na rozwój, jakość i stabilność polskich narzędzi AI.

---

## Autor i licencja

Twórca i maintainer: **Michell Hoduń** ([@b44x](https://github.com/b44x)).  
Repozytorium: [github.com/b44x/ai-polish-skills](https://github.com/b44x/ai-polish-skills).  
Licencja: [MIT License](LICENSE).

