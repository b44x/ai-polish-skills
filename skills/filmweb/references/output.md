# Filmweb CLI — output reference

Missing values are `null`; lists are `[]` when empty.

## `search`

List of:

| Field | Type | Notes |
|---|---|---|
| `id` | int | Filmweb ID |
| `type` | string | `film`, `serial`, `game`, … |
| `title` | string | matched title (usually Polish) |
| `mainCast` | string[] | up to a few main actors |

## `film`

| Field | Type | Notes |
|---|---|---|
| `id` | int | Filmweb ID |
| `title` | string | Polish title |
| `originalTitle` | string\|null | |
| `year` | int\|null | |
| `type` / `subType` | string | e.g. `film` / `film_cinema` |
| `url` | string | filmweb.pl page, built from title, year and ID |
| `posterUrl` | string\|null | |
| `rating` | float\|null | average user rating 1–10 |
| `votesCount` | int\|null | |
| `wantToSeeCount` | int\|null | users who want to see it |
| `votesDistribution` | object | `{"1": count, …, "10": count}` |
| `criticsRating` | float\|null | average critics rating 1–10 |
| `criticsCount` | int\|null | |
| `genres` | string[] | Polish names |
| `countries` | string[] | ISO country codes |
| `duration` | int\|null | minutes |
| `directors` | `{id, name}[]` | |
| `mainCast` | `{id, name}[]` | two leading actors; use `cast` for more |
| `plot` | string\|null | short synopsis; use `description` for the full one |
| `siteRecommends` | bool | Filmweb editorial recommendation |

## `description`

`{id, description}` — Filmweb markup such as `[person=87]…[/person]` is stripped.

## `cast`

List of `{personId, name, profession, roleRating, roleVotes}`, ordered by how users rate the role.
Character names are not available from this endpoint.

## `dates`

Object with any of `worldPremiere`, `worldRelease`, `polandRelease`, `polandReissue`,
each `{date: "YYYY-MM-DD", country: "PL", cinemas: bool}`.

## `vod`

List of `{provider, link, availableFrom, availableUntil, offers}`; expired offers are skipped.
`offers` is a list of `{type: "subscription"|"free"|"rent"|"buy", pricePLN: float|null}`.
An offer without payment details is reported as `subscription` when the provider sells subscriptions,
otherwise `type` is `null`. Several prices of the same type usually mean different video quality (SD/HD).

## `person`

`{id, name, realName, birthDate, birthplace, height, mainProfession, photoUrl, knownForIds, url}`.
`knownForIds` are Filmweb title IDs — resolve them with `film` only if needed.
