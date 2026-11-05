# Wynik GIOŚ

`stations` zwraca listę stacji: ID, nazwę, miasto, województwo, ulicę i współrzędne WGS84.
`station` oraz `near` zwracają `station`, `index` i `measurements`; `near` dodaje `distance_km` (odległość w linii prostej).

Każdy pomiar ma `sensor_id`, `pollutant`, `unit`, `value`, `measured_at`, `latest_slot_at` i `status`:

- `available`: najnowszy przedział ma wartość.
- `latest_slot_missing`: zwrócono wcześniejszy, ostatni niepusty pomiar; jego czas jest w `measured_at`.
- `no_current_data`: seria jest pusta, wszystkie wartości są null albo API nie udostępnia bieżących danych czujnika. `value` i `measured_at` są null.

Nie porównuj wieku pomiaru z czasem pobrania bez uwzględnienia stref: pomiary i indeks są w czasie Europe/Warsaw, a `fetched_at` ma jawny offset UTC. API nie rozróżnia dwóch identycznych godzin lokalnych podczas jesiennej zmiany czasu; zachowujemy zapis źródłowy. Wszystkie stężenia, również CO, w µg/m³. Dane wstępne, niezweryfikowane.

`index.status` zachowuje flagę indeksu ogólnego z GIOŚ. Przy null lub false zaznacz brak/niepełność indeksu, zamiast zapewniać o dobrej jakości powietrza.

## Przykład z rzeczywistego uruchomienia

Zapis z 2026-11-04T21:20:53+00:00. Skrócony widok; pełny wynik w materiale demo.

```json
{
  "station": {
    "id": 400,
    "name": "Kraków, Aleja Krasińskiego",
    "city": "Kraków",
    "voivodeship": "MAŁOPOLSKIE",
    "street": "Al. Krasińskiego",
    "latitude": 50.057678,
    "longitude": 19.926189
  },
  "index": {
    "value": 1,
    "category": "Dobry",
    "calculated_at": "2026-11-04 22:10:35",
    "measured_at": "2026-11-04 22:00:00",
    "status": true
  },
  "measurements": [
    {
      "sensor_id": 2750,
      "pollutant": "PM10",
      "unit": "µg/m³",
      "value": 22.2,
      "measured_at": "2026-11-04 22:00:00",
      "latest_slot_at": "2026-11-04 22:00:00",
      "status": "available"
    },
    {
      "sensor_id": 2752,
      "pollutant": "PM2.5",
      "unit": "µg/m³",
      "value": 14.6,
      "measured_at": "2026-11-04 22:00:00",
      "latest_slot_at": "2026-11-04 22:00:00",
      "status": "available"
    }
  ],
  "measurement_timezone": "Europe/Warsaw",
  "note": "Dane GIOŚ są wstępne. Czas pomiaru może różnić się między czujnikami; brak pomiaru nie oznacza zera.",
  "distance_km": 1.02,
  "source": "GIOŚ",
  "source_url": "https://api.gios.gov.pl/pjp-api/v1/rest/",
  "fetched_at": "2026-11-04T21:20:53.397246+00:00"
}
```
