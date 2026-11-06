# Próbki do testów offline

`product-v3.6.json`: ograniczona do potrzebnych pól odpowiedź API v3.6 ze **staging** Open Food Facts (`world.openfoodfacts.net`), kod 5901432003117, pobrana 2026-11-06. Nazwa: Mleko 3.2%, Mleczna Dolina. Dane staging mogą być inne niż produkcyjne.

`search.json`: dwa skróty wyników publicznego Search-a-licious dla `countries_tags:"en:poland" mleko`, pobrane 2026-11-06; usunięto techniczny obiekt debug, zachowano pola produktu i paginację.

Źródło: **Open Food Facts contributors**. Baza ODbL 1.0, treści DbCL 1.0; [warunki](https://world.openfoodfacts.org/terms-of-use). Próbki służą wyłącznie testom parsera. CLI nie używa ich zamiast bieżącej odpowiedzi API; testy tworzą dodatkowe warianty błędów i braków w pamięci.
