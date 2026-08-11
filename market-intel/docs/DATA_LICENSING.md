# Data Licensing

**Being able to fetch data is not permission to redistribute it.** Every source
carries a `license_class` in `data_sources`, and every source can be disabled
independently via `enabled = 0` without touching code.

| Class | Meaning | Redistribution of derived analytics |
|---|---|---|
| `PUBLIC` | US government work, no copyright | Yes |
| `OPEN_DATA` | Published under an open licence | Usually yes — check attribution terms |
| `API` | Free/paid API with terms | Depends on the contract |
| `LICENSE_REQUIRED` | Commercial licence needed | No, until signed |
| `REVIEW_REQUIRED` | Not yet assessed | **Do not ship** |

Default for a new source is `REVIEW_REQUIRED`.

## Current classifications

- **SEC EDGAR — PUBLIC.** US government work, not subject to copyright.
  Derived analytics may be redistributed. Access policy (declared UA, rate
  limit) still applies and is enforced in code.
- Everything else — unassessed. Nothing else is ingested.

## Before enabling any new source

1. Read the terms; record the URL and date in this file.
2. Decide separately: (a) may we *store* it, (b) may we *derive* from it,
   (c) may we *show* the derivation to a paying customer.
3. If a vendor forbids redistribution, the raw values stay internal — only
   sufficiently transformed aggregates may surface, and only if terms allow.
4. Set `license_class` and register the source before writing the collector.

## Kill switch

`UPDATE data_sources SET enabled = 0 WHERE id = '<source>';` — pipelines check
this. A licence dispute is contained to one source, not the platform.
