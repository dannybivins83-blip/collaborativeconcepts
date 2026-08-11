---
name: analyze-stock
description: Produce a stock brief from STORED evidence only: score + coverage, active signals with z-scores, tag trajectory, filing changes, recent filings.
---

# analyze stock

Produce a stock brief from STORED evidence only: score + coverage, active signals with z-scores, tag trajectory, filing changes, recent filings. Every claim cites a source record. State what is missing rather than filling gaps.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
