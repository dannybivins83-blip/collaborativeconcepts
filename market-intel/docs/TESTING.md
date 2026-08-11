# Testing

`make test` → `python3 tests/test_all.py` — **69 tests, no network, no
dependencies, no paid APIs.**

## Principles

1. **Mock the wire, not the code.** `FixtureTransport` replaces only the bytes
   returned by HTTP. Parsing, validation, resolution and persistence run for
   real, so an offline test failing means production would fail.
2. **Every bug gets a regression test.** Two are already in the suite:
   - `test_validate_tolerates_scalar_metadata_keys` — a payload with scalar
     metadata beside row objects crashed validation.
   - `test_per_tag_signals_are_stored_separately` — nine per-tag observations
     silently collapsed into one on a too-narrow unique key.
3. **Test the invariants, not just the functions.** The e2e test asserts zero
   orphaned derived rows and that re-running the pipeline does not duplicate.
4. **Test the guards.** Naive datetimes rejected; substring tag matches
   rejected; annual periods excluded from quarterly series; ambiguous entities
   never merged; collector failure isolated to its own run record.

## Coverage by area

primitives/time/provenance · database upsert idempotency · transport
(fixtures, retry, contact-UA, rate limit) · three SEC collectors · document
extraction · entity resolution (identifier/alias/fuzzy/ambiguous) · tag engine
(boundaries, dedup, timeseries) · signal maths + compute · scoring coverage ·
filing diff · 17 API routes · full pipeline e2e.

## Not covered

FastAPI adapter (not installed here), docker-compose, live network paths,
frontend JS, load/performance.
