# IMGW-PIB CLI — Output and Data Schema Reference

All commands return formatted JSON on standard output (`stdout`), and errors on `stderr`.
Missing numeric values are returned as `null`, and empty lists as `[]`.

---

## 1. `weather <station>`

Fetches current synoptic data for the selected meteorological station.

| Field | Type | Description and Units |
|---|---|---|
| `stationId` | string | 5-digit IMGW / WMO station identifier (e.g. `"12375"`) |
| `stationName` | string | Official station name (e.g. `"Warszawa"`, `"Zakopane"`) |
| `measurementDate` | string | Measurement date in `YYYY-MM-DD` format |
| `measurementHour` | int | Measurement hour in UTC (e.g. `12`) |
| `measurementTime` | string | Full timestamp (e.g. `"2026-09-28 12:00 UTC"`) |
| `temperatureC` | float | Air temperature in degrees Celsius (°C) |
| `windSpeedMs` | float | Wind speed in meters per second (m/s) |
| `windDirectionDeg` | int | Wind direction in degrees (0°–360°) |
| `relativeHumidityPercent` | float | Relative air humidity in percent (%) |
| `rainfallMm` | float | Total precipitation over the measurement period in millimeters (mm) |
| `pressureHpa` | float \| null | Sea-level pressure in hectopascals (hPa). **Note:** At high-mountain stations (e.g. Zakopane, Kasprowy Wierch, Śnieżka) this value is `null` |
| `formatted` | object | Convenient, ready-made text strings with units (`temperature`, `pressure`, `wind`, `humidity`, `rainfall`) |
| `coordinates` | object \| null | Station coordinates `{lat, lon}` |
| `source` | string | Data source attribution (IMGW-PIB) |

### Example:
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

Returns a summary of observations for all 62 synoptic stations in Poland.

Sorting options:
- `name` (default, alphabetical)
- `temp` (coldest first)
- `temp_desc` (warmest first)
- `wind_desc` (windiest first)
- `pressure_desc` (highest pressure first)
- `rain_desc` (highest precipitation first)

---

## 3. `near <lat> <lon> [--limit N]`

Finds the meteorological station nearest to the given GPS coordinates using the great-circle (Haversine) formula and by default includes its current weather.

| Field | Type | Description |
|---|---|---|
| `queryCoordinates` | object | Input query `{lat, lon}` |
| `closestStation` | object | Nearest station with distance in km (`distanceKm`) and a `weather` object |
| `nearbyStations` | list | List of the N nearest stations with distances in kilometers |

---

## 4. `warnings [--type meteo|hydro|all] [--voivodeship V]`

Returns official IMGW-PIB warnings.

| Field | Type | Description |
|---|---|---|
| `number` | string | Warning number |
| `type` | string | Type: `"meteo"` or `"hydro"` |
| `event` | string | Phenomenon (e.g. `"Susza hydrologiczna"`, `"Burze z gradem"`, `"Silny wiatr"`, `"Upał"`) |
| `level` | int \| string | Warning level (1, 2, 3 or `-1` for hydrological drought) |
| `published` | string | Warning publication time |
| `validFrom` | string | Start of validity |
| `validTo` | string | End of validity |
| `probabilityPercent` | int \| null | Probability of the phenomenon occurring in % (e.g. `90`) |
| `office` | string | IMGW forecast office issuing the notice |
| `course` | string | Description of the expected course and impacts |
| `comment` | string \| null | Additional forecaster comment |
| `voivodeships` | string[] | List of voivodeships (województwa) covered by the warning |

---

## 5. `hydro [--river R] [--station S] [--alarm-only]`

Returns measurements from water-gauge stations on Polish rivers.

| Field | Type | Description |
|---|---|---|
| `stationId` | string | Water-gauge station identifier |
| `stationName` | string | Station name (locality) |
| `river` | string | River name |
| `voivodeship` | string | Voivodeship (województwo) |
| `status` | string | Status: `"normalny"`, `"ostrzegawczy"`, `"alarmowy"` |
| `waterLevelCm` | float \| null | Current water level in centimeters (cm) |
| `warningLevelCm` | float \| null | Warning level in centimeters (cm) |
| `alarmLevelCm` | float \| null | Alarm level in centimeters (cm) |
| `waterTemperatureC` | float \| null | Water temperature in °C (if measured by the station) |
| `flowM3s` | float \| null | Water flow in m³/s |
| `measurementDate` | string | Time of the latest measurement |

---

## 6. `stations [--search Q]`

Catalog of the 62 main IMGW synoptic stations in Poland. Works 100% offline (no network requests).

---

## Exit Codes

| Code | Meaning | Agent Action |
|---|---|---|
| `0` | Success | Read and process the JSON object from `stdout` |
| `2` | Not found | Station or river does not exist; check the suggestions or the list from `stations` |
| `64` | Validation / argument error | Check the arguments or GPS coordinates |
| `69` | IMGW server / network error | Temporary problem with the IMGW server; try again shortly |

---

## Data Terms of Use

The data comes from the public resources of the Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy (IMGW-PIB), available at `https://danepubliczne.imgw.pl/`. In accordance with the service's terms, the user is required to cite the data source (IMGW-PIB) every time.
