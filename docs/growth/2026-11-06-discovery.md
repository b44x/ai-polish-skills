# Pakiet premierowy: praca, adresy i otwarte dane

Status: materiały przygotowane do przeglądu; żadnych postów ani wiadomości nie opublikowano. Demo należy nagrać z bieżącego uruchomienia. Wyniki, liczby ofert i dostępność źródeł mogą się zmienić. Nie zastępuj awarii lub braku wyników fikcyjnym sukcesem.

## Instalacja wspólna

Przed wydaniem na `main`, z checkoutu gałęzi PR:

```bash
git clone --branch skill/adresy-otwarte-dane https://github.com/b44x/ai-polish-skills.git
cd ai-polish-skills
bash install.sh praca adresy otwarte-dane
```

Instalator wybierze `.agents/skills` lub `.claude/skills` zgodnie ze środowiskiem. Zainstaluj pojedynczy skill przez `bash install.sh praca` (analogicznie `adresy`, `otwarte-dane`). Na Windows skopiuj wybrany folder z `skills/` do katalogu skilli agenta i uruchamiaj skrypt przez `py`. Nowe skille nie wymagają pip ani kluczy API.

Po wydaniu na `main` będzie można używać standardowego instalatora z głównego README. Dopóki nie ma wydania, nie reklamować komendy pobierającej `main` jako instalacji tych nowości.

## Praca

**Opis marketingowy:** Zapytaj o pracę po polsku. Otrzymaj konkretne oferty SOLID.Jobs z linkami, trybem pracy i widełkami.

**Korzyść:** Mniej ręcznego porównywania ogłoszeń; widoczne różnice B2B/UoP, walut i okresów wynagrodzenia. Odczyt bez konta, bez wysyłania CV. Zakres obejmuje jeden portal, a nie całą Polskę.

**5 pytań do agenta:**

1. „Znajdź oferty Python zdalnie. Sprawdź maksymalnie trzy strony i pokaż, czy są kolejne”.
2. „Szukam pracy w marketingu w Warszawie. Pokaż firmę, widełki i link”.
3. „Znajdź oferty Java dla seniora w Krakowie”.
4. „Pokaż oferty Python z dolnymi widełkami co najmniej 20 tys. PLN miesięcznie; zaznacz, czy próg spełnia B2B czy UoP”.
5. „Pokaż statystyki ofert IT z SOLID.Jobs, oddzielając B2B od UoP i podając czas aktualizacji”.

**3 demonstracje:**

| Scenariusz | Komenda z korzenia repo | Co pokazać |
|---|---|---|
| Praca zdalna w jednym pytaniu | `python3 skills/praca/scripts/praca.py search Python --remote --pages 3` | Linki i tryb pracy; `next_page`, żeby nie sugerować kompletności |
| Uczciwe widełki | `python3 skills/praca/scripts/praca.py search Python --min-pln-month 20000 --limit 50` | Obie formy umowy; nie zamieniać B2B w kwotę „na rękę” |
| Sygnały z rynku portalu | `python3 skills/praca/scripts/praca.py stats --division IT` | Liczba ogłoszeń, próbki płac, czas źródłowy; podpis „SOLID.Jobs” |

**SEO:** praca Python zdalnie, oferty pracy AI agent, widełki B2B UoP, SOLID.Jobs API, polskie skille praca, Python bez pip.

**Film 25–30 s:** 0–5 s pytanie o Python zdalnie; 5–15 s uruchomienie skryptu; 15–23 s trzy oferty z linkami i formami umowy; 23–30 s informacja o zakresie stron i instalacja. Nie pokazywać zmyślonych wynagrodzeń; gdy brak dopasowań, zmienić jawnie frazę lub pokazać ten rezultat.

**X — propozycja:**

> „Znajdź pracę Python zdalnie” → oferty, linki, widełki i rodzaj umowy. Nowy skill `praca` w ai-polish-skills korzysta z oficjalnego API SOLID.Jobs. Python bez pip i kluczy. Podaje też, ile stron sprawdził. Kod i demo: https://github.com/b44x/ai-polish-skills

**LinkedIn — propozycja:**

> Dodaliśmy do ai-polish-skills wyszukiwanie ofert pracy z SOLID.Jobs. Agent może znaleźć ogłoszenia według frazy, miasta i doświadczenia, a potem odfiltrować pobrane strony po pracy zdalnej i widełkach PLN/miesiąc. Zachowujemy różnice B2B/UoP oraz źródłowe daty. To otwarta integracja dla kandydatów i twórców asystentów. Przyda się feedback: jaki filtr najbardziej skróciłby Wam poszukiwania? https://github.com/b44x/ai-polish-skills

