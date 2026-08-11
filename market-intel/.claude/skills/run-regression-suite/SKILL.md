---
name: run-regression-suite
description: make test — 69 offline tests.
---

# run regression suite

make test — 69 offline tests. On failure, fix the code not the assertion; if the assertion was wrong, say so explicitly in the commit. Every bug fix adds a regression test.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
