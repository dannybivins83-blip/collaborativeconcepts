# Architecture

## The model

```
DATA SOURCE → RAW RECORD → NORMALIZATION → ENTITY RESOLUTION
   → TAGGING → RELATIONSHIPS → TIME SERIES → SIGNALS → SCORES → INTELLIGENCE
```

Each arrow is a boundary with its own failure mode and its own tests. Nothing
downstream may invent a fact that is not traceable to a `source_records` row.

## Layers

**Collectors** (`collectors/`) implement one contract — `fetch / validate /
normalize / persist_raw / persist_normalized / health_check` — and are isolated:
a dead provider records a failed `ingestion_run` and raises `CollectorError`; it
never takes down another source. Transport handles rate limiting, retry with
backoff, and fail-fast on 4xx. `FixtureTransport` swaps only the wire bytes, so
offline tests exercise production code.

**Storage** (`packages/database`) is three logical zones over one schema:
- RAW — `source_records`, append/upsert only, never destructively rewritten.
- NORMALIZED — `entities`, `sec_filings`, `filing_facts`, `filing_sections`.
- DERIVED — `entity_tags`, `relationships`, `signal_observations`, `scores`.

Every normalized and derived row carries `source_record_id`. The e2e test
asserts zero orphans.

**Entity resolution** (`packages/entity_resolution`) is the join key for
everything. Identifiers (CIK/ticker/domain) are authoritative; names are only
evidence. Ambiguity produces candidates for review, never a silent merge.

**Tag graph** (`packages/tag_engine`) stores observations, not labels:
`(entity, tag, source_record, observed_at, frequency, relevance, evidence)`.
Strength over time is therefore a query, which is what makes "AI mentions
accelerating" answerable.

**Signals** (`packages/signal_engine`) are registered definitions plus a compute
function. Cross-sectional z-scores/percentiles are computed within a run so
companies are comparable. Every observation stores evidence and the date the
value became *knowable*.

**Scoring** (`packages/scoring_engine`) blends normalized signals by category
with versioned weights and reports `coverage`.

**API** (`apps/api`) — handlers are framework-agnostic `(db, params) ->
(status, payload)`; the stdlib server and the FastAPI adapter both delegate to
them, so they cannot drift.

## Request path (today)

```
browser → apps/web/index.html → GET /api/v1/stocks/NVDA/...
        → apps/api/server.py → handlers.dispatch → SQLite → JSON
```

## Scaling path (not yet built)

Precompute derived aggregates in the worker rather than at request time;
materialized views for cross-sectional rankings; Redis for hot reads;
partition `signal_observations` and `entity_tags` by time; OpenSearch behind the
existing search abstraction. The API contract does not change for any of these.
