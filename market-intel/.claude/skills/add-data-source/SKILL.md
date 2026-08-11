---
name: add-data-source
description: Register a source in data_sources with a license_class BEFORE any collector exists.
---

# add data source

Register a source in data_sources with a license_class BEFORE any collector exists. Steps: classify licence (docs/DATA_LICENSING.md) → add a DATA_CATALOG row → register(db) with rate limits and auth → confirm the kill switch works.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
