# Supported formats and interpretation

These are recognized schemas, not a promise of nationwide coverage. Resource format labels alone do not establish compatibility. Initial examples were read on 2026-11-07; CSV timestamp variants and XLSX were checked on 2026-11-08.

| Profile | Recognition | Unit identity | Date basis | Verified resource |
|---|---|---|---|---|
| `dated-json` | Object keyed by dates; each date maps unit codes to `Symbol`, `Nazwa`, `PowU`, `Brutto`, `CenaM2` | Exact `Symbol`, checked against the enclosing key | Date from the file's enclosing key | 67625, dataset 4863 |
| `snapshot-csv` | Explicit columns including `nazwa_inwestycji`, `budynek`, `numer_lokalu`, `snapshot_date`, `currency`, gross prices and area | `project::building::property-kind::unit` | Row's `snapshot_date` | 76661, dataset 5948 |
| `disclosure-csv` | Unique Polish column prefixes for locality, street, building, unit, property kind, base total, m² price and price-effective date | `locality::street::building::unit` | Catalog `data_date`; `price_effective_from` preserved separately | 463289, dataset 5948 |
| `disclosure-xlsx`, `disclosure-xlsx-coded` | One-sheet OOXML table with the same verified disclosure column aliases; coded exports additionally expose checked `kod_produktu`, `Budynek`, `Rodzaj` columns | Address/unit identity, or exact publisher product code for recognized coded exports | Catalog `data_date`; separate effective date/time | Dom Development 1296899 and 2900284 |
| `disclosure-xlsx-history` | Repeated unit rows with complete, explicit price-effective dates in the same disclosure table | Same address/unit identity; never just a bare unit number | Publisher-declared effective date/time; not an observed daily snapshot | Murapol 695898, dataset 7126 |
| `spreadsheet-xml` | One SpreadsheetML worksheet; exact columns `Inwestycja`, `Numer`, `Typ`, `Powierzchnia rozliczeniowa`, `Cena ofertowa brutto`, `cena brutto m2` | `investment::number` | Catalog `data_date` | 71532 and 71531, dataset 4927 |

`disclosure-csv` does not infer area by dividing rounded prices. It ignores rows with no residential unit identifier and property type `X` or empty; `sources[].excluded_rows_without_residential_identifier` reports the count. Those rows can describe separate property components; they are not added to the unit price. Other malformed identities fail explicitly. CSVs must be UTF-8 (optional BOM), comma- or semicolon-delimited. Known publisher headers may be truncated; only the documented, unique prefix matches are accepted. Verified aliases include `Cena m2` and the shortened base-price-effective-date heading used in Murapol exports. Explicit unknown markers (`X`, `-`, `NULL`, `brak`, empty) stay unknown. ISO dates, ISO local timestamps and the verified `DD-MM-YYYY HH:MM[:SS]` form are distinguished; timestamps are preserved without assuming a timezone.

The SpreadsheetML reader preserves sparse cell indices, rejects ambiguous/multiple sheets, and rejects DTD/entity declarations. General real-estate XML, legacy Excel XLS and XML wrapper documents are unsupported. XLSX is handled by the separate bounded OOXML reader described below.

A real freshness pitfall: resource 76661 had a catalog date in November 2026 but rows with `snapshot_date` in September 2025. The explicit file date remains authoritative for that profile. XML and disclosure CSV lack an independent snapshot date in the supported schema: catalog dates are therefore labeled as such. An effective-from date alone does not establish when a snapshot was captured or that the quoted price still applies.

## History semantics

- Identity is scoped to the same dataset, publisher and parsing profile. Unit numbers are not globally unique. Cross-profile matching is unsupported, including two different export schemas from one developer.
- `price_points` contains consecutive groups of identical reported values, including area, status and effective date where present. It is a compact record of observations, not continuous legal validity. Gaps are also reported separately.
- Missing price, zero price and unknown area are not imputed. A change from an unknown price has no computed percentage. A changed known area or kind suppresses all comparison summaries.
- `first_to_last_change` compares the selected unit's first and last **priced** endpoints only when both endpoint prices are known and at least two distinct snapshot dates or two explicit, ordered effective instants are present. One snapshot is insufficient to claim an unchanged price. The minimum/maximum reflects the selected files, never the whole market or an uninterrupted history. No claim is made that a low observed price was available for purchase.
- `area_consistent` is false if observed areas differ, true if every observation has the same known area, and null if area checks are incomplete. Even a consistent area does not prove legal identity or identical contract terms.
- A unit absent in the latest selected snapshot remains historical. Its absence does not establish sale, reservation, withdrawal or a price of zero. `absent_on_snapshot_dates` counts source snapshot dates without the unit, including dates outside its first/last appearance.
- Prices are quoted gross asking prices from publisher fields. `total_includes_additional_costs` remains null: there is no general, verified rule for including parking, storage or other charges. Base price and all-in price are not interchangeable.

No local snapshot database is maintained. Run the CLI again to retrieve current source files, keeping the returned dates and SHA-256 when recording evidence. Provider corrections can replace historical content; the skill cannot reconstruct a version no longer exposed by the source.

## Bounded XLSX reading and declared histories

The client reads exactly one worksheet through workbook relationships, not by assuming sheet ID equals filename. It preserves shared and inline strings and sparse cell positions, including leading zeroes in identifiers. Only needed ZIP members are read in memory. Duplicate archive entries, external sheet relationships, DTD/entities, formula/error/boolean cells, duplicate cell addresses and excessive sizes/ranges fail explicitly. Formula caches are not evaluated or trusted. Native numeric Excel date serials are unsupported because interpreting them requires a verified date-system/style contract.

Recognized Dom Development exports contain `kod_produktu`, `Budynek` and `Rodzaj`. The product code must equal the declared residential unit identifier. Its identity remains stable when address fields are missing or filled later. `location_incomplete` exposes missing location fields; the code is not a validated postal address. Components without a residential unit identifier are counted and excluded, never silently added to an apartment price.

When a disclosure XLSX repeats units and every retained row has an explicit effective date, it is a publisher-declared price-history table. The profile suffix `-history`, `sources[].declared_price_history` and `timeline_type: published_price_effective_dates` identify it. Different explicit local times on one day remain separate events. Conflicts at the same effective instant fail; mixing an undated time with several prices on one day also fails rather than guessing event order. `units` selects the latest declared row per unit in that file. Snapshot metadata remains the catalog date and is separate from the effective-price date range.

In that mode, time between declared price changes is **not** missing daily sampling: `calendar_gaps` and `absent_on_snapshot_dates` are null. Presence checks refer to the latest selected source file, not whether another unit changed price later. Neither mode establishes present-day availability. A source may retain only historical declarations, return a header-only current export, or revise earlier data.
