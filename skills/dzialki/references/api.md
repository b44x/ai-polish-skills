# ULDK: format i weryfikacja

Endpoint `https://uldk.gugik.gov.pl/`, operacje:

| CLI | ULDK |
|---|---|
| `id` | `GetParcelById`, parametr `id` |
| `search` | `GetParcelByIdOrNr`, parametr `id=Nazwa obrębu numer` |
| `point` | `GetParcelByXY`, parametr `xy=longitude,latitude,4326` |

Każde zapytanie wskazuje `result=id,parcel,voivodeship,county,commune,region,datasource,geom_wkt` i `srid=4326` lub `2180`. `source_url` odtwarza pełne zapytanie.

Dla `id` i `point` pierwsza linia to status `0`, następne linie zawierają osiem pól rozdzielonych `|`. Dla `search` pierwsza linia jest liczbą znalezionych działek. Liczba musi odpowiadać faktycznej liczbie wierszy. Wyszukiwanie może zwrócić wiele działek, ponieważ nazwy obrębów powtarzają się w kraju. Wyświetlana lista zachowuje kolejność ULDK, bez rankingu „najlepszego dopasowania”.

Parser odróżnia prostą odpowiedź `-1 brak wyników` lub licznik wyszukiwania `0` od awarii. Komunikat `-1 brak wyników` z dodatkowym błędem XML lub innym komunikatem technicznym ma kod `69`. Brak geometrii, błędna liczba kolumn, niespójny CRS, niezamknięty pierścień i powtórzony identyfikator również kończą odczyt błędem. Nie są zamieniane w puste wyniki.

Obsługiwane geometrie to dwuwymiarowe POLYGON/MULTIPOLYGON z opcjonalnym prefiksem `SRID`. Limity klienta: odpowiedź 8 MiB, geometria 4 MiB, do 100 000 wierzchołków na obiekt i 1000 rekordów źródłowych. Parser sprawdza domknięcie pierścieni, skończone liczby i zakres współrzędnych; nie zastępuje pełnej walidacji topologicznej GIS.

## Weryfikacja na żywo

Przykłady pobrano 2026-11-06 z oficjalnego ULDK:

- [Działka 022602_1.0003.59, WGS84](https://uldk.gugik.gov.pl/?request=GetParcelById&id=022602_1.0003.59&result=id,parcel,voivodeship,county,commune,region,datasource,geom_wkt&srid=4326): Złotoryja (miasto), Obręb 3, źródło „powiat złotoryjski (wfs)”. Pełna odpowiedź w [parcel-wgs84.txt](../resources/parcel-wgs84.txt).
- [Ten sam identyfikator, PL-1992](https://uldk.gugik.gov.pl/?request=GetParcelById&id=022602_1.0003.59&result=id,parcel,voivodeship,county,commune,region,datasource,geom_wkt&srid=2180): poprawnie przeliczone metry. [parcel-2180.txt](../resources/parcel-2180.txt).
- [Krzewina 134](https://uldk.gugik.gov.pl/?request=GetParcelByIdOrNr&id=Krzewina%20134&result=id,parcel,voivodeship,county,commune,region,datasource,geom_wkt&srid=4326): odpowiedź z licznikiem `1`, identyfikator `022503_5.0003.134`. [search.txt](../resources/search.txt).
- `GetParcelByXY` z `xy=15.915,51.12315,4326` zwróciło działkę `022602_1.0003.59`, zgodnie z odczytem po identyfikatorze.

Pliki są zapisanymi odpowiedziami do testów offline; produkcyjne CLI zawsze odczytuje API lub świeży cache, nie używa plików jako danych zastępczych.

Zasady atrybucji, źródła danych i limity IP: [specyfikacja ULDK, FAQ](https://uldk.gugik.gov.pl/opis.html).
