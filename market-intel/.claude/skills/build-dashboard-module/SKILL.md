---
name: build-dashboard-module
description: Add a UI panel.
---

# build dashboard module

Add a UI panel. Requirements: fetch from an existing API route, show as-of dates, degrade to an explicit empty state, and surface the DEMO banner when data.contains_demo_data is true.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
