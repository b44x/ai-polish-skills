# NFZ CLI — Output and Data Schema Reference

All `scripts/nfz.py` commands return structured, valid JSON on standard output (`stdout`), and errors on standard error (`stderr`).
Missing or unavailable values are represented as `null`, and empty lists as `[]`.

---

## 1. `benefits <phrase>`

Searches for official service names in the NFZ catalog/dictionary.

### Response fields:
| Field | Type | Description |
|---|---|---|
| `query` | string | Search phrase (min. 3 characters) |
| `count` | int | Number of official services found |
| `benefits` | string[] | List of official NFZ service names, written in uppercase |
| `source` | string | Official data source |

### Example:
```json
{
  "query": "rezonans",
  "count": 1,
  "benefits": [
    "REZONANS MAGNETYCZNY"
  ],
  "source": "Narodowy Fundusz Zdrowia (apinfz.nfz.gov.pl)"
}
```

---

## 2. `queues [--benefit B] [--province P] [--locality L] [...]`

Fetches data on queues and the estimated waiting time (PCUŚ) for the specified service and location.

### Queue / facility object fields (`results[]`):
| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier of the queue / service in the NFZ register |
| `benefit` | string | Official name of the medical service |
| `provider` | string | Full name of the healthcare entity (service provider, *świadczeniodawca*) |
| `place` | string | Name of the place where services are provided (ward, clinic, lab) |
| `locality` | string | Locality (town/city) |
| `address` | string | Street and building number |
| `phone` | string \| null | Contact phone number |
| `case` | string | Admission mode: `"stabilny"` (przypadek stabilny, stable case) or `"pilny"` (przypadek pilny, urgent case) |
| `waitingTime` | object | Estimated waiting time data (PCUŚ) |
| `waitingTime.pcus` | string \| null | Estimated waiting time in NFZ text format (e.g. `"1 mies. 3 tyg."`, `"4 dni"`) |
| `waitingTime.averagePeriodDays` | int \| null | Average estimated waiting time in days (numeric value for sorting and comparisons) |
| `waitingTime.awaiting` | int \| null | Number of people currently waiting in the queue |
| `waitingTime.dateSituationAsAt` | string \| null | Date of the queue snapshot (format `YYYY-MM-DD`) |
| `waitingTime.statisticsUpdateMonth` | string \| null | Month of the statistics update (format `YYYY-MM`) |
| `coordinates` | object \| null | Geographic coordinates `{lat, lon, isApproximate}` (`isApproximate` flags approximate coordinates) |
| `distanceKm` | float \| null | Distance in kilometers from the given reference point (if provided) |
| `queueInCer` | bool | Whether the queue is covered by Centralna e-Rejestracja (central e-registration) (`true`/`false`) |
| `accessibility` | object | Facilities for people with disabilities (`toilet`, `ramp`, `carPark`, `elevator`, `ac`) |
| `source` | string | Official source identifier |

### Example:
```json
{
  "benefit": "REZONANS MAGNETYCZNY",
  "province": "11",
  "locality": "Gdańsk",
  "case": "stabilny",
  "count": 1,
  "results": [
    {
      "id": "5c7044e8-6bb3-0369-e063-b4200a0a4532",
      "benefit": "REZONANS MAGNETYCZNY",
      "provider": "NADMORSKIE CENTRUM MEDYCZNE SP. Z O.O.",
      "place": "PRACOWNIA REZONANSU MAGNETYCZNEGO 3T",
      "locality": "GDAŃSK",
      "address": "ŚWIĘTOKRZYSKA 4",
      "phone": "+48 58 763 98 85",
      "case": "stabilny",
      "waitingTime": {
        "pcus": "1 mies. 3 tyg.",
        "averagePeriodDays": 63,
        "awaiting": 820,
        "dateSituationAsAt": "2026-09-02",
        "statisticsUpdateMonth": "2026-08"
      },
      "coordinates": {
        "lat": 54.325971,
        "lon": 18.606809,
        "isApproximate": false
      },
      "distanceKm": null,
      "queueInCer": false,
      "accessibility": {
        "toilet": true,
        "ramp": true,
        "carPark": true,
        "elevator": true,
        "ac": true
      },
      "source": "Narodowy Fundusz Zdrowia (apinfz.nfz.gov.pl)"
    }
  ]
}
```

---

## 3. `near <location|lat> [lon] --benefit <B> [--radius-km R] [--sort time|distance]`

Finds facilities providing the given service within the given geographic radius (default 50 km).

### Response fields:
| Field | Type | Description |
|---|---|---|
| `query` | object | Query parameters: `benefit`, `location`, `coordinates`, `radiusKm`, `case` |
| `count` | int | Number of facilities found within the radius |
| `results` | object[] | List of facilities sorted by the chosen criterion (`time` or `distance`), including the computed `distanceKm` field |
| `source` | string | Official source |

---

## 4. `compare --benefit <B> [--locality L] [--province P] [--limit N]`

Lists facilities for the given service side by side and generates a summary of extreme values (`highlights`).

### `highlights` section fields:
| Field | Type | Description |
|---|---|---|
| `shortestWaitClinic` | object \| null | Facility with the shortest estimated waiting time (`place`, `locality`, `pcus`, `averageDays`) |
| `fewestAwaitingClinic` | object \| null | Facility with the fewest waiting patients (`place`, `locality`, `awaitingCount`) |
| `closestClinic` | object \| null | Facility closest to the reference point (if a locality was given) |

---

## 5. `provinces`

Returns the list of the 16 Polish voivodeships (województwa) with their official two-digit NFZ codes.
The command works 100% offline (from a built-in dictionary).

---

## Exit Codes

| Code | Meaning | Agent Action |
|---|---|---|
| `0` | Success | Read and process the JSON object from `stdout` |
| `2` | Not found | No facilities or no such service in the NFZ database |
| `64` | Validation / argument error | Check the phrase length (min. 3 characters), the voivodeship code or the coordinates |
| `69` | NFZ server / network error | Upstream API error or network problem; try again |

---

## Medical Neutrality Rules and Legal Limitations

1. **PCUŚ is not an appointment date:** The `waitingTime.pcus` value is the *Prognozowany Czas Oczekiwania na Świadczenie* (estimated waiting time for a service), calculated statistically by NFZ from historical facility data. It is not a booking nor a guaranteed first free appointment.
2. **Medical neutrality:** This skill is a tool for accessing NFZ administrative data. It does not generate diagnoses, recommend therapies or assess doctors' competence.
3. **Phone verification:** The agent should always recommend contacting the facility directly by phone to confirm the queue is current and to book an appointment.
