# Rejestr Aptek source and fields

- [CeZ medical registers](https://cez.gov.pl/pl/rejestry-medyczne) describes the register maintained by the provincial pharmaceutical inspectorates.
- [Public register UI](https://rejestry.ezdrowie.gov.pl/ra/search/public).
- [Public CSV export](https://rejestry.ezdrowie.gov.pl/api/ra/filegenerator/getcsv). Verified directly on 2026-11-13: HTTP 200, UTF-8 BOM, `|` separator, 17,642,954 bytes, 24,024 unique records. The response filename declared `Rejestr_Aptek_stan_na_dzien_2026-11-13.csv`; these counts are observations, not required constants.

The provider returned `Cache-Control: no-cache, no-store, max-age=0, must-revalidate`. There is no automatic disk cache. Search is local after one GET; it does not rely on the UI's internal search interface. No published request quota or SLA was established.

## Mapping

| CSV fields | Result |
|---|---|
| `identyfikator_apteki` | `id`, unchanged numeric string |
| `nazwa_apteki` | `name`, nullable |
| `stan_apteki`, `rodzaj_apteki` | `registry_status`, `pharmacy_type`, raw source labels |
| `wojewodztwo`, `powiat`, `gmina`, `miejscowosc`, street/building/unit/postcode fields | `address`, retaining Polish field names |
| `telefon`, `email`, `adres_www` | `contact`, source text only |
| permit number, issuing authority, issue/revocation/expiry/valid-until dates | `authorization`, source text only |
| `godziny_otwarcia_*` | `opening_hours_reported`, suffix keys unchanged |

The export also contains proprietor and manager data. These fields are intentionally omitted: they are unnecessary for finding a facility. Do not replace a pharmacy's contact/address with its proprietor's details.

Observed statuses: `AKTYWNA`, `NIEAKTYWNA`, `NIEAKTYWNA - ZAWIESZENIE DZIAŁALNOŚCI`, `CZASOWO NIECZYNNA`, `OCZEKUJĄCA`. Unknown future labels remain visible through `--status all`/`get` and are not silently classified as active. `--kind public` admits only the two explicitly supported community types; all other types require `--kind all` or an exact ID lookup.

All source strings are preserved; missing values become null. No phone, website, opening-hours interval or legal status is independently verified. `open_now_assessed` and `medicine_stock_assessed` are false. An inactive record can retain old hours and contact details. Source presence alone does not establish current operations, medicinal stock, dispensing authorization for a particular product or a night duty.
