# API i pochodzenie danych

Sprawdzone 2026-11-06:

- [Oficjalna dokumentacja OFF](https://openfoodfacts.github.io/openfoodfacts-server/api/): v3.6 to zalecana wersja odczytu. Limity wynoszą 15 odczytów produktu i 10 wyszukiwań na minutę/IP. Nagłówek User-Agent powinien zawierać `AppName/Version (ContactEmail)`. Dane są społecznościowe, bez gwarancji kompletności i poprawności.
- Produkt: `GET https://world.openfoodfacts.org/api/v3.6/product/{barcode}.json?fields=...`. Klient pobiera tylko potrzebne pola. Pomyślna odpowiedź ma `status: success`, obiekt `product`, tablice ostrzeżeń i wynik identyfikujący znalezienie produktu. HTTP 404 lub `product_not_found` oznacza brak rekordu.
- [Changelog schematu](https://openfoodfacts.github.io/openfoodfacts-server/api/ref-api-and-product-schema-change-log/): v3.5 wprowadza nowe `nutrition.input_sets` i `nutrition.aggregated_set`; v3.6 wprowadza `tags_sources`. Nie interpretuj pustego starego `nutriments` jako braku wszystkich danych odżywczych.
- Wyszukiwanie: [oficjalny OpenAPI Search-a-licious](https://search.openfoodfacts.org/openapi.json), [interfejs dokumentacji](https://search.openfoodfacts.org/docs). Klient używa `POST /search` z obiektem JSON (`q`, `langs`, `fields`, `page`, `page_size`). Operacja jest wyszukiwaniem bez zapisu danych. Odpowiedź: `hits`, `count`, `is_count_exact`, `page_count`, `timed_out`. Timeout, błędy lub niezgodna strona kończą się kodem 69.
- Zapytanie domyślne: `countries_tags:"en:poland" <tekst>`. Nazwa jest zamieniana na małe litery, interpunkcja zastępowana spacjami; użytkownik nie może wprowadzać własnych operatorów Lucene zmieniających filtr kraju. `normalized_query` pokazuje faktyczny tekst. `--scope world` jawnie usuwa filtr.
- W Search-a-licious pola tekstowe mogą być lokalizowanymi obiektami, a marki listą; skrypt zachowuje metadane wybranego języka i normalizuje listę marek do tekstu. Indeks może być opóźniony względem odczytu produktu. Wynik wyszukiwania nie zawiera pełnego składu — pobierz wybrany kod osobno.
- [Normalizacja kodów OFF](https://openfoodfacts.github.io/openfoodfacts-server/api/ref-barcode-normalization/): po usunięciu zer wiodących krótkie kody są dopełniane do 8 cyfr, a kody 9–12-cyfrowe do 13. UPC-A i odpowiadający mu EAN mogą wskazywać ten sam rekord. Inny kod w odpowiedzi jest błędem 69. Kod poprawny formalnie nie musi występować w bazie.

## Wartości odżywcze

Każdy zestaw zachowuje swoją podstawę: np. `per: serving`, `per_quantity: 250`, `per_unit: ml` albo `per: 100ml`. Składnik ma `name`, `value`, `unit`, `modifier` oraz odrębne pola obliczenia/proweniencji. Skrypt nie przelicza jednostek, nie skaluje porcji i nie zastępuje braków zerami. `source_per` wskazuje podstawę źródłową danego składnika w agregacie.

`value_computed` jest zachowane jako osobne surowe obliczenie OFF. Przechwycony rekord mleka ma `value: 60` kcal w agregacie na 100 ml oraz `value_computed: 150` i `source_per: serving`; porcja ma 250 ml i 150 kcal. Takie pola wymagają osobnej interpretacji i mogą być objęte ostrzeżeniem jakości OFF. Nie podstawiaj `value_computed` do `value` ani nie przypisuj mu automatycznie podstawy agregatu.

Puste tagi alergenów w tym samym rekordzie nie uprawniają do stwierdzenia „bez mleka”. Nazwa produktu, wykaz składników i zgłoszone alergeny mogą być niepełne lub sprzeczne. `absence_confirmed` nie przyjmuje wartości true. Nie wyciągaj wniosków zdrowotnych ani o tolerancji danego produktu.

## Licencja i środowiska

Źródło: Open Food Facts contributors, [warunki ponownego wykorzystania](https://world.openfoodfacts.org/terms-of-use), ODbL dla bazy i DbCL dla treści. Skrypt nie pobiera zdjęć (mają odrębną licencję CC BY-SA).

Staging produktu: `https://world.openfoodfacts.net`, Basic Auth `off:off`, zgodnie z publiczną dokumentacją. `--staging` nie wysyła zapytań do produkcyjnej wyszukiwarki. Testy regresyjne nie łączą się z siecią; próbki nie są fallbackiem produkcyjnym. Weryfikacja funkcji obejmowała odczyt produktu w staging i pojedyncze wyszukiwania tylko do odczytu w publicznej wyszukiwarce.
