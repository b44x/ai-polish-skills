<p align="center">
  🇵🇱 <b>Polski</b> | 🇬🇧 <a href="README_EN.md">English</a>
</p>

# ai-polish-skills 🇵🇱

Oficjalny, modułowy zbiór skilli dla agentów sztucznej inteligencji (`SKILL.md`), dostosowanych do **polskiego rynku, usług, urzędów i API**.

> 🌐 Oficjalna strona projektu: [polskieskille.pl](https://polskieskille.pl)

Każdy skill w repozytorium zapewnia:
- Standaryzowaną definicję `SKILL.md` zgodną z otwartym standardem agentów AI (*Progressive Disclosure*).
- Niezależne skrypty CLI w Pythonie 3 (zero zewnętrznych zależności, wyłącznie biblioteka standardowa).
- Komunikację przez czysty JSON na `stdout` i ustrukturyzowane błędy na `stderr`.
- Kompletne referencje pól, schematów i statusów.

---

## Dostępne skille

| Skill | Opis | Słowa kluczowe / Triggery |
|---|---|---|
| [`biala-lista`](skills/biala-lista/SKILL.md) | Oficjalny Wykaz podatników VAT Ministerstwa Finansów (**Biała Lista VAT**). Weryfikacja statusu podatnika VAT (czynny/zwolniony), danych rejestrowych firmy (KRS, REGON, adres) oraz weryfikacja konta bankowego przed przelewem B2B (split payment, limit 15 tys. zł). | NIP, REGON, status VAT, "sprawdź NIP", "biała lista", "rachunek na białej liście", split payment |
| [`inpost`](skills/inpost/SKILL.md) | **InPost i Paczkomaty w całej Polsce**. Śledzenie przesyłek po 24-cyfrowym numerze, wyszukiwarka Paczkomatów po kodzie (np. WAW01M), ulicy, mieście oraz współrzędnych GPS (odległość w metrach, godziny 24/7, Strefa Łatwego Dostępu, płatności, nawigacja Google Maps). | InPost, Paczkomat, "gdzie moja paczka", "status przesyłki InPost", "najbliższy paczkomat" |
| [`filmweb`](skills/filmweb/SKILL.md) | Baza filmów, seriali i ludzi kina **Filmweb.pl**. Wyszukiwanie tytułów, oceny użytkowników i krytyków, pełna obsada, daty premier oraz dostępność na platformach VOD wraz z cenami w PLN. | Filmweb, ocena filmu, "gdzie obejrzę", "kto grał w", polskie recenzje, seriale |

---

## ⚡ Szybka instalacja automatyczna

Możesz zainstalować wszystkie skille lub wybrany jednym poleceniem w terminalu:

```bash
# Instalacja wszystkich skilli w Twoim bieżącym projekcie
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash

# Instalacja tylko wybranego skilla (np. inpost)
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s inpost

# Instalacja globalna (dostępna we wszystkich projektach Google Antigravity)
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s -- --global
```

Instalator **automatycznie wykrywa środowisko**, w którym pracujesz (Google Antigravity, Claude Code, Cursor, Windsurf) i kopiuje pliki do właściwego katalogu.

---

## 🤖 Instalacja jednym promptem (dla Agenta AI)

Jeśli pracujesz z agentem AI (Google Antigravity, Claude Code, Cursor, Windsurf), wklej mu w oknie czatu poniższe polecenie:

```text
Zainstaluj skille inpost oraz biala-lista z repozytorium https://github.com/b44x/ai-polish-skills w katalogu skilli naszego projektu.
```

Agent sam sklonuje lub pobierze wymagane katalogi i natychmiast zacznie z nich korzystać!

---

## Instalacja ręczna

### 1. Google Antigravity (AGY)

#### Poziom projektu (zalecane):
```bash
mkdir -p .agents/skills
ln -s /sciezka/do/ai-polish-skills/skills/biala-lista .agents/skills/biala-lista
ln -s /sciezka/do/ai-polish-skills/skills/inpost .agents/skills/inpost
```

#### Poziom globalny (dla wszystkich projektów na komputerze):
```bash
mkdir -p ~/.gemini/config/skills
ln -s /sciezka/do/ai-polish-skills/skills/biala-lista ~/.gemini/config/skills/biala-lista
ln -s /sciezka/do/ai-polish-skills/skills/inpost ~/.gemini/config/skills/inpost
```

### 2. Claude Code

```bash
mkdir -p .claude/skills
ln -s /sciezka/do/ai-polish-skills/skills/inpost .claude/skills/inpost
```

### 3. Cursor / Windsurf / Inne narzędzia

Wystarczy dodać odwołanie w regułach projektu (np. w `.cursorrules` lub `.windsurfrules`):

```markdown
Gdy użytkownik pyta o polskie firmy, NIP lub podatki, korzystaj z instrukcji w skills/biala-lista/SKILL.md.
Gdy pyta o paczki, przesyłki lub Paczkomaty InPost, korzystaj z skills/inpost/SKILL.md.
```

### 4. Uruchamianie bezpośrednio z terminala (CLI)

Wszystkie skrypty działają samodzielnie na standardowym Pythonie 3:

```bash
# Sprawdzenie kontrahenta na Białej Liście VAT
python3 skills/biala-lista/scripts/biala_lista.py nip 5252344078

# Weryfikacja konta bankowego kontrahenta przed przelewem
python3 skills/biala-lista/scripts/biala_lista.py check 5252344078 93103015080000000504162006

# Wyszukanie najbliższych Paczkomatów InPost po współrzędnych GPS
python3 skills/inpost/scripts/inpost.py near 52.2297 21.0122 --limit 3
```

---

## Dobre praktyki tworzenia skilli

Gdy tworzysz nowego skilla dla `ai-polish-skills`:

1. **Progressive Disclosure:** Główny plik `SKILL.md` powinien być zwięzły (< 500 linii). Szczegółowe schematy odpowiedzi, słowniki i teorię przenoś do katalogu `references/`.
2. **Deterministyczne skrypty zamiast halucynacji:** Jeśli zadanie wymaga odpytania API, parsowania lub obliczeń, zamknij to w skrypcie `scripts/<name>.py`. Agent powinien wykonać skrypt, zamiast zgadywać.
3. **Zero zewnętrznych zależności:** Skrypty muszą działać na standardowym Pythonie 3.8+ (`urllib`, `json`, `argparse`) bez wymogu instalacji pakietów przez `pip`.
4. **Czysty JSON:** Skrypty zawsze zwracają poprawny JSON na `stdout`, a błędy w formacie `{"error": "...", "type": "..."}` na `stderr`.
5. **Kody wyjścia:** `0` (sukces), `2` (nie znaleziono), `64` (błąd walidacji / złe argumenty), `69` (błąd sieci / API).

---

## Walidacja jakości

Wszystkie commity i Pull Requesty są automatycznie sprawdzane w GitHub Actions:

```bash
python3 scripts/validate_skills.py
```

## Publikacja wydań

Projekt posiada w pełni zautomatyzowany skrypt publikacji wydań:

```bash
python3 scripts/release.py
```

---

## Autor i licencja

Projekt stworzony i rozwijany przez: **Michell Hoduń** ([@b44x](https://github.com/b44x) / [ai-polish-skills](https://github.com/b44x/ai-polish-skills)).

Licencja: [MIT License](LICENSE).
