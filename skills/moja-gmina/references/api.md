# Źródło, dostępność i interpretacja

- Oficjalne API: `https://bdl.stat.gov.pl/api/v1/`; [instrukcja GUS](https://api.stat.gov.pl/home/bdlapi).
- [Specyfikacja w oficjalnym portalu CPA](https://cpa.gov.pl/store/api-docs/cpa/BDL-API/v1): typy `UnitDetails`, `VariableDetails`, `SingleUnitData`, `VariableData`, `YearValue`, `Attribute`. Schemat sprawdzono 2026-11-05. Używanym źródłem danych pozostaje BDL; alternatywny portal służy jako dokumentacja.
- `units/search?name=...&level=6`, `variables/search?name=...&level=6`, `variables/{id}`, `units/{id}`, `attributes`, `data/by-unit/{id}?var-id=...`. Parametry zawierają myślniki: `page-size`, `var-id`. Strony numeruje się od 0. Wyszukiwanie pobiera jedną stronę i podaje `has_more`; następna strona przez `--page`.
- Słownik `attributes` według oficjalnego Swaggera nie ma stronicowania ani parametru `page-size`: zwraca `totalRecords` i `results`. Niezgodność liczby rekordów lub powtórzone identyfikatory przerywają porównanie kodem 69, zamiast pozornie zamieniać poprawne obserwacje w braki.
- Alias `ludnosc` wskazuje ID 72305, ludność ogółem. Identyfikator i jednostka „osoba” występują w [oficjalnym podręczniku BDL](https://bdl.stat.gov.pl/bdl/pdf_files/Podrecznik_uzytkownika_BDL.pdf), w tabeli z wierszem „Cechy”. Aktualna definicja i lata zawsze są pobierane z metadanych API; alias nie podmienia metadanych.
- `VariableDetails.level` opisuje dostępność/agregację wskaźnika; źródło rozstrzyga faktyczną dostępność dla konkretnej jednostki. Skill nie wymusza równości tego pola z `UnitDetails.level`, ponieważ wyższe agregaty także mogą mieć dane.
- `compare` zachowuje porządek jednostek podany przez użytkownika, bez automatycznego rankingu. Dla każdej zmiennej porównuje tę samą definicję i jednostkę miary w tym samym roku. Przy jawnym roku zachowuje braki; bez roku nie porównuje różnych lat.
- `observation.value` jest skończoną liczbą albo `null`; `source_value` zachowuje surową wartość. Atrybut zawierający informację o tajemnicy statystycznej, braku danych, niedostępności lub braku zastosowania (także symbole `#`, `.`, `x`) powoduje `value: null`, także jeśli pole źródłowe zawiera liczbę. Brak definicji użytego atrybutu także wyłącza obserwację z porównania (`attribute_unknown`). Pozostałe atrybuty są zachowane z opisem; uwagi o zmianach metodologii nadal wymagają uwzględnienia przez agenta.
- Dane: CC BY 4.0; podaj „Źródło: GUS, Bank Danych Lokalnych”, link oraz informację o własnych przeliczeniach, jeśli je wykonano. Skrypt: MIT.

## Ograniczenia eksploatacyjne

Anonimowy dostęp ma limity 5/s, 100/15 min, 1000/12 h i 10000/7 dni. Klient utrzymuje odstęp 0,3 s w jednym uruchomieniu, cache ogranicza kolejne wywołania. Wiele równoległych procesów nadal dzieli limit adresu IP. 429 kończy odczyt bez ponowienia; `retry_after` pochodzi z nagłówka serwera. Błąd któregoś odczytu przerywa całe porównanie.

Zapis cache jest atomowy, nie zawiera klucza API; brak prawa zapisu nie przerywa poprawnego odczytu. Nie używa się starego cache po awarii. Dane roczne mogą być aktualizowane; czas odczytu nie jest rokiem obserwacji ani datą publikacji. `last_update` pochodzi z szeregu BDL.

Testy w `scripts/test_moja_gmina.py` używają jawnie syntetycznych odpowiedzi zgodnych ze sprawdzonym schematem. Nie są przechwyconymi pomiarami ani fallbackiem API. Weryfikacja danych REST z 2026-11-05 nie powiodła się z powodu timeoutów upstream; potrzebny jest ponowny smoke test, gdy GUS odpowie.
