# Wynik i zakres RCN

- `records`: rekordy obiektów, posortowane malejąco według daty aktu; remisy rozstrzyga `gid`. `feature_id` identyfikuje wiersz warstwy, a para `transaction_namespace` + `transaction_id` transakcję. Pola `deed_number`, `deed_creator` i `deed_date`, razem z przestrzenią nazw, identyfikują akt: jeden akt zbiorczy może mieć wiele identyfikatorów transakcji.
- `area_m2`: powierzchnia użytkowa lokalu/budynku lub ewidencyjna działki. Nie oznacza powierzchni udziału. Cena obiektu pochodzi odpowiednio z `LOK_CENA_BRUTTO`, `BUD_CENA_BRUTTO`, `DZI_CENA_BRUTTO`; brak wartości nie jest zerem.
- `summary.groups`: osobne grupy według rynku i roku aktu. `count` to liczba porównywalnych transakcji w pobranej i przefiltrowanej próbie, nie liczba transakcji na rynku. Akty z wieloma obiektami są wykluczane przed filtrowaniem; cena obiektu musi odpowiadać cenie całej transakcji, co odrzuca również pojedynczy widoczny składnik większego pakietu. Mediana opiera się na stawkach za m² zaokrąglonych do groszy. Opis obiektu może ujawniać dodatkowe składniki ceny, dlatego porównywalność wymaga oceny kontekstu.
- `scan_limit_reached: true` / `has_more: null`: zapytanie osiągnęło limit próby; istnienie kolejnej strony nie zostało sprawdzone. `display_limit_reached` dotyczy wyłącznie listy, nie próby statystycznej.
- `location.shape: square`: pole `radius_km` opisuje połowę boku kwadratu w PL-1992. Dla `bbox_wgs84` krawędzie są próbkowane w 41 punktach i przeliczane do prostokąta PL-1992 z dwumetrowym marginesem, aby uwzględnić krzywiznę odwzorowania.
- `source_url`: odtwarzalne pierwsze zapytanie WFS; filtry obszaru są w URL, a pozostałe filtry znajdują się w `filters`. Brak danych jest kodem `2` i opisem zakresu próby na stderr.

## WFS i współrzędne

Endpoint: `https://mapy.geoportal.gov.pl/wss/service/rcn`.
`GetCapabilities` i `DescribeFeatureType` opisują warstwy `ms:lokale`, `ms:budynki`, `ms:dzialki`. Skrypt używa `GetFeature`, WFS 2.0.0, GML 3.2 oraz `startIndex/count`.

Zapytania pozostają w natywnym EPSG:2180. W BBOX tego WFS kolejność osi to **northing, easting**, zgodna z deklaracją EPSG:2180. Współrzędne WGS84 są przeliczane lokalnie przez odwzorowanie poprzeczne Mercatora GRS80: południk 19°, skala 0,9993, przesunięcie northing −5 300 000 m, easting 500 000 m. Przy wyszukiwaniu okolicy pomijalna jest różnica WGS84/ETRS89.

Podczas weryfikacji 2026-11-05 jawne `srsName=EPSG:4326` dawało błędnie opisane, nieprzeliczone współrzędne, a zapytania WGS84 BBOX — fałszywie puste wyniki. Skrypt celowo wysyła natywny BBOX i nie żąda transformacji po stronie serwera. Nie interpretuje natywnych współrzędnych jako stopni.

Oficjalny opis zakresu i tymczasowego charakteru usługi: [Geoportal — RCN](https://www.geoportal.gov.pl/pl/dane/rejestr-cen-nieruchomosci-rcn/). Limitu zapytań nie opublikowano; klient wykonuje najwyżej 10 ograniczonych zapytań na uruchomienie i zatrzymuje się na błędzie HTTP.
