# Discovery polskich skilli — 2026-11-06

To jeden zamknięty cykl, nie uruchomiony monitoring. Oceny są hipotezami produktowymi, nie wynikami ankiety ani prognozą instalacji. Research obejmuje dokumentację dostawców, GitHub, katalogi API i portale open data. Nie wykonano wywiadów ani nie pozyskano statystyk użycia projektu.

## Ranking i decyzja

Punkty: **U** użyteczność /25, **G** grupa użytkowników /20, **Z** organiczny zasięg /15, **D** wiarygodność danych /15, **Ł** łatwość /10, **W** unikalność /10, **R** niskie ryzyko /5. Suma /100. Punktacja kosztu wdrożenia uwzględnia wymóg standardowej biblioteki, dostępu i utrzymania.

| # | Skill | U | G | Z | D | Ł | W | R | Suma | Decyzja |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `praca` | 24 | 19 | 14 | 13 | 9 | 6 | 5 | **90** | Wdrożony |
| 2 | `adresy` | 24 | 18 | 12 | 14 | 9 | 7 | 5 | **89** | Wdrożony |
| 3 | `otwarte-dane` | 23 | 17 | 12 | 15 | 9 | 6 | 5 | **87** | Wdrożony |
| 4 | `kolej` | 25 | 19 | 14 | 13 | 3 | 7 | 4 | **85** | Następny research |
| 5 | `leki` | 24 | 19 | 13 | 14 | 4 | 7 | 3 | **84** | Następny research |
| 6 | `ceidg` | 24 | 17 | 11 | 14 | 6 | 7 | 4 | **83** | Następny research |
| 7 | `ceny-deweloperow` | 24 | 18 | 14 | 11 | 3 | 8 | 4 | **82** | Następny research |
| 8 | `ladowarki` | 23 | 16 | 12 | 14 | 5 | 7 | 4 | **81** | Następny research |
| 9 | `internety` | 23 | 18 | 12 | 13 | 3 | 8 | 4 | **81** | Następny research |
| 10 | `parkingi` | 22 | 16 | 12 | 12 | 7 | 6 | 5 | **80** | Następny research |
| 11 | `fakturownia` | 24 | 15 | 10 | 14 | 6 | 5 | 3 | **77** | Następny research |
| 12 | `drogi` | 23 | 17 | 11 | 13 | 3 | 6 | 4 | **77** | Następny research |
| 13 | `szkoly` | 22 | 18 | 10 | 14 | 3 | 6 | 4 | **77** | Następny research |
| 14 | `bibliografia` | 19 | 15 | 10 | 15 | 8 | 5 | 5 | **77** | Następny research |
| 15 | `regon` | 22 | 15 | 9 | 15 | 6 | 5 | 4 | **76** | Następny research |
| 16 | `ksef-odczyt` | 25 | 19 | 14 | 13 | 1 | 3 | 1 | **76** | Następny research |
| 17 | `uczelnie` | 20 | 15 | 9 | 14 | 6 | 7 | 5 | **76** | Następny research |
| 18 | `baselinker` | 24 | 14 | 10 | 14 | 5 | 5 | 3 | **75** | Następny research |
| 19 | `allegro-sprzedawca` | 23 | 16 | 11 | 14 | 4 | 4 | 3 | **75** | Następny research |
| 20 | `zabytki` | 18 | 14 | 12 | 14 | 5 | 7 | 5 | **75** | Następny research |
| 21 | `teryt` | 20 | 13 | 7 | 15 | 7 | 6 | 5 | **73** | Następny research |
| 22 | `obszary-chronione` | 20 | 13 | 10 | 14 | 4 | 8 | 4 | **73** | Następny research |
| 23 | `cepik-statystyki` | 19 | 14 | 9 | 14 | 5 | 6 | 5 | **72** | Następny research |
| 24 | `schroniska` | 18 | 13 | 13 | 7 | 6 | 8 | 4 | **69** | Następny research |
| 25 | `sankcje-pl` | 22 | 12 | 9 | 14 | 3 | 6 | 2 | **68** | Następny research |

Najlepsza trójka łączy pracę (nowa kategoria z konkretnym wynikiem), adresy (odblokowują użycie istniejących skilli lokalnych) i discovery źródeł (użyteczne dla użytkowników i contributorów). Wszystkie trzy mają udokumentowane, oficjalne i zweryfikowane odczyty bez konta. Nie wybrano prostego wrappera bibliografii tylko dlatego, że łatwo go napisać. KSeF ma wysoki potencjał, lecz autoryzacja, kryptografia i dostęp do danych finansowych nie mieszczą się w bezpiecznym zakresie tego cyklu.

