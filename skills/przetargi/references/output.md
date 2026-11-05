# Wynik BZP

`search` zwraca `notices`, `count`, `filters`, `order`, `limit_reached`, `has_more` i `next_cursor`.
`notice` zwraca pojedynczy obiekt `notice`, z dodatkowym `content_text` (treść ogłoszenia po usunięciu HTML, skryptów i stylów).

Każde ogłoszenie zawiera:

- `id`: pełny numer BZP, przyjmowany przez komendę `notice`.
- `object_id`: UUID API, wykorzystywany jako kursor i w linku do ogłoszenia.
- `title`, `notice_type`, `buyer`, `buyer_city`, `buyer_voivodeship`.
- `published_at`, `offers_due_at`: oryginalne znaczniki czasu z API; null oznacza brak terminu.
- `cpv`: kody i opisy z API; poszukiwany kod może być kodem dodatkowym, nie głównym przedmiotem zamówienia.
- `tender_id`, `source_url`: identyfikator postępowania i publiczny link do ogłoszenia.

`filters` zawiera faktyczne parametry zapytania i zakres dat UTC. Kolejność jest zgodna z API. Po osiągnięciu limitu `has_more` jest null: nie wykonujemy dodatkowego zapytania tylko po to, żeby potwierdzić kolejną stronę. Ponów identyczne zapytanie z `--after <next_cursor>` i jawnymi datami; pusta kolejna strona kończy się kodem 2. Krótsza strona oznacza `has_more: false`.

Fraza i CPV są łączone warunkiem AND. Użyj samego `--cpv`, jeśli celem jest kategoria usług bez ograniczania tytułu.

## Przykład z rzeczywistego uruchomienia

Zapis z 2026-11-04T21:22:13+00:00. Skrócony widok; pełny wynik w materiale demo.

```json
{
  "count": 3,
  "limit_reached": true,
  "has_more": null,
  "next_cursor": "08df3010-f521-555b-701a-d00001ab1d20",
  "filters": {
    "NoticeType": "ContractNotice",
    "PublicationDateFrom": "2026-10-06T00:00:00Z",
    "PublicationDateTo": "2026-11-04T23:59:59.9999999Z",
    "CpvCode": "72413000-8"
  },
  "order": "upstream",
  "note": "Ogłoszenia BZP; termin w ogłoszeniu nie potwierdza, że postępowanie nadal przyjmuje oferty. Województwo dotyczy zamawiającego.",
  "source": "Biuletyn Zamówień Publicznych — e-Zamówienia",
  "source_url": "https://ezamowienia.gov.pl/mo-board/api/v1/notice",
  "fetched_at": "2026-11-04T21:22:13.542209+00:00",
  "notices": [
    {
      "id": "2026/BZP 00475839/01",
      "object_id": "08df2467-1cf3-5b7c-647d-de00016e2894",
      "title": "Rozbudowa i modernizacja platformy wirtualnego przewodnictwa i gier terenowych dla partnerów projektu „Kultura w zasięgu 3.0”",
      "notice_type": "ContractNotice",
      "buyer": "Województwo Kujawsko-Pomorskie",
      "buyer_city": "Toruń",
      "buyer_voivodeship": "PL04",
      "published_at": "2026-10-07T11:35:39.2661822Z",
      "offers_due_at": "2026-10-16T08:00:00Z",
      "cpv": "72212220-7 (Usługi opracowywania oprogramowania dla internetu i intranetu),72212500-4 (Usługi opracowywania oprogramowania komunikacyjnego i multimedialnego),72413000-8 (Usługi w zakresie projektowania stron WWW),72254100-1 (Usługi w zakresie testowania systemu),79552000-8 (Usługi przetwarzania tekstu),92111250-9 (Produkcja filmów informacyjnych),32353000-2 (Nagrania dźwiękowe),79530000-8 (Usługi w zakresie tłumaczeń pisemnych),30121420-3 (Nadajniki cyfrowe),30213200-7 (Komputer tablet)",
      "tender_id": "ocds-148610-8db70a34-0fc6-4a4c-b7ec-11276373a348",
      "source_url": "https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/id/08df2467-1cf3-5b7c-647d-de00016e2894"
    }
  ]
}
```
