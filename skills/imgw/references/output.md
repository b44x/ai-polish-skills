# IMGW-PIB CLI — Dokumentacja Wyjścia i Schematów Danych

Wszystkie polecenia zwracają sformatowany JSON na standardowym wyjściu (`stdout`), a błędy na `stderr`.
Brakujące wartości numeryczne zwracane są jako `null`, a puste listy jako `[]`.

---

## 1. `weather <stacja>`

Pobiera bieżące dane synoptyczne dla wybranej stacji meteorologicznej.

| Pole | Typ | Opis i Jednostki |
|---|---|---|
| `stationId` | string | 5-cyfrowy identyfikator stacji IMGW / WMO (np. `"12375"`) |
| `stationName` | string | Oficjalna nazwa stacji (np. `"Warszawa"`, `"Zakopane"`) |
| `measurementDate` | string | Data pomiaru w formacie `YYYY-MM-DD` |
| `measurementHour` | int | Godzina pomiaru w czasie UTC (np. `12`) |
| `measurementTime` | string | Pełny znacznik czasu (np. `"2026-09-28 12:00 UTC"`) |
| `temperatureC` | float | Temperatura powietrza w stopniach Celsjusza (°C) |
| `windSpeedMs` | float | Prędkość wiatru w metrach na sekundę (m/s) |
| `windDirectionDeg` | int | Kierunek wiatru w stopniach (0°–360°) |
| `relativeHumidityPercent` | float | Wilgotność względna powietrza w procentach (%) |
| `rainfallMm` | float | Suma opadu atmosferycznego za okres pomiarowy w milimetrach (mm) |
| `pressureHpa` | float \| null | Ciśnienie na poziomie morza w hektopaskalach (hPa). **Uwaga:** Na stacjach wysokogórskich (np. Zakopane, Kasprowy Wierch, Śnieżka) wartość ta wynosi `null` |
| `formatted` | object | Wygodne, gotowe ciągi tekstowe z jednostkami (`temperature`, `pressure`, `wind`, `humidity`, `rainfall`) |
| `coordinates` | object \| null | Współrzędne stacji `{lat, lon}` |
| `source` | string | Oznaczenie źródła danych (IMGW-PIB) |

### Przykład:
```json
{
  "stationId": "12375",
  "stationName": "Warszawa",
  "measurementDate": "2026-09-28",
  "measurementHour": 12,
  "measurementTime": "2026-09-28 12:00 UTC",
  "temperatureC": 20.4,
  "windSpeedMs": 3.0,
  "windDirectionDeg": 100,
  "relativeHumidityPercent": 50.3,
  "rainfallMm": 0.0,
  "pressureHpa": 1028.5,
  "formatted": {
    "temperature": "20.4 °C",
    "pressure": "1028.5 hPa",
    "wind": "3.0 m/s (100°)",
    "humidity": "50.3 %",
    "rainfall": "0.0 mm"
  },
  "coordinates": {
    "lat": 52.17,
    "lon": 20.97
  },
  "source": "Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy (IMGW-PIB)"
}
```

---

## 2. `synop [--sort ...] [--limit N]`

Zwraca zestawienie obserwacji dla wszystkich 62 stacji synoptycznych w Polsce.

Opcje sortowania:
- `name` (domyślnie alfabetycznie)
- `temp` (od najzimniejszych)
- `temp_desc` (od najcieplejszych)
- `wind_desc` (od najbardziej wietrznych)
- `pressure_desc` (od najwyższego ciśnienia)
- `rain_desc` (od największych opadów)

---

## 3. `near <lat> <lon> [--limit N]`

Wyszukuje najbliższą stację meteorologiczną do podanych współrzędnych GPS przy użyciu formuły ortodromy (Haversine) i domyślnie dołącza jej bieżący stan pogodowy.

| Pole | Typ | Opis |
|---|---|---|
| `queryCoordinates` | object | Zapytanie wejściowe `{lat, lon}` |
| `closestStation` | object | Najbliższa stacja wraz z odległością w km (`distanceKm`) oraz obiektem `weather` |
| `nearbyStations` | list | Lista N najbliższych stacji z odległościami w kilometrach |

---

## 4. `warnings [--type meteo|hydro|all] [--voivodeship V]`

Zwraca oficjalne ostrzeżenia IMGW-PIB.

| Pole | Typ | Opis |
|---|---|---|
| `number` | string | Numer ostrzeżenia |
| `type` | string | Typ: `"meteo"` lub `"hydro"` |
| `event` | string | Zjawisko (np. `"Susza hydrologiczna"`, `"Burze z gradem"`, `"Silny wiatr"`, `"Upał"`) |
| `level` | int \| string | Stopień ostrzeżenia (1, 2, 3 lub `-1` dla suszy hydrologicznej) |
| `published` | string | Czas publikacji ostrzeżenia |
| `validFrom` | string | Początek obowiązywania |
| `validTo` | string | Koniec obowiązywania |
| `probabilityPercent` | int \| null | Prawdopodobieństwo wystąpienia zjawiska w % (np. `90`) |
| `office` | string | Biuro prognoz IMGW wydające komunikat |
| `course` | string | Treść przebiegu i przewidywanych skutków |
| `comment` | string \| null | Dodatkowy komentarz synoptyka |
| `voivodeships` | string[] | Lista województw objętych ostrzeżeniem |

---

## 5. `hydro [--river R] [--station S] [--alarm-only]`

Zwraca pomiary ze stacji wodowskazowych na polskich rzekach.

| Pole | Typ | Opis |
|---|---|---|
| `stationId` | string | Identyfikator stacji wodowskazowej |
| `stationName` | string | Nazwa stacji (miejscowości) |
| `river` | string | Nazwa rzeki |
| `voivodeship` | string | Województwo |
| `status` | string | Status: `"normalny"`, `"ostrzegawczy"`, `"alarmowy"` |
| `waterLevelCm` | float \| null | Aktualny stan wody w centymetrach (cm) |
| `warningLevelCm` | float \| null | Stan ostrzegawczy w centymetrach (cm) |
| `alarmLevelCm` | float \| null | Stan alarmowy w centymetrach (cm) |
| `waterTemperatureC` | float \| null | Temperatura wody w °C (jeśli stacja mierzy) |
| `flowM3s` | float \| null | Przepływ wody w m³/s |
| `measurementDate` | string | Czas ostatniego pomiaru |

---

## 6. `stations [--search Q]`

Katalog 62 głównych stacji synoptycznych IMGW w Polsce. Działa w 100% w trybie offline (brak zapytań sieciowych).

---

## Kody Wyjścia

| Kod | Znaczenie | Akcja Agenta |
|---|---|---|
| `0` | Sukces | Odczytaj i przetwórz obiekt JSON z `stdout` |
| `2` | Nie znaleziono | Stacja lub rzeka nie istnieje; sprawdź podpowiedzi lub listę z `stations` |
| `64` | Błąd walidacji / argumentów | Sprawdź poprawność argumentów lub współrzędnych GPS |
| `69` | Błąd serwera IMGW / sieci | Chwilowy problem z serwerem IMGW; spróbuj ponownie za chwilę |

---

## Warunki Użytkowania Danych

Dane pochodzą z publicznych zasobów Instytutu Meteorologii i Gospodarki Wodnej – Państwowego Instytutu Badawczego (IMGW-PIB) dostępnych pod adresem `https://danepubliczne.imgw.pl/`. Zgodnie z regulaminem serwisu, użytkownik zobowiązany jest do każdorazowego podawania źródła pochodzenia danych (IMGW-PIB).