**Reddit — propozycja:**

> Tytuł: Zrobiłem otwarty skill do wyszukiwania ofert SOLID.Jobs przez agenta — Python bez pip
>
> Jestem współtwórcą ai-polish-skills. Dodaliśmy odczyt publicznego API ofert i statystyk SOLID.Jobs. Skrypt nie wysyła CV, pokazuje źródło, strony i osobne formy wynagrodzenia. Filtry zdalności działają na pobranych stronach, więc wynik nie udaje pełnego przeglądu rynku. Kod: https://github.com/b44x/ai-polish-skills. Chętnie sprawdzę zgłoszenia błędnych dopasowań — bez danych osobowych kandydatów.

**Instalacja:** `bash install.sh praca` z checkoutu gałęzi PR.

## Adresy

**Opis marketingowy:** Polski adres → współrzędne GPS z GUGiK. Jeden krok do znalezienia usług w okolicy.

**Korzyść:** Użytkownik podaje adres, zamiast szukać współrzędnych ręcznie. Agent zachowuje warianty dopasowania i rozróżnia punkt budynku, ulicę oraz miejscowość.

**5 pytań do agenta:**

1. „Znajdź współrzędne adresu Marki, Andersa 1”.
2. „Jaki punkt adresowy jest najbliżej 52.229, 21.020?”.
3. „Sprawdź, czy Warszawa oznacza jednoznacznie jedną miejscowość w rejestrze”.
4. „Znajdź ulicę Andersa w Markach i powiedz, czy wynik wskazuje budynek”.
5. „Ustal GPS tego adresu i użyj go do znalezienia najbliższej stacji GIOŚ, podając jej odległość”.

**3 demonstracje:**

| Scenariusz | Komenda / kroki | Co pokazać |
|---|---|---|
| Adres → GPS | `python3 skills/adresy/scripts/adresy.py search "Marki, Andersa 1"` | `latitude`, `longitude`, numer i jednostkę administracyjną |
| Niejednoznaczna Warszawa | `python3 skills/adresy/scripts/adresy.py search Warszawa` | Różne SIMC i jednostki; agent nie wybiera pierwszego wyniku automatycznie |
| GPS → adres | `python3 skills/adresy/scripts/adresy.py reverse 52.229 21.020` | Pobliską ulicę i numer, dystans; nie twierdzić, że to lokalizacja wewnątrz budynku |

Dodatkowe połączenie z katalogiem: po rozstrzygnięciu adresu przekaż uzyskane liczby do `smog near LAT LON` lub `inpost near LAT LON`. Nie zapisuj na stałe współrzędnych z wcześniejszego nagrania jako nowego wyniku API.

**SEO:** współrzędne adresu, geokodowanie Polska, adres GPS GUGiK, reverse geocoding Poland, agent AI Geoportal, PRG adresy.

**Film 20–25 s:** 0–5 s pełny adres; 5–12 s wynik GPS z podpisem GUGiK; 12–20 s pytanie „a co z samą Warszawą?” i lista wariantów; 20–25 s instalacja. To pokazuje użyteczność i rzeczywisty problem danych.

**X — propozycja:**

> Agent zna adres, ale potrzebuje GPS do znalezienia pobliskiej usługi? `adresy` w ai-polish-skills odpytuje GUGiK i zachowuje warianty dopasowania. Działa też GPS → pobliski adres. Python bez pip. https://github.com/b44x/ai-polish-skills

**LinkedIn — propozycja:**

> Dodaliśmy brakujący krok do asystentów lokalnych: polski adres na współrzędne z oficjalnego GUGiK UUG. Wynik można przekazać do wyszukiwania stacji GIOŚ czy Paczkomatów. Skill rozróżnia miejscowość, ulicę i punkt adresowy, a przy niejednoznacznej nazwie pokazuje warianty. Kod, testy i przykłady: https://github.com/b44x/ai-polish-skills

**Reddit — propozycja:**

> Tytuł: Polski adres na GPS z GUGiK — mały skill Python dla agentów
>
> W ai-polish-skills dodaliśmy klienta publicznego geokodera GUGiK. Przydaje się przed pytaniem o usługi „w pobliżu”. Uważamy na układ współrzędnych i niejednoznaczne nazwy: samo „Warszawa” może dać kilka miejscowości. Bez pip i klucza. Repo projektu, przy którym pracuję: https://github.com/b44x/ai-polish-skills. Przyjmujemy zgłoszenia z przykładami publicznych adresów.

**Instalacja:** `bash install.sh adresy` z checkoutu gałęzi PR.

## Otwarte dane

**Opis marketingowy:** Zapytaj o temat. Znajdź polski zbiór danych, źródło i warunki jego użycia.

