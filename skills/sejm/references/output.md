# Sejm RP CLI — Dokumentacja Wyjścia i Schematów Danych

Wszystkie polecenia zwracają ustrukturyzowany format JSON na standardowym wyjściu (`stdout`), a błędy na `stderr`.
Brakujące wartości zwracane są jako `null`, a puste zbiory jako `[]`.

---

## 1. `mps` (lub `mp`)

Pobiera bazę posłów na Sejm RP (domyślnie X kadencja).

### Wyszukiwanie / lista:
`python3 scripts/sejm.py mps [--search <nazwisko>] [--club <klub>] [--district <okręg>]`

| Pole | Typ | Opis |
|---|---|---|
| `id` | int | Unikalny identyfikator posła w bazie Sejmu RP |
| `firstLastName` | string | Imię i nazwisko posła (np. `"Szymon Hołownia"`) |
| `club` | string | Skrót klubu lub koła poselskiego (np. `"PiS"`, `"KO"`, `"Polska2050"`, `"PSL-TD"`, `"Konfederacja"`, `"Lewica"`, `"Razem"`, `"niez."`) |
| `districtName` | string | Siedziba okręgowej komisji wyborczej (np. `"Białystok"`, `"Gdańsk"`, `"Warszawa"`) |
| `districtNum` | int | Numer okręgu wyborczego |
| `voivodeship` | string | Województwo |
| `email` | string | Oficjalny adres e-mail w domenie `@sejm.pl` |
| `active` | bool | Czy mandat poselski jest aktywny |
| `profession` | string | Wykonywany zawód zgłoszony przez posła |

### Szczegóły posła i komisje:
`python3 scripts/sejm.py mps --id <id>`

Dodatkowe pola:
- `birthDate`, `birthLocation`, `educationLevel`, `numberOfVotes`, `oathDate`
- `committees`: lista komisji sejmowych, w których zasiada poseł, wraz z pełnioną funkcją (`"przewodniczący"`, `"zastępca przewodniczącego"`, `"członek"`).

---

## 2. `voting`

Pobiera szczegółowe wyniki pojedynczego głosowania, zestawienie klubowe oraz głos konkretnego posła.

`python3 scripts/sejm.py voting <posiedzenie> <głosowanie> [--mp <nazwisko_lub_id>]`

| Pole | Typ | Opis |
|---|---|---|
| `term` | int | Numer kadencji (np. `10`) |
| `sitting` | int | Numer posiedzenia Sejmu |
| `votingNumber` | int | Numer głosowania na posiedzeniu |
| `date` | string | Dokładna data i godzina głosowania ISO-8601 |
| `title` | string | Pełny oficjalny tytuł głosowania (np. punkt porządku dziennego, numer druku) |
| `topic` | string | Temat głosowania / skrócony opis |
| `totalVoted` | int | Liczba posłów biorących udział w głosowaniu |
| `majorityVotes` | int | Wymagana większość głosów |
| `majorityType` | string | Typ większości (np. `"SIMPLE_MAJORITY"`, `"ABSOLUTE_MAJORITY"`) |
| `results` | object | Wyniki ogólne: `yes`, `no`, `abstain`, `notParticipating` |
| `clubSummary` | object | Zagregowane wyniki dla każdego klubu: `{ "PiS": {"total": 194, "yes": 192, "absent": 2}, ... }` |
| `mpVote` | object \| null | Głos wskazanego posła: `{ "id": 133, "name": "...", "club": "...", "vote": "YES" }` |

Wartości głosu posła (`vote`):
- `YES` — za
- `NO` — przeciw
- `ABSTAIN` — wstrzymał się
- `ABSENT` / `NOT_PARTICIPATING` — nieobecny / brak udziału

---

## 3. `votings`

Przegląd głosowań na danym posiedzeniu Sejmu.

`python3 scripts/sejm.py votings [--sitting <nr>] [--search <fraza>]`

