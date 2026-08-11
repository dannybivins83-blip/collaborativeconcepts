---
name: analyze-earnings
description: Build the topic-frequency time series per company per tag from transcripts, then compute acceleration.
---

# analyze earnings

Build the topic-frequency time series per company per tag from transcripts, then compute acceleration. (Blocked: no transcript collector yet — see BUILD_STATUS.)

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
