---
name: normalize-dataset
description: Map a raw payload onto normalized tables.
---

# normalize dataset

Map a raw payload onto normalized tables. Rules: keep every column's provenance, coerce types explicitly, reject rather than guess, and give the row a stable natural key so re-ingestion upserts.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
