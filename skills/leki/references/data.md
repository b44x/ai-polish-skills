# RPL source and field contract

## Verified sources

- [CeZ description of medical registers](https://cez.gov.pl/pl/rejestry-medyczne) identifies RPL and distinguishes it from the GIF decisions register.
- [Official RPL search](https://rejestry.ezdrowie.gov.pl/rpl/search/public).
- [Public XML export, version 6.0.0](https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/public-pl-report/6.0.0/overall.xml). This is an official bulk-download endpoint, not a documented general-purpose search REST API. The skill uses no third-party wrapper or internal search endpoint.

The complete export read on 2026-11-08 declared `stanNaDzien="2026-11-08"`: 22,917 products (20,269 human and 2,648 veterinary) and 88,457 packages. These are verification observations, not hardcoded expected counts or a coverage guarantee. Some entries lack ordinary leaflets, some use parallel-import document fields, some packages are marked deleted, and some authorization dates have elapsed. Eight nonempty source GTINs failed checksum validation in that snapshot and remain explicitly invalid.

## XML mapping

Accepted namespace: `http://rejestry.ezdrowie.gov.pl/rpl/eksport-danych-v6.0.0`; root `produktyLecznicze`, dated by `stanNaDzien`. Records are `produktLeczniczy`. Unknown namespaces and incomplete exports fail without replacing the current index.

| XML field / section | JSON meaning |
|---|---|
| `id` | Exact export product identifier, kept as a string |
| `nazwaProduktu`, `rodzajPreparatu` | `name`, `kind` (`ludzki` / `weterynaryjny`) |
| `nazwaPowszechnieStosowana`, `moc`, `nazwaPostaciFarmaceutycznej` | Common name, strength and pharmaceutical form; no normalization of doses |
| `podmiotOdpowiedzialny`, `numerPozwolenia`, `waznoscPozwolenia`, `typProcedury` | Authorization holder, number, raw validity text/date and procedure |
| `substancjeCzynne/substancjaCzynna` | Substance name, source amount/unit, preparation amount/unit and other description; empty fields become null |
| `kodyATC/kodATC`, `drogiPodania/drogaPodania` | Source ATC codes and route names; not interpreted as indications or directions |
| `opakowania/opakowanie` | Package ID, main GTIN, supply category, deletion flag, EU number and parallel importer |
| `jednostkiOpakowania/jednostkaOpakowania` | Source packaging attributes retained under their Polish keys; no multiplication or dose calculation |

`skasowane="TAK"` maps to `deleted: true`, `NIE` to false, missing/empty to null. This is a registry package flag, not a batch recall decision. `package_counts` separates these three groups. `packages` includes only false by default; `barcode` preserves all three states. A barcode can match more than one record; the client returns all matching records across pages instead of choosing one.

Amounts, strengths and IDs are strings. They may contain decimals, ratios, units, mixtures or descriptive text. Missing amounts are not zero. Substance lookup searches an individual declared `nazwaSubstancji`; it does not search pharmacological classes, compute equivalent doses or certify that two products are substitutes. Search normalization folds case and diacritics, including Polish ł, and collapses whitespace. Substring matching is literal, not SQL wildcards or a typo-correction service.

## Document links

The client copies six distinct source attributes, using the same keys in `documents`:

- `ulotka`: patient leaflet.
- `charakterystyka`: product characteristics (SmPC / ChPL).
- `etykietoUlotka`: combined labelling and leaflet.
- `ulotkaImportRownolegly`: parallel-import leaflet.
- `etykietoUlotkaImportRownolegly`: parallel-import combined labelling and leaflet.
- `oznaczenieOpakowanImportRownolegly`: parallel-import package marking.

Only HTTPS links on `rejestry.ezdrowie.gov.pl` under `/api/rpl/medicinal-products/` are accepted. No fallback link is invented. The export ID and document endpoint ID are different identifiers: for example, the verified export product `100006494` supplied a leaflet URL containing `/649/leaflet`. A link is not evidence that its PDF was read or that it is presently downloadable.

## Local index and limits

The SQLite file `registry-v1.sqlite3` contains product records, declared substance names, package records and snapshot metadata. Queries use parameters and deterministic ordering; page results refer to the index used for that invocation. A refresh can change the dataset between page calls, so preserve the snapshot SHA-256 when combining pages. Human records are the default; exact-ID product/package lookups can address either kind and expose it explicitly.

`retrieved_at` is the successful download time. `source_as_of` is the export's declared date. `cache_age_seconds` controls the 24-hour automatic-refresh policy; `source_age_days` describes the source's date independently. No assumption is made that a fresh download contains today's registry. Explicit offline reads can use any age; display the source date and `cache_expired` rather than presenting them as current. Failed refreshes never produce a successful stale response automatically.

Refresh uses temporary files in the cache directory and an exclusive creation lock. The previous database is retained if parsing, download, local disk operations or source-date checks fail. No XML, PDF, query history or credentials are retained after a successful refresh. A forcibly killed process can leave a temporary directory and lock for manual cleanup after verifying that no refresh is active.

Bounds: 128 MiB XML, 100,000 products, 1,000,000 packages, 2 MiB serialized XML per product, 2,000 packages and 200 substances per product, 32 XML nesting levels. DTD/entity declarations, non-UTF-8 bytes, duplicate product/package identities and unknown human/veterinary classifications are rejected. File download has a 30-second socket timeout and checks a 120-second elapsed budget between reads; a currently blocked read is still subject to its socket timeout. Neither rate limits nor an SLA were published in the verified source material; avoid repeated refreshes and honor HTTP 429.

These checks establish a parsed snapshot, not completeness of the underlying register, medicine authenticity, currently valid authorization, pharmacy stock, reimbursement, GIF decisions or clinical suitability. Such claims require their own appropriate sources.
