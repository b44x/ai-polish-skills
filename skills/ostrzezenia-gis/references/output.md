# Źródło, wynik i ograniczenia

Źródło: [Ostrzeżenia GIS](https://www.gov.pl/web/gis/ostrzezenia). Stan struktury sprawdzono 2026-11-06. Nie znaleziono zadeklarowanego kanału RSS na stronie; wykorzystywany jest HTML. Skrypt rozpoznaje `article-area__article`, listę `art-prev`, daty oraz rzeczywisty link `js-pagination-page-next`. Detal używa `event-date` i `editor-content`.

`list` zwraca tytuł, `published_at` i `url`. `search` pobiera tekst każdego komunikatu spełniającego filtr dat w wybranych stronach. `notices` ogranicza `--limit`, natomiast `matched_in_scope` obejmuje wszystkie dopasowania w tej próbie. Puste `notices` jest poprawnym wynikiem wyszukiwania z opisem zakresu, nie dowodem bezpieczeństwa produktu.

`scope` opisuje:

- `scanned_pages` i `page_urls`: rzeczywiście pobrane strony listy;
- `listed_notices`: liczba unikalnych datowanych pozycji na tych stronach; `searched_notices`: liczba pobranych i przeszukanych tekstów komunikatów po filtrze dat;
- `publication_date_from/to`: żądany filtr dat publikacji;
- `oldest_listed_date/newest_listed_date`: zakres dat pozycji w pobranej próbie przed filtrowaniem;
- `next_page_url` i `page_limit_reached`: czy pozostał nieprzejrzany link do kolejnej strony;
- `archive_links_not_scanned`: rozpoznane roczne archiwa, których skrypt nie przegląda.

`notice` zwraca pełny tekst `editor-content` w kolejności źródła: nagłówki, akapity, elementy list i tabele (wiersze oraz komórki, z `colspan/rowspan`). `content_text` służy wyszukiwaniu. Białe znaki HTML są normalizowane, encje dekodowane; numery partii, daty i tekst pozostają tekstem, bez zgadywania struktury. Zdjęcia, załączniki oraz tekst poza `editor-content` nie są pobierane ani OCR-owane. Jeśli identyfikacja produktu zależy od zdjęcia/załącznika, skieruj użytkownika do źródłowego komunikatu.

URL wejściowy i przekierowania ograniczono do HTTPS `www.gov.pl/web/gis/<slug>`. Nie pobiera się dowolnych stron, obrazów ani adresów przesłanych w treści komunikatu. Listy i komunikaty mają limit 3 MiB, timeout 20 s, odstęp co najmniej 1 s między żądaniami sieciowymi w jednym procesie, bez automatycznych ponowień. Cache 5 minut jest atomowy i nie jest używany po terminie ważności. Równoległe procesy nie mają wspólnego limitera.

Wyszukiwanie maksymalnie 5 stron może pobrać do około 50 komunikatów; przy pierwszym odczycie potrwa co najmniej kilkadziesiąt sekund. Nie uruchamiaj wielu identycznych wyszukiwań równolegle. `list` jest tańsze, jeśli użytkownik chce tylko najnowsze publikacje.

Treści tekstowe Gov.pl: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) zgodnie ze stopką oraz [prawami autorskimi Gov.pl](https://www.gov.pl/web/gov/prawa-autorskie). Wynik zawiera atrybucję i informację o przekształceniu. Zdjęcia mają osobne warunki; nie są dołączane. Kod skilla pozostaje MIT. Snapshoty testowe i ich pochodzenie opisano w [resources/README.md](../resources/README.md).
