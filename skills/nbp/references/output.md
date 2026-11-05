# Narodowy Bank Polski (NBP) — Field Reference and Legal Tax Rules

## API Overview

Narodowy Bank Polski publishes official average exchange rates and gold prices at `https://api.nbp.pl/`.
New exchange rate tables are published every business day between 11:45 and 12:15 CET/CEST.

---

## Legal Tax Rules for Currency Invoices (Art. 31a VAT / Art. 11a PIT)

When issuing or processing a foreign currency invoice in Poland:

1. **Rule:** Amounts expressed in foreign currencies are converted to Polish zloty (PLN) using the **average exchange rate announced by the National Bank of Poland on the last business day preceding the date of invoice issuance or taxable event**.
   - *Legal basis:* Art. 31a ust. 1 Ustawy o podatku od towarów i usług (VAT), Art. 11a ust. 1 Ustawy o podatku dochodowym od osób fizycznych (PIT), Art. 12 ust. 2 Ustawy o CIT.
2. **Weekends and Holidays:** If an invoice is issued on a Monday, the exchange rate from the preceding Friday is used. If Friday was a public holiday, the rate from Thursday applies.
3. **Audit Trail:** Tax authorities require documenting both the exchange rate, the date of publication, and the exact official table number (e.g. `187/A/NBP/2026`).

---

## Output Fields

### Currency Rate (`rate <currency>`)

| Field | Type | Description |
|---|---|---|
| `currency` | string | 3-letter ISO 4217 currency code (e.g. `EUR`, `USD`, `GBP`, `CHF`) |
| `currencyName` | string | Polish name of currency (e.g. `euro`, `dolar amerykański`) |
| `table` | string | Table type: `A` (major currencies) or `B` (exotic currencies) |
| `tableNumber` | string | Official NBP publication number, e.g. `188/A/NBP/2026` |
| `effectiveDate` | string | Date when rate took effect (`YYYY-MM-DD`) |
| `mid` | float | Official average exchange rate to PLN |

### Tax Invoice Calculation (`invoice <amount> <currency> <date>`)

| Field | Type | Description |
|---|---|---|
| `amount` | float | Invoice amount in foreign currency |
| `currency` | string | Currency code |
| `currencyName` | string | Polish name of currency |
| `invoiceDate` | string | Date of invoice issuance / taxable event |
| `taxEffectiveDate` | string | Date of the preceding business day's NBP table |
| `tableNumber` | string | Official table number of the preceding business day |
| `exchangeRate` | float | Exchange rate applied for tax calculation |
| `amountPln` | float | Converted amount in PLN (rounded to 2 decimal places) |
| `amountPlnExact` | float | Exact converted amount without rounding |
| `legalBasis` | string | Statutory tax reference |

### Currency Conversion (`convert <amount> <from> <to>`)

| Field | Type | Description |
|---|---|---|
| `amount` | float | Source amount |
| `fromCurrency` | string | Source currency code |
| `toCurrency` | string | Target currency code |
| `convertedAmount` | float | Converted amount (rounded to 2 decimals) |
| `convertedAmountExact` | float | Exact converted amount (4 decimals) |
| `rateFromPln` | float | Source currency rate in PLN |
| `rateToPln` | float | Target currency rate in PLN |
| `effectiveRate` | float | Direct cross-rate (`from / to`) |
| `date` | string | Date of rates used |

### Gold Price (`gold`)

| Field | Type | Description |
|---|---|---|
| `date` | string | Date of quote (`YYYY-MM-DD`) |
| `pricePerGramPln` | float | Official NBP price in PLN per 1 gram of gold (purity 1000) |
| `pricePerTroyOuncePln` | float | Calculated price in PLN per 1 troy ounce (31.1035 g) |
| `priceFormatted` | string | Formatted price per gram, e.g. `530.05 zł / g` |
| `priceOunceFormatted` | string | Formatted price per ounce, e.g. `16486.40 zł / oz` |
| `purity` | string | Purity standard (1000) |
