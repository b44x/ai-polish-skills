# Supported formats and interpretation

These are recognized schemas, not a promise of nationwide coverage. Resource format labels alone do not establish compatibility. Examples below were read on 2026-11-07.

| Profile | Recognition | Unit identity | Date basis | Verified resource |
|---|---|---|---|---|
| `dated-json` | Object keyed by dates; each date maps unit codes to `Symbol`, `Nazwa`, `PowU`, `Brutto`, `CenaM2` | Exact `Symbol`, checked against the enclosing key | Date from the file's enclosing key | 67625, dataset 4863 |
| `snapshot-csv` | Explicit columns including `nazwa_inwestycji`, `budynek`, `numer_lokalu`, `snapshot_date`, `currency`, gross prices and area | `project::building::property-kind::unit` | Row's `snapshot_date` | 76661, dataset 5948 |
| `disclosure-csv` | Unique Polish column prefixes for locality, street, building, unit, property kind, base total, m² price and price-effective date | `locality::street::building::unit` | Catalog `data_date`; `price_effective_from` preserved separately | 463289, dataset 5948 |
| `spreadsheet-xml` | One SpreadsheetML worksheet; exact columns `Inwestycja`, `Numer`, `Typ`, `Powierzchnia rozliczeniowa`, `Cena ofertowa brutto`, `cena brutto m2` | `investment::number` | Catalog `data_date` | 71532 and 71531, dataset 4927 |

`disclosure-csv` does not infer area by dividing rounded prices. It ignores rows with no residential unit identifier and property type `X` or empty; `sources[].excluded_rows_without_residential_identifier` reports the count. Those rows can describe separate property components; they are not added to the unit price. Other malformed identities fail explicitly. CSVs must be UTF-8 (optional BOM), comma- or semicolon-delimited. Known publisher headers may be truncated; only the documented, unique prefix matches are accepted.

The SpreadsheetML reader preserves sparse cell indices, rejects ambiguous/multiple sheets, and rejects DTD/entity declarations. General real-estate XML, Excel XLS/XLSX and XML wrapper documents are unsupported.

A real freshness pitfall: resource 76661 had a catalog date in November 2026 but rows with `snapshot_date` in September 2025. The explicit file date remains authoritative for that profile. XML and disclosure CSV lack an independent snapshot date in the supported schema: catalog dates are therefore labeled as such. An effective-from date alone does not establish when a snapshot was captured or that the quoted price still applies.

## History semantics

- Identity is scoped to the same dataset, publisher and parsing profile. Unit numbers are not globally unique. Cross-profile matching is unsupported, including two different export schemas from one developer.
- `price_points` contains consecutive groups of identical reported values, including area, status and effective date where present. It is a compact record of observations, not continuous legal validity. Gaps are also reported separately.
- Missing price, zero price and unknown area are not imputed. A change from an unknown price has no computed percentage. A changed known area or kind suppresses all comparison summaries.
- `first_to_last_change` compares the selected unit's first and last **priced** endpoints only when both endpoint prices are known and at least two distinct dates are present. One snapshot is insufficient to claim an unchanged price. The minimum/maximum reflects the selected files, never the whole market or an uninterrupted history. No claim is made that a low observed price was available for purchase.
- `area_consistent` is false if observed areas differ, true if every observation has the same known area, and null if area checks are incomplete. Even a consistent area does not prove legal identity or identical contract terms.
- A unit absent in the latest selected snapshot remains historical. Its absence does not establish sale, reservation, withdrawal or a price of zero. `absent_on_snapshot_dates` counts source snapshot dates without the unit, including dates outside its first/last appearance.
- Prices are quoted gross asking prices from publisher fields. `total_includes_additional_costs` remains null: there is no general, verified rule for including parking, storage or other charges. Base price and all-in price are not interchangeable.

No local snapshot database is maintained. Run the CLI again to retrieve current source files, keeping the returned dates and SHA-256 when recording evidence. Provider corrections can replace historical content; the skill cannot reconstruct a version no longer exposed by the source.
