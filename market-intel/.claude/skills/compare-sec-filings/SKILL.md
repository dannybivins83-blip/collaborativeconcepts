---
name: compare-sec-filings
description: Diff a filing against its prior comparable (same registrant, same form).
---

# compare sec filings

Diff a filing against its prior comparable (same registrant, same form). Report added/removed/modified per section with excerpts. Never compare across form types.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
