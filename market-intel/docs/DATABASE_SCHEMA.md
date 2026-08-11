# Database Schema

Authoritative DDL: `packages/database/schema.sql` (28 tables). It is written in
the SQLite ∩ PostgreSQL subset so the same file ports with a type map.

## SQLite → PostgreSQL map

| SQLite | PostgreSQL |
|---|---|
| `INTEGER PRIMARY KEY` | `BIGSERIAL PRIMARY KEY` |
| `TEXT` (ISO-8601 timestamp) | `TIMESTAMPTZ` |
| `TEXT` (JSON payload) | `JSONB` |
| `REAL` | `DOUBLE PRECISION` |
| `INTEGER` (0/1 flag) | `BOOLEAN` |
| `INSERT .. ON CONFLICT(x) DO UPDATE` | identical |

## Table groups

**Sources & lineage** — `data_sources`, `ingestion_runs`, `source_records`.
`source_records.payload` is the untouched document; everything else is derivable.

**Entities** — `entities` (one table for all 20 entity types, so a relationship
can join any two), `entity_aliases`, `entity_identifiers` (CIK/ticker/domain,
with `valid_from`/`valid_to` because tickers get reassigned),
`resolution_candidates` (the never-auto-merge review queue).

**Markets** — `securities`, `ohlcv`.

**SEC** — `sec_filings`, `filing_sections`, `filing_facts` (XBRL),
`filing_diffs`.

**Tag graph** — `tags` (self-referencing hierarchy), `tag_aliases`,
`entity_tags` (temporal observations, unique per source document so a document
can never inflate a tag twice).

**Relationships** — `relationships` + `relationship_evidence` (evidence stored
separately: one assertion, many supports).

**Signals & scores** — `signals`, `signal_observations` (unique on
`signal_id, entity_id, subject_id, observed_at, signal_version` — see D-009),
`score_models`, `scores`.

**User layer** — `users`, `watchlists`, `watchlist_items`, `alerts`,
`alert_events` (tables exist; no UI yet).

## Three enforced invariants

1. **Provenance** — normalized/derived rows FK to `source_records`.
2. **Idempotency** — every ingested row has a natural UNIQUE key; collectors
   upsert. Re-running a collector converges.
3. **Temporality** — `observed_at` (when true) and `ingested_at` (when knowable)
   are separate columns. Backtests filter on `ingested_at`.

## Planned tables (spec'd, not created)

`organizations`, `subscriptions`, `api_keys`, `earnings_events`,
`earnings_transcripts`, `transcript_segments`, `insider_transactions`,
`institutional_holdings`, `options_contracts`, `options_activity`,
`news_articles`, `news_mentions`, `web_mentions`, `search_interest`,
`social_mentions`, `saved_searches`, `ai_reports`, `research_sessions`.
