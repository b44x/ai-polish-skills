# Trzy nowe zastosowania Polskich Skilli

Materiały do publikacji w kolejności: CERT → smog → przetargi. Każdy post kieruje do jednego zastosowania i konkretnej komendy instalacji. Poniższe teksty są szkicami; nie zostały opublikowane.

## 1. CERT — link z wiadomości

**Prompt:** „Sprawdź domenę cert.pl na liście ostrzeżeń CERT Polska. Wyjaśnij, co oznacza wynik, bez otwierania strony”. W pokazie z podejrzanym adresem podmień domenę na wybrany aktualny wpis listy CERT i ponownie zapisz rzeczywisty wynik.

**Instalacja:** `./install.sh cert-pl`

**Scenariusz 25 sekund:**

| Czas | Obraz i treść |
|---|---|
| 0–4 s | „Dostałeś link w SMS? Sprawdź, czy jest na liście CERT”. |
| 4–10 s | Prompt, wybór `cert-pl`, wywołanie `check`. |
| 10–19 s | Rzeczywisty wynik: domena, ewentualny wpis i czas pobrania listy. |
| 19–22 s | „Brak wpisu nie oznacza, że strona jest bezpieczna”. |
| 22–25 s | Komenda instalacji i polskieskille.pl. |

**Szkic posta:**

> Link z SMS-a można sprawdzić w oficjalnej liście CERT Polska jednym pytaniem do swojego agenta. Nowy skill `cert-pl` sprawdza domenę i jej subdomeny bez odwiedzania podejrzanego adresu. Pokazuje też datę pobrania listy. Brak wpisu nie jest gwarancją bezpieczeństwa. Kod i instalacja: https://github.com/b44x/ai-polish-skills

Domyślne demo używa `cert.pl` i pokazuje brak wpisu. Nie przedstawiaj tego wyniku jako wykrytego oszustwa ani jako certyfikatu bezpieczeństwa. Dla dodatniego wyniku ustaw `DEMO_CERT_DOMAIN` na domenę z aktualnej listy; na filmie pokaż ją jako tekst, nie zachęcaj do otwierania.

## 2. Smog — powietrze w okolicy

**Prompt:** „Sprawdź jakość powietrza w pobliżu 50.06, 19.94. Podaj najbliższą stację GIOŚ, PM10, PM2.5 i godzinę każdego pomiaru”.

**Instalacja:** `./install.sh smog`

**Scenariusz 25 sekund:**

| Czas | Obraz i treść |
|---|---|
| 0–4 s | „Jaki jest smog w Twojej okolicy?” |
| 4–10 s | Prompt ze współrzędnymi, wybór `smog`, wywołanie `near`. |
| 10–20 s | Nazwa stacji, odległość, indeks GIOŚ, PM10 i PM2.5 z godzinami. |
| 20–25 s | „Źródło: GIOŚ. Pomiary wstępne”. Komenda instalacji. |

**Szkic posta:**

> „Jaki jest smog w mojej okolicy?” Nowy skill `smog` pobiera dane z GIOŚ: najbliższą stację, polski indeks jakości powietrza i ostatnie dostępne pomiary. Każdy wynik ma jednostkę i godzinę, a brak danych pozostaje brakiem danych. Działa bez klucza API i instalowania bibliotek Pythona. https://github.com/b44x/ai-polish-skills

## 3. Przetargi — ogłoszenia dla wykonawców

**Prompt:** „Znajdź 3 ogłoszenia BZP z ostatnich 30 dni z kodem CPV 72413000-8 — projektowanie stron WWW. Podaj zamawiających, zakres, terminy z ogłoszeń i linki do źródeł”.

**Instalacja:** `./install.sh przetargi`

**Scenariusz 30 sekund:**

| Czas | Obraz i treść |
|---|---|
| 0–5 s | „Robisz strony internetowe? Sprawdź ogłoszenia BZP przez agenta”. |
| 5–12 s | Prompt, wybór CPV, jawny zakres dat i limit 3. |
| 12–23 s | Wyniki: tytuł, zamawiający, termin z ogłoszenia, link do BZP. |
| 23–26 s | „CPV może być dodatkowy. Sprawdź zakres i późniejsze zmiany”. |
| 26–30 s | Komenda instalacji i adres repozytorium. |

**Szkic posta:**

> Do Polskich Skilli doszło wyszukiwanie zamówień publicznych. `przetargi` czyta oficjalne ogłoszenia BZP, filtruje po CPV, frazie, województwie zamawiającego i datach. Wyniki zawierają linki i terminy ze źródła, a pełne ogłoszenie można pobrać kolejnym poleceniem. Przydatne dla freelancerów i firm szukających zleceń. Sprawdź: https://github.com/b44x/ai-polish-skills

## Rzeczywiste dane i odtwarzanie

[demo_data.json](demo_data.json) zawiera dziesięć scen, w tym trzy nowe zapisane uruchomienia: komendy, kody wyjścia, czas wykonania, czas pobrania, pełny JSON i karty wyników. Nie używa fixture’ów testowych. Pomiary i ogłoszenia zmieniają się — przed publikacją odśwież dane:

```bash
python3 docs/demo/capture.py --only cert-pl smog przetargi
# Ponowienie jednej sceny z zachowaniem pozostałych:
python3 docs/demo/capture.py --only przetargi
```

Główny [film MP4](demo.mp4) i [podgląd GIF](demo.gif) obejmują dotychczasowe siedem scen oraz CERT (około 57–64 s), smog (64–71 s) i przetargi (71–79 s). Całość z intro i zakończeniem trwa około 84 s. Scenariusze powyżej służą krótkim materiałom promocyjnym. Materiały nie zostały opublikowane w serwisach społecznościowych.

```bash
./docs/demo/generate_demo.sh --reuse-data
```

Wymagania renderera pozostają takie jak w [instrukcji demo](README.md). Repozytorium utrzymuje jeden komplet: `demo.mp4`, `demo.gif` i `demo_data.json`. Przed publikacją obejrzyj render i sprawdź czytelność dłuższych nazw ogłoszeń.

## Ocena zainteresowania po premierze

Przez 14 dni zapisuj ręcznie datę publikacji, adres posta, wyświetlenia, kliknięcia dostępne w panelu platformy, przyrost gwiazdek i zgłoszenia dotyczące skilla. Porównaj z 14 dniami przed premierą. Obecny lokalny instalator nie mierzy instalacji — nie wyciągaj ich liczby z samych wyświetleń. Decyzję o kolejnych integracjach oprzyj na pytaniach użytkowników i powtarzających się zastosowaniach.