---

## 4. `prints` (lub `print`)

Wyszukiwanie i pobieranie druków sejmowych (projekty ustaw, uchwał, sprawozdania komisji, wnioski).

`python3 scripts/sejm.py prints [--number <nr>] [--search <fraza>]`

| Pole | Typ | Opis |
|---|---|---|
| `number` | string | Numer druku sejmowego |
| `title` | string | Oficjalny tytuł druku |
| `documentDate` | string | Data sporządzenia dokumentu |
| `deliveryDate` | string | Data wpłynięcia / doręczenia do Sejmu |
| `attachments` | string[] | Pliki załączników PDF dostępne w API |
| `processPrint` | string[] | Powiązane numery druków w procesie legislacyjnym |

---

## 5. `process`

Śledzenie etapów procesu legislacyjnego nad danym drukiem / projektem ustawy.

`python3 scripts/sejm.py process <numer_druku>`

| Pole | Typ | Opis |
|---|---|---|
| `number` | string | Numer druku |
| `title` | string | Tytuł projektu ustawy lub uchwały |
| `titleFinal` | string \| null | Ostateczny tytuł przyjętego aktu prawnego |
| `documentType` | string | Rodzaj dokumentu (np. `"projekt ustawy"`, `"projekt uchwały"`) |
| `processStartDate` | string | Data rozpoczęcia procedowania w Sejmie |
| `closureDate` | string \| null | Data zakończenia prac w Sejmie |
| `passed` | bool | Czy ustawa / uchwała została uchwalona przez Sejm |
| `displayAddress` | string \| null | Pozycja w Dzienniku Ustaw lub Monitorze Polskim |
| `stages` | list | Chronologiczna lista etapów prac: `{ "date", "stageName", "stageType", "sitting" }` |
| `links` | list | Linki do ISAP, ELI oraz treści ustawy |

---

## 6. `interpellations`

Wyszukiwanie interpelacji poselskich i odpowiedzi resortów.

`python3 scripts/sejm.py interpellations [--number <nr>] [--search <fraza>] [--mp-id <id>]`

| Pole | Typ | Opis |
|---|---|---|
| `number` | int | Numer interpelacji |
| `title` | string | Tytuł interpelacji |
| `receiptDate` | string | Data wpływu do Marszałka Sejmu |
| `sentDate` | string | Data przekazania do właściwego ministerstwa |
| `fromMpIds` | string[] | Identyfikatory posłów wnioskujących |
| `toRecipients` | string[] | Adresaci (np. `"minister finansów"`, `"minister infrastruktury"`) |
| `replies` | list | Odpowiedzi ministerstw: autor odpowiedzi, data wpływu, data modyfikacji |

---

## 7. `terms`

Katalog kadencji Sejmu RP (od I do X kadencji). Działa w 100% offline.

---

## Kody Wyjścia

| Kod | Znaczenie | Działanie Agenta |
|---|---|---|
| `0` | Sukces | Odczytaj wynik z formatu JSON na `stdout` |
| `2` | Nie znaleziono | Poseł, głosowanie, druk lub proces nie istnieje |
| `64` | Błąd walidacji / argumentów | Sprawdź parametry wywołania polecenia |
| `69` | Błąd serwera Sejmu RP / sieci | Chwilowy błąd API Sejmu; ponów próbę za chwilę |

---

## Neutralność i Prawa Autorskie

Dane pochodzą z oficjalnego Otwartego API Sejmu Rzeczypospolitej Polskiej (`https://api.sejm.gov.pl/`). Zgodnie z polskim prawem autorskim, materiały urzędowe, dokumenty i materiały parlamentarne nie podlegają prawu autorskiemu (art. 4 ustawy o prawie autorskim i prawach pokrewnych). Odpowiedzi powinny zawsze wskazywać źródło danych: **Kancelaria Sejmu RP** oraz jednoznacznie określać kadencję i identyfikator sprawy.
