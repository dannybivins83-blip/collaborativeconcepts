---
name: create-signal
description: Add a signal.
---

# create signal

Add a signal. Requirements: @signal definition with params, compute() returning raw_value + knowable_at + evidence + source_record_ids, subject_id when per-dimension, and a test on a fixture with a known answer.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