API „oficjalne” oznacza interfejs udostępniony przez właściciela źródła, także prywatną firmę. Społecznościowy wrapper oficjalnego rejestru nie staje się przez to oficjalnym API. Dla backlogu „potwierdzono dokumentację” nie znaczy „integracja działa”. Nie wymyślano adresów endpointów dla kandydatów bez dostępu.

## Karty 25 pomysłów

### 1. praca — 90/100

- **Problem:** Oferty z widełkami i trybem pracy zamiast przeszukiwania wielu stron.
- **Użytkownicy:** Kandydaci, rekruterzy, doradcy kariery.
- **Pytanie:** Znajdź pracę Python zdalnie i pokaż osobno B2B oraz UoP.
- **Źródło i dokumentacja:** [źródło 1](https://solid.jobs/api-ofert-pracy), [źródło 2](https://github.com/solid-company/solid-jobs-client)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Brak; publiczny identyfikator campaign.
- **Limity, koszty, ograniczenia:** Bezpłatny odczyt, 300/min/IP, cache dostawcy do godziny; jeden portal, nie cały rynek.
- **Trudność:** Średnia: strony, waluty i formy umów.
- **Codzienne użycie:** Wysoki podczas poszukiwania pracy.
- **Udostępnianie:** Wysoki: konkretne oferty i krótkie demonstracje.
- **Weryfikacja:** Dokumentacja dostawcy + udane odczyty live ofert i statystyk. Dostawca ma też własne skille; wyróżnikiem tutaj jest samodzielny Python bez pip i wspólny kontrakt repo.

### 2. adresy — 89/100

- **Problem:** Brak GPS dla istniejących skilli szukających obiektów w pobliżu.
- **Użytkownicy:** Mieszkańcy, logistyka, analitycy GIS.
- **Pytanie:** Znajdź współrzędne Marki, Andersa 1.
- **Źródło i dokumentacja:** [źródło 1](https://services.gugik.gov.pl/uug/opis.html)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Brak.
- **Limity, koszty, ograniczenia:** Publiczny odczyt; brak opublikowanej kwoty zapytań/SLA. Nieudokumentowana paginacja; wyniki przybliżone.
- **Trudność:** Średnia: osie, EPSG, niejednoznaczne nazwy.
- **Codzienne użycie:** Wysoki jako pierwszy krok wielu zadań lokalnych.
- **Udostępnianie:** Wysoki: adres → GPS → pobliska usługa.
- **Weryfikacja:** Dokumentacja + live search i reverse, także przypadek wielu miejscowości Warszawa.

### 3. otwarte-dane — 87/100

- **Problem:** Trudność odnalezienia właściwego zbioru, licencji i pliku źródłowego.
- **Użytkownicy:** Analitycy, dziennikarze, twórcy integracji, NGO.
- **Pytanie:** Znajdź otwarte dane o transporcie z linkami i datami aktualizacji.
- **Źródło i dokumentacja:** [źródło 1](https://api.dane.gov.pl/1.4/doc), [źródło 2](https://api.dane.gov.pl/spec/1.4)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Brak dla odczytu.
- **Limity, koszty, ograniczenia:** Bezpłatnie; do 100 rekordów/stronę; brak potwierdzonej kwoty zapytań. Licencje zależą od zbioru.
- **Trudność:** Średnia: JSON:API, strony, metadane praw.
- **Codzienne użycie:** Wysoki dla analityków, okresowy dla mieszkańców.
- **Udostępnianie:** Wysoki w społecznościach danych i open source.
- **Weryfikacja:** OpenAPI pobrane + live listy, szczegóły i strony. Nie interpretuje zawartości plików.

### 4. kolej — 85/100

- **Problem:** Planowane i rzeczywiste odjazdy pociągów w jednym pytaniu.
- **Użytkownicy:** Pasażerowie kolei, osoby dojeżdżające.
- **Pytanie:** Jakie są najbliższe odjazdy pociągów z tej stacji?
- **Źródło i dokumentacja:** [źródło 1](https://www.plk-sa.pl/klienci-i-kontrahenci/api-otwarte-dane), [źródło 2](https://pdp-api.plk-sa.pl/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Rejestracja/dostęp operatora API.
- **Limity, koszty, ograniczenia:** Warunki, kwoty zapytań i ewentualne opłaty wymagają sprawdzenia po uzyskaniu dostępu. Nie zakładać dostępu anonimowego.
- **Trudność:** Wysoka: dostęp, rozkłady, identyfikatory, zmiany ruchu.
- **Codzienne użycie:** Bardzo wysoki.
- **Udostępnianie:** Wysoki: codzienne dojazdy.
- **Weryfikacja:** Oficjalna strona potwierdza API i rejestrację; brak konta i live danych. Nie dubluje miejskich odjazdów.

### 5. leki — 84/100

- **Problem:** Odnalezienie oficjalnej ulotki i substancji czynnej bez treści marketingowych.
- **Użytkownicy:** Pacjenci, opiekunowie, farmaceuci.
- **Pytanie:** Znajdź oficjalną ulotkę i substancję czynną tego leku.
- **Źródło i dokumentacja:** [źródło 1](https://www.gov.pl/web/urpl/rejestr-produktow-leczniczych3), [źródło 2](https://github.com/SaDa1337/RPL.API)
- **Oficjalne API:** nie / niepotwierdzone; szczegóły poniżej
- **Uwierzytelnienie:** Publiczna wyszukiwarka/eksport; zasady REST do dalszej weryfikacji.
- **Limity, koszty, ograniczenia:** Oficjalny rejestr URPL; społecznościowy wrapper REST nie jest oficjalnym API. Duży eksport XML, aktualność ulotek; bez porad dawkowania.
- **Trudność:** Wysoka: pobieranie i indeks dużego eksportu XML.
- **Codzienne użycie:** Wysoki.
- **Udostępnianie:** Wysoki: bezpośredni link do ulotki.
- **Weryfikacja:** Potwierdzono rejestr i projekt open source. Nie wykonano odczytu produkcyjnego eksportu ani nie potwierdzono oficjalnego REST; kandydat do walidacji.

### 6. ceidg — 83/100

- **Problem:** Status i zawieszenia działalności JDG, której nie ma w KRS.
- **Użytkownicy:** Freelancerzy, księgowość, małe firmy.
- **Pytanie:** Czy kontrahent prowadzi aktywną działalność w CEIDG?
- **Źródło i dokumentacja:** [źródło 1](https://pliki.biznes.gov.pl/20220425/pliki/HD-CEIDG-API-Hurtowni-Danych-Dokumentacja-dla-integratorow-v1-5.pdf)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** JWT po wniosku i weryfikacji użytkownika.
- **Limity, koszty, ograniczenia:** Dostęp zależny od nadanych uprawnień; aktualne limity trzeba potwierdzić dla przyznanej wersji. Dokument przykładowy opisuje v1, nie dowodzi aktualności v2.
- **Trudność:** Średnia/wysoka: autoryzacja, dane osób fizycznych.
- **Codzienne użycie:** Wysoki w B2B.
- **Udostępnianie:** Średni/wysoki: sprawdzanie kontrahenta.
- **Weryfikacja:** Potwierdzono oficjalną dokumentację i proces dostępu. Brak tokenu, bez live danych.

### 7. ceny-deweloperow — 82/100

- **Problem:** Historia cen ofertowych lokali i porównanie składników ceny.
- **Użytkownicy:** Kupujący mieszkania, analitycy mieszkaniowi.
- **Pytanie:** Pokaż historię ceny tego lokalu u dewelopera.
- **Źródło i dokumentacja:** [źródło 1](https://api.dane.gov.pl/1.4/doc), [źródło 2](https://api.dane.gov.pl/1.4/datasets)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Brak dla katalogu.
- **Limity, koszty, ograniczenia:** Publiczne pliki różnych dostawców, różne formaty i licencje, możliwe braki i korekty. Nie mylić ofert z transakcjami RCN.
- **Trudność:** Wysoka: normalizacja CSV/XLSX, stabilna tożsamość lokalu.
- **Codzienne użycie:** Średni; wysoki w okresie zakupu.
- **Udostępnianie:** Bardzo wysoki: historia promocji i jawność cen.
- **Weryfikacja:** Potwierdzone API katalogu; dedykowany parser cenników i kompletność niezweryfikowane. otwarte-dane umożliwia discovery, nie zastępuje tej analizy.

### 8. ladowarki — 81/100

- **Problem:** Złącze, lokalizacja i dostępność publicznego ładowania.
- **Użytkownicy:** Kierowcy EV, operatorzy flot.
- **Pytanie:** Znajdź pobliskie stacje z CCS i informacją o dostępności.
- **Źródło i dokumentacja:** [źródło 1](https://eipa.udt.gov.pl/reader/docs), [źródło 2](https://eipa.udt.gov.pl/faq)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Rejestracja czytelnika; nie używać API operatora do publicznego odczytu.
- **Limity, koszty, ograniczenia:** JSON; szczegółowe warunki czytelnika i aktualność statusów do sprawdzenia po rejestracji. Opłaty za identyfikatory operatorów nie są automatycznie opłatami za czytanie.
- **Trudność:** Średnia/wysoka: dostęp i statusy.
- **Codzienne użycie:** Wysoki dla kierowców EV.
- **Udostępnianie:** Wysoki w społecznościach elektromobilności.
- **Weryfikacja:** Oficjalna dokumentacja reader i FAQ; bez klucza nie wykonano live.

### 9. internety — 81/100

- **Problem:** Sprawdzenie źródłowej informacji o usługach internetu pod adresem.
- **Użytkownicy:** Osoby przeprowadzające się, firmy, mieszkańcy terenów wiejskich.
- **Pytanie:** Jak zweryfikować dostęp do światłowodu pod tym adresem?
- **Źródło i dokumentacja:** [źródło 1](https://internet.gov.pl/docs/api/), [źródło 2](https://internet.gov.pl/help/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Nagłówek Authorization: Token; zakres uprawnień wymaga potwierdzenia.
- **Limity, koszty, ograniczenia:** SIDUSIS ma udokumentowane API, ale nie potwierdzono ogólnodostępnego odczytu zasięgu dla dowolnego adresu. Koszt i limity nieustalone.
- **Trudność:** Wysoka: uprawnienia i zasięg API; blokada wdrożenia.
- **Codzienne użycie:** Okresowy, bardzo użyteczny przy przeprowadzce.
- **Udostępnianie:** Wysoki: lokalne grupy i nieruchomości.
- **Weryfikacja:** Dokumentacja potwierdza API i token, nie potwierdza jeszcze proponowanego scenariusza odczytu. Nie implementować przez wewnętrzne API mapy.

### 10. parkingi — 80/100

- **Problem:** Zajętość parkingów P+R przed dojazdem do miasta.
- **Użytkownicy:** Kierowcy dojeżdżający do Poznania.
- **Pytanie:** Na którym parkingu buforowym są wolne miejsca?
- **Źródło i dokumentacja:** [źródło 1](https://www.ztm.poznan.pl/otwarte-dane/dokumentacja/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Publiczne pliki, bez konta w opisanym kanale.
- **Limity, koszty, ograniczenia:** Oficjalna specyfikacja plików; aktualność i częstotliwość pobierania do potwierdzenia; brak gwarancji miejsca po dojeździe.
- **Trudność:** Średnia.
- **Codzienne użycie:** Wysoki lokalnie.
- **Udostępnianie:** Wysoki lokalnie; łatwe demo.
- **Weryfikacja:** Oficjalna dokumentacja plików parkingów potwierdzona; bez live w tym cyklu. Osobny problem od rozkładów odjazdów.

### 11. fakturownia — 77/100

- **Problem:** Lista niezapłaconych faktur i przegląd należności.
- **Użytkownicy:** Mikrofirmy i księgowi korzystający z Fakturowni.
- **Pytanie:** Pokaż moje zaległe faktury, bez wysyłania przypomnień.
- **Źródło i dokumentacja:** [źródło 1](https://fakturownia.pl/api), [źródło 2](https://github.com/fakturownia/api)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Token API i konto użytkownika.
- **Limity, koszty, ograniczenia:** Plan konta i aktualny cennik dostawcy; nie potwierdzono ceny ani kwoty zapytań. Dane finansowe klienta.
- **Trudność:** Średnia: token, strony, uprawnienia tylko do odczytu.
- **Codzienne użycie:** Wysoki.
- **Udostępnianie:** Średni: konkretna oszczędność czasu w firmie.
- **Weryfikacja:** Oficjalne API i repo dostawcy; bez konta i odczytu prywatnych danych.

### 12. drogi — 77/100

- **Problem:** Oficjalne utrudnienia na drogach zamiast niesprawdzonych informacji.
- **Użytkownicy:** Kierowcy, logistyka.
- **Pytanie:** Czy na tej drodze są zgłoszone utrudnienia?
- **Źródło i dokumentacja:** [źródło 1](https://kpd.gddkia.gov.pl/index.php/en/profile-datex/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Warunki dostępu KPD do dalszej weryfikacji.
- **Limity, koszty, ograniczenia:** DATEX II, różne publikacje i profile. Nie potwierdzono anonimowego endpointu całego zakresu ani kosztu.
- **Trudność:** Wysoka: XML, geografia, aktualność zdarzeń.
- **Codzienne użycie:** Wysoki.
- **Udostępnianie:** Średni/wysoki lokalnie.
- **Weryfikacja:** Oficjalna dokumentacja profili DATEX II potwierdzona; bez live danych.

### 13. szkoly — 77/100

- **Problem:** Weryfikacja placówki w RSPO i jej typu/statusu.
- **Użytkownicy:** Rodzice, NGO, samorządy.
- **Pytanie:** Czy ta szkoła jest aktywna w RSPO?
- **Źródło i dokumentacja:** [źródło 1](https://cie.gov.pl/nowe-api-wyszukiwarki-rspo/), [źródło 2](https://api.rspo.gov.pl/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Wniosek o przyznanie dostępu.
- **Limity, koszty, ograniczenia:** Nowe API od stycznia 2026; stare wyłączane według komunikatu w marcu. Limity i koszt nieustalone. Rejestr nie mierzy jakości nauczania.
- **Trudność:** Średnia/wysoka: dostęp i nowy kontrakt.
- **Codzienne użycie:** Sezonowy, duży zasięg.
- **Udostępnianie:** Wysoki w grupach rodziców.
- **Weryfikacja:** Aktualny komunikat CIE; brak uprawnień/live. Nie używać starego api-rspo.men.gov.pl.

### 14. bibliografia — 77/100

- **Problem:** Poprawne dane książki/ISBN do bibliografii.
- **Użytkownicy:** Uczniowie, studenci, bibliotekarze.
- **Pytanie:** Znajdź wydanie tej książki w Bibliotece Narodowej.
- **Źródło i dokumentacja:** [źródło 1](https://data.bn.org.pl/docs), [źródło 2](https://data.bn.org.pl/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Brak w publicznym API.
- **Limity, koszty, ograniczenia:** JSON/XML/MARC; źródło opisuje otwarte pobieranie. Brak ustalonego SLA/kwoty. Metadane nie oznaczają dostępu do pełnego tekstu.
- **Trudność:** Niska/średnia.
- **Codzienne użycie:** Średni, wysoki w edukacji.
- **Udostępnianie:** Średni: demonstracja bibliografii bez zmyślonych pozycji.
- **Weryfikacja:** Dokumentacja BN potwierdzona, bez live w tym cyklu.

### 15. regon — 76/100

- **Problem:** Działalności PKD i jednostki lokalne poza danymi VAT.
- **Użytkownicy:** Analitycy B2B, księgowi, administracja.
- **Pytanie:** Pokaż jednostki lokalne i PKD firmy z rejestru REGON.
- **Źródło i dokumentacja:** [źródło 1](https://api.stat.gov.pl/Home/RegonApi?lang=pl)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Klucz użytkownika BIR, sesja SOAP.
- **Limity, koszty, ograniczenia:** Usługa bezpłatna; harmonogram limitów do odczytu z dokumentacji właściwej wersji.
- **Trudność:** Średnia: SOAP, sesje, raporty.
- **Codzienne użycie:** Wysoki w B2B.
- **Udostępnianie:** Średni.
- **Weryfikacja:** Oficjalna strona GUS potwierdza usługę, bezpłatność i klucz; bez live. Zakres musi wykraczać poza istniejącą białą listę.

### 16. ksef-odczyt — 76/100

- **Problem:** Bezpieczny przegląd faktur i statusów w KSeF.
- **Użytkownicy:** Przedsiębiorcy i księgowość.
- **Pytanie:** Pokaż statusy faktur z mojego KSeF.
- **Źródło i dokumentacja:** [źródło 1](https://github.com/CIRFMF/ksef-api)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Uwierzytelnienie KSeF, tokeny/certyfikaty i uprawnienia według aktualnego API.
- **Limity, koszty, ograniczenia:** Obsługa kryptografii i sekretów; stdlib-only ogranicza bezpieczną implementację. Nie projektować własnej kryptografii. Limity w repo MF.
- **Trudność:** Bardzo wysoka; blokada tego cyklu.
- **Codzienne użycie:** Bardzo wysoki.
- **Udostępnianie:** Wysoki, ale duża konkurencja i ryzyko.
- **Weryfikacja:** Oficjalne repo; dawny ksef-docs przekierowuje do ksef-api. Bez sesji i danych produkcyjnych.

### 17. uczelnie — 76/100

- **Problem:** Weryfikacja uczelni i kierunków w danych RAD-on.
- **Użytkownicy:** Kandydaci na studia, badacze, dziennikarze.
- **Pytanie:** Sprawdź tę uczelnię i prowadzone kierunki.
- **Źródło i dokumentacja:** [źródło 1](https://radon.nauka.gov.pl/pomoc/knowledge-base/scenariusze-pobierania-danych-przy-uzyciu-api-rad-onu/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Publiczne REST; dokładny zakres bez konta do potwierdzenia.
- **Limity, koszty, ograniczenia:** Warunki RAD-on; nie ustalono kwoty zapytań. Nie traktować rejestru jako rankingu uczelni.
- **Trudność:** Średnia.
- **Codzienne użycie:** Sezonowy.
- **Udostępnianie:** Średni/wysoki w rekrutacji.
- **Weryfikacja:** Oficjalne scenariusze REST/R/Python potwierdzone, bez live.

### 18. baselinker — 75/100

- **Problem:** Dzienny przegląd niewysłanych zamówień z wielu kanałów.
- **Użytkownicy:** Sprzedawcy e-commerce.
- **Pytanie:** Które zamówienia oczekują na wysyłkę?
- **Źródło i dokumentacja:** [źródło 1](https://api.baselinker.com/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** X-BLToken z konta.
- **Limity, koszty, ograniczenia:** POST connector.php; ceny zależą od planu, limity metod trzeba sprawdzić przed implementacją. Minimalizować dane kupujących.
- **Trudność:** Średnia/wysoka: uprawnienia i paginacja chronologiczna.
- **Codzienne użycie:** Bardzo wysoki w sklepie.
- **Udostępnianie:** Średni/wysoki w grupach e-commerce.
- **Weryfikacja:** Oficjalna dokumentacja getOrders i autoryzacji; bez tokenu/live.

### 19. allegro-sprzedawca — 75/100

- **Problem:** Przegląd zamówień i ofert na własnym koncie.
- **Użytkownicy:** Sprzedawcy Allegro.
- **Pytanie:** Pokaż zamówienia wymagające obsługi na moim Allegro.
- **Źródło i dokumentacja:** [źródło 1](https://developer.allegro.pl/faq), [źródło 2](https://developer.allegro.pl/documentation)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** OAuth i zakresy dostępu.
- **Limity, koszty, ograniczenia:** Główny limit 9000/min/Client ID, dodatkowe limity zasobów. Opłaty handlowe i dostęp zależą od usługi; nie zakładać anonimowej wyszukiwarki ofert.
- **Trudność:** Wysoka: OAuth, zakresy i dane kupujących.
- **Codzienne użycie:** Bardzo wysoki dla sprzedawcy.
- **Udostępnianie:** Średni.
- **Weryfikacja:** Oficjalna dokumentacja i FAQ, bez autoryzowanego odczytu.

### 20. zabytki — 75/100

- **Problem:** Oficjalne obiekty dziedzictwa do planowania zwiedzania.
- **Użytkownicy:** Turyści, nauczyciele, lokalne społeczności.
- **Pytanie:** Znajdź pomniki historii w okolicy.
- **Źródło i dokumentacja:** [źródło 1](https://nid.pl/en/zasoby/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Publiczne usługi/pliki.
- **Limity, koszty, ograniczenia:** NID opisuje bezpłatne dane wektorowe; WFS dla pomników historii i UNESCO. Nie zakładać identycznego zakresu WFS dla wszystkich rejestrów.
- **Trudność:** Średnia: WFS i geometria.
- **Codzienne użycie:** Okresowy.
- **Udostępnianie:** Wysoki: mapy lokalnych ciekawostek.
- **Weryfikacja:** Oficjalne zasoby NID i zakres usług potwierdzone; bez live.

### 21. teryt — 73/100

- **Problem:** Historyczne identyfikatory miejscowości i zmiany podziału terytorialnego.
- **Użytkownicy:** Analitycy, integratorzy, administracja.
- **Pytanie:** Jaki kod TERYT miała ta gmina w danym roku?
- **Źródło i dokumentacja:** [źródło 1](https://api.stat.gov.pl/Home/TerytApi), [źródło 2](https://api.stat.gov.pl/)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Dostęp i konto zgodnie z TERYT ws1; do weryfikacji rejestracji.
- **Limity, koszty, ograniczenia:** Oficjalny katalog API potwierdzony; szczegółowa strona miała timeout w narzędziu. Limitów i ceny nie zweryfikowano.
- **Trudność:** Średnia: SOAP i wersjonowanie danych.
- **Codzienne użycie:** Wysoki w integracjach, niski u konsumentów.
- **Udostępnianie:** Niski/średni.
- **Weryfikacja:** Potwierdzona obecność API w portalu GUS; bez live. Zakres historyczny odróżnia od geokodowania i BDL.

### 22. obszary-chronione — 73/100

- **Problem:** Sprawdzenie nakładania się lokalizacji i form ochrony przyrody.
- **Użytkownicy:** Właściciele działek, turyści, analitycy GIS.
- **Pytanie:** Czy wskazany punkt leży na obszarze Natura 2000?
- **Źródło i dokumentacja:** [źródło 1](https://www.gov.pl/web/gdos/dostep-do-danych-geoprzestrzennych)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Brak w opisanych publicznych WFS.
- **Limity, koszty, ograniczenia:** Brak ustalonej kwoty zapytań; granice informacyjne nie zastępują aktu prawnego. Nie publikować lokalizacji wrażliwych gatunków.
- **Trudność:** Wysoka: WFS, CRS, punkt w poligonie.
- **Codzienne użycie:** Średni.
- **Udostępnianie:** Średni/wysoki w społecznościach lokalnych.
- **Weryfikacja:** Oficjalne adresy WFS/WMS GDOŚ potwierdzone, bez live.

### 23. cepik-statystyki — 72/100

- **Problem:** Analiza rejestracji pojazdów według regionu i rodzaju napędu.
- **Użytkownicy:** Dziennikarze, analitycy rynku, samorządy.
- **Pytanie:** Porównaj rejestracje elektryków w województwach.
- **Źródło i dokumentacja:** [źródło 1](https://api.cepik.gov.pl/doc), [źródło 2](https://www.gov.pl/web/cepik/api-dla-centralnej-ewidencji-pojazdow-i-kierowcow-api-do-cepik)
- **Oficjalne API:** tak
- **Uwierzytelnienie:** Publiczne API; aktualne ograniczenia do sprawdzenia.
- **Limity, koszty, ograniczenia:** Anonimizowane dane, paginacja i zakres dat; brak ustalonego SLA/kwoty. Nie jest usługą historii konkretnego auta po VIN.
- **Trudność:** Średnia/wysoka: wolumen i jakość danych.
- **Codzienne użycie:** Średni.
- **Udostępnianie:** Średni: raporty regionalne.
- **Weryfikacja:** Oficjalna publikacja i Swagger potwierdzone, bez live.

### 24. schroniska — 69/100

- **Problem:** Odkrywanie lokalnych schronisk i źródeł danych o adopcji.
- **Użytkownicy:** Osoby szukające zwierzęcia i wolontariusze.
- **Pytanie:** Znajdź źródła danych o schroniskach w mojej okolicy.
- **Źródło i dokumentacja:** [źródło 1](https://github.com/Lechr11/otwarteschroniska)
- **Oficjalne API:** nie / niepotwierdzone; szczegóły poniżej
- **Uwierzytelnienie:** Publiczny projekt społecznościowy; kontrakt dostępu do potwierdzenia.
- **Limity, koszty, ograniczenia:** Deklarowane CC-BY 4.0 dla danych i MIT dla kodu; mały projekt, pokrycie i aktualność wymagają audytu. Nie obiecywać dostępności zwierzęcia.
- **Trudność:** Średnia.
- **Codzienne użycie:** Okresowy.
- **Udostępnianie:** Wysoki społecznie.
- **Weryfikacja:** Repo projektu potwierdzone. Nie jest państwowym rejestrem ani potwierdzonym API wszystkich schronisk; bez live.

### 25. sankcje-pl — 68/100

- **Problem:** Odnalezienie wpisu i decyzji w polskiej liście sankcyjnej.
- **Użytkownicy:** Compliance i działy zakupów.
- **Pytanie:** Znajdź wpis tego podmiotu na liście MSWiA i link do decyzji.
- **Źródło i dokumentacja:** [źródło 1](https://www.gov.pl/web/mswia/lista-osob-i-podmiotow-objetych-sankcjami)
- **Oficjalne API:** nie / niepotwierdzone; szczegóły poniżej
- **Uwierzytelnienie:** Publiczna strona i załączniki.
- **Limity, koszty, ograniczenia:** Nie potwierdzono oficjalnego REST. Tabela/załączniki; liczne homonimy, transliteracja i ryzyko fałszywych zgodności. Brak wpisu nie oznacza braku wszystkich sankcji.
- **Trudność:** Wysoka: tożsamość, aktualność, brak API.
- **Codzienne użycie:** Wysoki w compliance.
- **Udostępnianie:** Niski/średni; ostrożne wykorzystanie.
- **Weryfikacja:** Oficjalna lista potwierdzona, API niepotwierdzone. Nie wdrażać jako automatycznej decyzji o osobie.

## Sygnały potrzeb i konkurencja

- Oficjalny dostawca SOLID.Jobs publikuje API oraz własne skille: dowód dostępności integracji i konkurencji, nie niezależny pomiar popytu. Nasz zakres to odczyt bez Node/pip w tym katalogu; nie kopia ich śledzenia aplikacji.
- Nowe API RSPO wymaga wniosku; stary interfejs został zapowiedziany do wyłączenia. Weryfikacja aktualnych dokumentów zapobiega tworzeniu martwych integracji.
- Publiczne katalogi [otwarteAPI](https://otwarteapi.pl/) i [polskie-api](https://github.com/Klaster1234/polskie-api) wykorzystano do discovery. Ustalenia techniczne oparto na źródłach właścicieli, nie na samym wpisie w katalogu.
- Społecznościowy [RPL.API](https://github.com/SaDa1337/RPL.API) pokazuje możliwość budowy indeksu XML, lecz nie dowodzi istnienia oficjalnego REST.
- Publiczne rozmowy o [jawności cen mieszkań](https://www.reddit.com/r/Polska/comments/1n89x0q) wskazują potrzebę porównania lokalizacji i historii cen. To jakościowy sygnał, bez ekstrapolacji na wielkość rynku.

## TOP 10 na następny cykl

1. **kolej (85)** — Oficjalna strona potwierdza API i rejestrację; brak konta i live danych. Nie dubluje miejskich odjazdów.
2. **leki (84)** — Potwierdzono rejestr i projekt open source. Nie wykonano odczytu produkcyjnego eksportu ani nie potwierdzono oficjalnego REST; kandydat do walidacji.
3. **ceidg (83)** — Potwierdzono oficjalną dokumentację i proces dostępu. Brak tokenu, bez live danych.
4. **ceny-deweloperow (82)** — Potwierdzone API katalogu; dedykowany parser cenników i kompletność niezweryfikowane. otwarte-dane umożliwia discovery, nie zastępuje tej analizy.
5. **ladowarki (81)** — Oficjalna dokumentacja reader i FAQ; bez klucza nie wykonano live.
6. **internety (81)** — Dokumentacja potwierdza API i token, nie potwierdza jeszcze proponowanego scenariusza odczytu. Nie implementować przez wewnętrzne API mapy.
7. **parkingi (80)** — Oficjalna dokumentacja plików parkingów potwierdzona; bez live w tym cyklu. Osobny problem od rozkładów odjazdów.
8. **fakturownia (77)** — Oficjalne API i repo dostawcy; bez konta i odczytu prywatnych danych.
9. **drogi (77)** — Oficjalna dokumentacja profili DATEX II potwierdzona; bez live danych.
10. **szkoly (77)** — Aktualny komunikat CIE; brak uprawnień/live. Nie używać starego api-rspo.men.gov.pl.

## Język i discovery

Nowe `SKILL.md` mają instrukcje po angielsku, a manifest zawiera angielskie zdanie discovery oraz polski opis i polskie frazy użytkownika (`language: pl` oznacza rynek/język zastosowania). README.md/README_EN.md opisują katalog dla obu odbiorców. Podczas cyklu w lokalnym repo pojawił się commit `885b453` ustanawiający angielskie instrukcje. Dostosowano nowe skille, zachowując wymagany przez zlecenie polski opis; nie powielono zmian cudzego commita w tym PR. Następnie zmiana trafiła do dev jako PR #2 i została uwzględniona przez rebase. Nie tworzymy dwóch pełnych kopii instrukcji. To decyzja utrzymaniowa, nie benchmark jakości routingu. Następny krok: porównać wybór skilla dla par pytań PL/EN.

Dane do ponownego rankingu: [candidates.json](2026-11-06-candidates.json). Audyt i pomiary: [audit.md](2026-11-06-audit.md). Materiały promocyjne: [growth](../growth/2026-11-06-discovery.md).
