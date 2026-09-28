# InPost — Field Reference and Statuses

## API Overview

InPost is Poland's leading parcel delivery service, operating the largest automated parcel locker (*Paczkomat*) network.

Official endpoints from InPost ShipX API: `https://api-shipx-pl.easypack24.net/v1`

---

## Output Fields

### Point Details (`point <name>`)

| Field | Type | Description |
|---|---|---|
| `name` | string | Point code, e.g. `WAW322M`, `KRA01A` |
| `type` | string | Raw type identifier: `parcel_locker`, `pop` |
| `typeDescription` | string | Polish human-readable name: `Paczkomat` or `Punkt Odbioru (POP)` |
| `status` | string | `Operating` for active machines |
| `address` | object | Address breakdown: `line1`, `line2`, `city`, `postCode`, `street`, `buildingNumber` |
| `locationDescription` | string | Landmark or visual location tip, e.g. "Przy salonie Rossmann" |
| `location` | object | Geographical coordinates `{latitude, longitude}` |
| `distanceMeters` | float \| null | Distance from origin when searched via `near` |
| `distanceFormatted` | string \| null | Formatted distance, e.g. `"120 m"` or `"2.4 km"` |
| `openingHours` | string | Opening hours, e.g. `"24/7"` or `"PN-PT 08-18 SB 10-14"` |
| `is24_7` | boolean | `true` if locker is accessible 24/7 |
| `easyAccessZone` | boolean | `true` if locker supports Strefa Łatwego Dostępu (lower compartments for people with disabilities or shorter height) |
| `paymentAvailable` | boolean | `true` if payment for Cash on Delivery (COD) is supported |
| `paymentDescription` | string | Description of supported payment methods (app, PayByLink, card) |
| `imageUrl` | string \| null | Photo of the physical locker location |
| `googleMapsUrl` | string \| null | Direct clickable Google Maps navigation URL |

### Parcel Tracking (`track <number>`)

| Field | Type | Description |
|---|---|---|
| `trackingNumber` | string | 24-digit InPost shipment number |
| `service` | string | Shipment service type (e.g. `inpost_locker_standard`, `inpost_courier_standard`) |
| `status` | string | Current status machine key (e.g. `ready_to_pickup`, `delivered`) |
| `statusTitle` | string | Official human-readable Polish status title |
| `targetMachine` | string \| null | Target destination Paczkomat machine code |
| `createdAt` | string | ISO timestamp when shipment was registered |
| `updatedAt` | string | ISO timestamp of last update |
| `expectedFlow` | array | Expected progression of shipment statuses |
| `events` | array | Historical event timeline: `[{datetime, status, title, agency}]` |
| `trackingUrl` | string | Official InPost public web tracking URL |

---

## Common Parcel Statuses

| Status Key | Polish Title | Meaning |
|---|---|---|
| `created` | Przesyłka utworzona | Label created, not yet shipped |
| `confirmed` | Przygotowana przez Nadawcę | Sender preparing parcel for dispatch |
| `dispatched_by_sender` | Nadana w Paczkomacie / POP | Placed in Paczkomat by sender, awaiting courier pickup |
| `taken_by_courier` | Odebrana przez Kuriera | Collected by courier, in transit to local sorting branch |
| `adopted_at_source_branch` | Przyjęta w Oddziale Nadawczym | Processed at sender branch |
| `sent_from_source_branch` | Wysłana z Oddziału Nadawczego | Dispatched from sender branch towards central sorting |
| `adopted_at_sorting_center` | Przyjęta w Sortowni | Reached central hub sorting facility |
| `sent_from_sorting_center` | Wysłana z Sortowni | En route to destination city branch |
| `adopted_at_target_branch` | Przyjęta w Oddziale Doręczenia | Arrived at destination city branch |
| `out_for_delivery` | Wydana do doręczenia | Courier en route to fill the Paczkomat locker |
| `ready_to_pickup` | Gotowa do odbioru | Parcel placed in locker; ready for recipient pickup |
| `delivered` | Doręczona / Odebrana | Recipient opened compartment and took parcel |
| `returned_to_sender` | Zwrócona do Nadawcy | Return shipment initiated or uncollected |
| `expired` | Upłynął termin odbioru | 48-hour pickup window elapsed |
