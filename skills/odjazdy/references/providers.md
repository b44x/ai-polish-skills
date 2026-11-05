# Dostawcy i schemat danych

Sprawdzono 2026-11-05. Integracje korzystają z publicznych usług operatorów bez kluczy i kont użytkowników.

| Sieć | Katalog / wyszukiwanie | Tablica | Warunki |
|---|---|---|---|
| ZTM Gdańsk | `stops.json`, dzienne pakiety `YYYY-MM-DD`, pola `stopId`, `stopDesc`, `stopLat`, `stopLon` | `/departures?stopId=…`, `lastUpdate`, `departures`, status `REALTIME` lub `SCHEDULED` | [Otwarty Gdańsk](https://ckan.multimediagdansk.pl/dataset/tristar), CC BY |
| ZTM Poznań / PEKA | POST `method.vm`: `getStopPoints` (`pattern`), `getBollardsByStopPoint` (`name`) | `getTimes` (`symbol` = `bollard.tag`, ewentualnie `symbol` gdy tag nieobecny), `getServerTime` | [Oficjalny Wirtualny Monitor](https://www.peka.poznan.pl/vm/), [zasady ZTM](https://www.ztm.poznan.pl/otwarte-dane/dla-deweloperow/) |
| ZDiTM Szczecin | `https://www.zditm.szczecin.pl/api/v2/stops`, pole `number` | `/api/v2/departure-boards/{number}?limit=…`, `data.updated_at` | [Dokumentacja przystanków](https://www.zditm.szczecin.pl/pl/zditm/dla-programistow/api-przystanki), [tablice](https://www.zditm.szczecin.pl/pl/zditm/dla-programistow/api-tablice-odjazdow), CC0 1.0, 100 żądań/min/IP |

Gdańsk publikuje katalog: `https://ckan.multimediagdansk.pl/dataset/tristar/resource/4c4025f0-01bf-41f7-a39f-d156d201b82b/download/stops.json`. Tablice: `https://ckan2.multimediagdansk.pl/departures`.

PEKA nie ma tu deklaracji stabilnego, wersjonowanego API: korzystamy z backendu publicznego interfejsu. Nazwy metod i semantykę potwierdzono w [kodzie oficjalnego klienta](https://www.peka.poznan.pl/vm/scripts/dao.js). [Oficjalny parser dat](https://www.peka.poznan.pl/vm/scripts/vm_rwd.js) formatuje lokalny zegar z dosłownym `Z`; próbny odczyt i zegar serwera potwierdziły tę różnicę. Zachowujemy surowy czas i osobne `scheduled_local`, aby nie przesuwać odjazdu o godzinę/dwie. Nie używamy logowania ani danych kont PEKA.

## Wynik `departures`

- `scheduled_at`, `estimated_at`: czasy UTC od Gdańska/Szczecina; `estimated_at` jest null dla kursu rozkładowego. Dla PEKA `scheduled_at` jest null, a `scheduled_local` ma odrębne `scheduled_timezone: Europe/Warsaw`; `estimated_at` jest przybliżeniem z minut dostawcy.
- `delay_seconds`: podpisane opóźnienie (wartość ujemna = wcześniej), null jeśli nieznane. Dla PEKA nie wyliczamy opóźnienia z minut do odjazdu.
- `freshness`: `current` dla tablicy z czasem źródła nie starszym niż 180 s ani ponad 60 s w przyszłości; `stale` poza tym zakresem; `unknown` przy braku czasu źródła. To techniczny próg skilla, nie gwarancja operatora.
- `vehicle_updated_at`, `measurement_stale`: dodatkowy czas konkretnego pojazdu, gdy Gdańsk go podaje. Null oznacza brak informacji.
- `realtime` zachowuje deklarację operatora; `usable_realtime` dodatkowo uwzględnia czas i odwołanie.
- `messages`, `warnings`: komunikaty i ograniczenia. Pusta lista odjazdów jest poprawną odpowiedzią. Sieć i uszkodzona odpowiedź są błędami, nie pustą listą.

Poznań zwraca ograniczone podpowiedzi nazw. Skill rozwija najwyżej trzy grupy i oznacza ucięcie; `matched_count` jest liczbą pobranych słupków, nie pełną liczbą pasujących słupków w całej aglomeracji. GPS obsługują Gdańsk i Szczecin. Numery słupków mają zasięg konkretnego miasta i nie są wymienne.
