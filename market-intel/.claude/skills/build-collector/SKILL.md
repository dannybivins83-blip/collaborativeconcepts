---
name: build-collector
description: Implement the Collector contract.
---

# build collector

Implement the Collector contract. Steps: subclass Collector → fetch() yields {source_record_id, kind, url, payload, observed_at} → validate() returns problems (never raises) → normalize() → persist_normalized() via repositories → record a fixture → write tests for ok/reject/failure/re-run-idempotency.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
