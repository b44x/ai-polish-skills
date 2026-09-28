# NFZ CLI — Dokumentacja Wyjścia i Schematów Danych

Wszystkie polecenia `scripts/nfz.py` zwracają ustrukturyzowany, poprawny JSON na standardowym wyjściu (`stdout`), a błędy na standardowym wyjściu błędów (`stderr`).
Wartości brakujące lub niedostępne reprezentowane są jako `null`, a puste listy jako `[]`.

---

## 1. `benefits <fraza>`

Wyszukuje oficjalne nazwy świadczeń w katalogu/słowniku NFZ.

### Pola odpowiedzi:
| Pole | Typ | Opis |
|---|---|---|
| `query` | string | Wyszukiwana fraza (min. 3 znaki) |
| `count` | int | Liczba znalezionych oficjalnych świadczeń |
| `benefits` | string[] | Lista oficjalnych nazw świadczeń NFZ pisanych wielkimi literami |
| `source` | string | Oficjalne źródło danych |

### Przykład:
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

Pobiera dane o kolejkach i prognozowanym czasie oczekiwania (PCUŚ) dla wskazanego świadczenia i lokalizacji.

### Pola obiektu kolejki / placówki (`results[]`):
| Pole | Typ | Opis |
|---|---|---|
| `id` | string | Unikalny identyfikator kolejki / świadczenia w rejestrze NFZ |
| `benefit` | string | Oficjalna nazwa świadczenia medycznego |
| `provider` | string | Pełna nazwa podmiotu leczniczego (świadczeniodawcy) |
| `place` | string | Nazwa miejsca udzielania świadczeń (oddział, poradnia, pracownia) |
| `locality` | string | Miejscowość |
| `address` | string | Ulica i numer budynku |
| `phone` | string \| null | Numer telefonu kontaktowego |
| `case` | string | Tryb przyjęcia: `"stabilny"` (przypadek stabilny) lub `"pilny"` (przypadek pilny) |
| `waitingTime` | object | Dane o prognozowanym czasie oczekiwania (PCUŚ) |
| `waitingTime.pcus` | string \| null | Prognozowany czas oczekiwania w formacie tekstowym NFZ (np. `"1 mies. 3 tyg."`, `"4 dni"`) |
| `waitingTime.averagePeriodDays` | int \| null | Średni prognozowany czas oczekiwania w dniach (wartość numeryczna do sortowania i porównań) |
| `waitingTime.awaiting` | int \| null | Liczba osób aktualnie oczekujących w kolejce |
| `waitingTime.dateSituationAsAt` | string \| null | Data stanu kolejki (format `YYYY-MM-DD`) |
| `waitingTime.statisticsUpdateMonth` | string \| null | Miesiąc aktualizacji statystyk (format `YYYY-MM`) |
| `coordinates` | object \| null | Współrzędne geograficzne `{lat, lon, isApproximate}` |
| `distanceKm` | float \| null | Odległość w kilometrach od zadanego punktu odniesienia (jeśli podano) |
| `queueInCer` | bool | Czy kolejka jest objęta Centralną e-Rejestracją (`true`/`false`) |
| `accessibility` | object | Udogodnienia dla osób z niepełnosprawnościami (`toilet`, `ramp`, `carPark`, `elevator`, `ac`) |
| `source` | string | Identyfikator oficjalnego źródła |

### Przykład:
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

Wyszukuje placówki wykonujące dane świadczenie w zadanym promieniu geograficznym (domyślnie 50 km).

### Pola odpowiedzi:
| Pole | Typ | Opis |
|---|---|---|
| `query` | object | Parametry zapytania: `benefit`, `location`, `coordinates`, `radiusKm`, `case` |
| `count` | int | Liczba znalezionych placówek w promieniu |
| `results` | object[] | Lista placówek posortowana wg wybranego kryterium (`time` lub `distance`), zawierająca wyliczone pole `distanceKm` |
| `source` | string | Oficjalne źródło |

---

## 4. `compare --benefit <B> [--locality L] [--province P] [--limit N]`

Zestawia obok siebie placówki dla danego świadczenia i generuje podsumowanie skrajnych wartości (`highlights`).

### Pola sekcji `highlights`:
| Pole | Typ | Opis |
|---|---|---|
| `shortestWaitClinic` | object \| null | Placówka z najkrótszym prognozowanym czasem oczekiwania (`place`, `locality`, `pcus`, `averageDays`) |
| `fewestAwaitingClinic` | object \| null | Placówka z najmniejszą liczbą oczekujących pacjentów (`place`, `locality`, `awaitingCount`) |
| `closestClinic` | object \| null | Najbliższa placówka do punktu odniesienia (jeśli podano miejscowość) |

---

## 5. `provinces`

Zwraca listę 16 polskich województw wraz z ich oficjalnymi dwucyfrowymi kodami NFZ.
Polecenie działa w 100% offline (ze wbudowanego słownika).

---

## Kody Wyjścia

| Kod | Znaczenie | Działanie Agenta |
|---|---|---|
| `0` | Sukces | Odczytaj i przetwórz obiekt JSON z `stdout` |
| `2` | Nie znaleziono | Brak placówek lub brak świadczenia w bazie NFZ |
| `64` | Błąd walidacji / argumentów | Sprawdź długość frazy (min. 3 znaki), poprawność kodu województwa lub współrzędnych |
| `69` | Błąd serwera NFZ / sieci | Błąd upstream API lub problem sieciowy; spróbuj ponownie |

---

## Zasady Medycznej Neutralności i Prawne Ograniczenia

1. **PCUŚ to nie data wizyty:** Wartość `waitingTime.pcus` to *Prognozowany Czas Oczekiwania na Świadczenie* wyliczany statystycznie przez NFZ na podstawie historycznych danych z placówek. Nie jest to rezerwacja ani gwarantowany pierwszy wolny termin.
2. **Neutralność medyczna:** Niniejszy skill jest narzędziem dostępu do danych administracyjnych NFZ. Nie generuje diagnoz, nie zaleca terapii i nie ocenia kompetencji lekarzy.
3. **Weryfikacja telefoniczna:** Agent powinien zawsze zalecać bezpośredni kontakt telefoniczny z placówką w celu potwierdzenia aktualności kolejki i umówienia wizyty.
