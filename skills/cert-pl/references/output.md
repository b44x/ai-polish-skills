# Wynik sprawdzenia CERT

- `domain`: znormalizowana domena ASCII (IDNA), bez ścieżki i parametrów URL.
- `listed`, `status`: `true` / `listed` lub `false` / `not_listed`. Oba wyniki mają kod wyjścia 0.
- `matched_domain`: dokładny wpis listy dopasowany do hosta albo jego domeny nadrzędnej; `null` przy braku wpisu.
- `list_fetched_at`: czas pobrania listy w UTC, nie czas zgłoszenia domeny do CERT.
- `cached`: czy wykorzystano lokalną listę młodszą niż 5 minut.
- `source`, `message`: źródło oraz interpretacja wyniku. Brak wpisu nie dowodzi bezpieczeństwa.

Cache zapisuje tylko publiczną listę i czas jej pobrania; nie zapisuje sprawdzanych adresów.
Przy błędzie odświeżenia nie zwracamy wyniku z nieaktualnej listy.

## Przykład z rzeczywistego uruchomienia

Zapis z 2026-11-04T21:20:49+00:00. Wynik historyczny, nie bieżąca ocena domeny.

```json
{
  "domain": "cert.pl",
  "listed": false,
  "matched_domain": null,
  "status": "not_listed",
  "message": "Nie znaleziono na liście CERT Polska. Nie jest to potwierdzenie bezpieczeństwa.",
  "source": "https://hole.cert.pl/domains/v2/domains.txt",
  "list_fetched_at": "2026-11-04T21:16:03.647825+00:00",
  "cached": true
}
```