**Korzyść:** Szybszy początek analizy i budowy integracji; daty, formaty i informacje licencyjne pozostają przy rekordzie. Katalog nie obiecuje poprawności każdego pliku dostawcy.

**5 pytań do agenta:**

1. „Znajdź zbiory o transporcie publicznym na dane.gov.pl”.
2. „Poszukaj źródeł cen ofertowych mieszkań; nie myl ich z cenami transakcyjnymi”.
3. „Pokaż zasoby zbioru 80, ich formaty i linki”.
4. „Sprawdź metadane i warunki ponownego użycia zasobu 1800”.
5. „Znajdź dane o edukacji i powiedz, z jakiego okresu pochodzą oraz kto je publikuje”.

**3 demonstracje:**

| Scenariusz | Komenda | Co pokazać |
|---|---|---|
| Temat → źródło | `python3 skills/otwarte-dane/scripts/otwarte_dane.py search transport --limit 3` | Tytuły, instytucje i linki zamiast wymyślonych API |
| Zbiór → zasób | `python3 skills/otwarte-dane/scripts/otwarte_dane.py resources 80 --limit 2` | Format pliku, ID i następna strona |
| Metadane przed analizą | `python3 skills/otwarte-dane/scripts/otwarte_dane.py resource 1800` | Daty, opis i link; brak warunków nie oznacza automatycznie CC0 |

**SEO:** dane.gov.pl API, otwarte dane Polska, wyszukiwarka zbiorów danych, Polish open data agent, źródła danych do analizy, publiczne API Polska.

**Film 25 s:** 0–5 s pytanie o transport; 5–12 s trzy znalezione zbiory; 12–20 s zasoby jednego zbioru i data aktualizacji; 20–25 s instalacja oraz informacja „metadane i linki, bez pobierania plików dostawców”.

**X — propozycja:**

> „Znajdź polskie dane o transporcie” → zbiór, dostawca, format i link. Nowy skill `otwarte-dane` przeszukuje oficjalne API dane.gov.pl i zachowuje metadane do weryfikacji źródła. Python bez pip i klucza. https://github.com/b44x/ai-polish-skills

**LinkedIn — propozycja:**

> Dobra analiza zaczyna się od źródła. Do ai-polish-skills dodaliśmy wyszukiwanie zbiorów i zasobów dane.gov.pl. Agent może wskazać dostawcę, aktualizację, format i warunki wykorzystania przed rozpoczęciem analizy. To także punkt startowy dla osób chcących dodać kolejne integracje do projektu. Kod i przykłady: https://github.com/b44x/ai-polish-skills

**Reddit — propozycja:**

> Tytuł: Otwarty skill do szukania zbiorów na dane.gov.pl — z metadanymi i paginacją
>
> W projekcie ai-polish-skills dodaliśmy prosty klient oficjalnego katalogu. Szuka zbiorów, wypisuje zasoby i zachowuje daty oraz informacje o licencji. Nie pobiera automatycznie plików z obcych serwerów i nie przedstawia starego CSV jako świeżych danych. Repo, przy którym pracuję: https://github.com/b44x/ai-polish-skills. Jakich zbiorów najtrudniej Wam dziś szukać?

**Instalacja:** `bash install.sh otwarte-dane` z checkoutu gałęzi PR.

## Dystrybucja i wkład społeczności

Po zatwierdzeniu i udostępnieniu kodu: jeden krótki film na skill, post techniczny z przykładem wyniku i ograniczeniami, potem odpowiedzi na rzeczywiste pytania użytkowników. Dostosować post do zasad danej społeczności; ujawnić udział w projekcie. Nie publikować dziewięciu identycznych ogłoszeń naraz.

Mierzyć użyteczność: liczbę powtarzalnych zgłoszeń, odsetek zgłoszeń zakończonych poprawką, czas od instalacji do pierwszego działającego wywołania w dobrowolnych testach oraz wkłady contributorów. Stars traktować jako sygnał pomocniczy. Brak telemetrii w nowych skryptach; `campaign` SOLID.Jobs jest udokumentowany i nie obejmuje danych użytkownika dodawanych przez nas.

Propozycje kolejnych małych wkładów (nie utworzono issues): testy wyszukiwania z polskimi znakami, zgłoszenia zmian schematu UUG z publicznym przykładem, udokumentowanie aktualnych warunków czytelnika EIPA, weryfikacja dostępu PKP PLK, test par pytań PL/EN dla wyboru skilla. Szablon zgłoszenia: wersja skilla/Pythona, polecenie bez danych prywatnych, kod wyjścia, oczekiwane zachowanie, czas i źródło.
