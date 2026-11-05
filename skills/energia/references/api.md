# Źródło i semantyka danych

- [PSE — dokumentacja API](https://api.raporty.pse.pl/).
- [Oficjalne mapowanie API v1 → v2](https://api.raporty.pse.pl/EndpointsMap.pdf), raport `rce-pln`.
- Zasób: `https://api.raporty.pse.pl/api/rce-pln`.

Sprawdzony 2026-11-05 filtr: `$filter=business_date ge '2026-11-01' and business_date le '2026-11-04'`, rozmiar strony `$first=1000`. Skrypt obsługuje `nextLink`, dopuszczając wyłącznie HTTPS tego samego hosta i zasobu. Limit: 8 stron, 4000 rekordów, 8 MiB na odpowiedź, 20 sekund na zapytanie. Zakres zapytania jest ograniczony do 31 dni; niepełne pobranie kończy się błędem, a nie częściowym sukcesem.

`value` zawiera m.in. `business_date`, `rce_pln`, `dtime_utc`, `period_utc` i `publication_ts_utc`. `dtime_utc` jest **końcem** przedziału. Jego początek wynika z długości `period_utc`. Zachowywane są opublikowane przedziały 15- lub 60-minutowe. Kolejne wersje tego samego końca przedziału są rozstrzygane według czasu publikacji; sprzeczne rekordy z identycznym czasem publikacji są błędem formatu.

Granice doby oblicza się dla Europe/Warsaw według reguły UE obowiązującej w obsługiwanych latach od 2024: zmiana w ostatnią niedzielę marca i października o 01:00 UTC. Implementacja jest samodzielna także na Pythonie 3.8. Nie opiera kolejności przedziałów na niejednoznacznym lokalnym zegarze.

Kompletność wymaga ciągłego pokrycia całej doby bez luk lub nakładania przedziałów. `expected_quarter_hours` wynosi zwykle 96, przy zmianie czasu 92 lub 100. Średnie są ważone długością przedziałów, bez wag zużycia i bez zaokrąglania ceny przed obliczeniem średniej. W oknie `--kwh` zużycie rozkłada się równomiernie w czasie.

Cache: `~/.cache/ai-polish-skills/energia/`, TTL 300 sekund, czas oryginalnego pobrania w `fetched_at` (UTC). `latest_publication_at` pochodzi z PSE; `cached` informuje o lokalnym odczycie. Przy odświeżaniu nie stosuje się przeterminowanych danych jako zastępstwa za błąd API. `--no-cache` pomija odczyt i zapis.

Przykładowe odpowiedzi w `../resources/` służą wyłącznie testom offline. Skrypt produkcyjny ich nie odczytuje.
