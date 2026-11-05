# Próbki do testów offline

Przycięte odpowiedzi publicznych usług z 2026-11-05: `poznan-stops.json` (`getBollardsByStopPoint`, Rondo Kaponiera), `poznan-departures.json` (`getTimes`, RKAP71) i `szczecin-departures.json` (API v2, 10822). Służą wyłącznie testom; CLI nigdy nie używa ich jako zamiennika aktualnych danych.

Źródła i warunki: [opis dostawców](../references/providers.md). Dane Poznania: ZTM Poznań/PEKA, dane Szczecina: ZDiTM Szczecin (CC0 1.0). Odpowiedzi zostały skrócone, aby zachować przypadki na żywo, rozkładowe oraz opóźnienia. Dodatkowe syntetyczne warianty (odwołania, stare daty, błędy) tworzą testy w pamięci.
