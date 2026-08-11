---
name: resolve-entity
description: Resolve a mention to an entity.
---

# resolve entity

Resolve a mention to an entity. Order: identifiers → exact alias → fuzzy above threshold with a clear margin. Ambiguous or weak results go to resolution_candidates. Never merge on a name alone.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
