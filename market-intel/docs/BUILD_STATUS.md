# Build Status

Honest per-subsystem state. "Complete" means *code exists, runs, and is covered
by tests that actually execute it* — not "a file exists with that name".

Last updated: 2026-08-07 · 69 tests passing (`make test`)

## ✅ COMPLETED (built, runs, tested)

| Subsystem | Evidence |
|---|---|
| Repo + monorepo structure | `market-intel/` tree, stdlib-only core |
| Database schema v1 (28 tables) | `packages/database/schema.sql`, migrations idempotent |
| Provenance model | every derived row FKs `source_records`; e2e test asserts zero orphans |
| Idempotent ingestion | `db.upsert` natural keys; re-run test asserts no duplication |
| Collector contract | `collectors/common/base.py` — fetch/validate/normalize/persist/health |
| HTTP transport | rate limiting, retry/backoff, 4xx fail-fast, contact-UA enforcement |
| Fixture transport | identical code path offline; proves the pipeline with no network |
| **SEC ticker map** | entities + aliases + identifiers + securities |
| **SEC submissions** | column-oriented filing arrays → `sec_filings`, former-name aliases |
| **SEC companyfacts** | XBRL → `filing_facts` with period/unit/form typing |
| **SEC documents** | HTML → text → Item sections → `filing_sections` |
| Entity resolution | identifier > alias > fuzzy; ambiguity queued, never auto-merged |
| Tag engine + taxonomy | 34 tags, word-boundary matching, temporal observations, timeseries |
| Filing diff | sentence-level added/removed/modified vs prior comparable filing |
| Signal framework | registry, cross-sectional z/percentile, evidence, 4 signals |
| Composite scoring | versioned weights, `coverage` reported, missing ≠ zero |
| REST API | 17 routes, framework-agnostic handlers, 404/400 handling |
| Dev server | stdlib `http.server`, serves API + static page |
| Stock page | signals, score breakdown, revenue chart, tag graph + sparklines, filing diffs |
| Test suite | 69 offline tests incl. 2 regression tests for bugs found during the build |

## 🟡 IN PROGRESS / PARTIAL

| Item | Gap |
|---|---|
| FastAPI app (`apps/api/fastapi_app.py`) | **Written but never executed** — fastapi/pydantic/uvicorn are not installed in the build environment and there is no network to install them. Syntax-checked only. Verify before trusting. |
| `docker-compose.yml` | Written; **not run** (no image pulls available here) |
| Postgres support | Schema is Postgres-compatible by construction; the driver path in `db.py` raises `NotImplementedError` on purpose rather than pretending |
| Relationship graph | Tables, repository writes and API route exist; **no collector populates relationships yet** — the stock page section will be empty |
| Screener | Filters by tag/signal/score only; no fundamentals/valuation filters |

## ❌ NOT STARTED (designed only)

Market prices/OHLCV · earnings transcripts · insider Form 4 · 13F institutional ·
options activity · news ingestion · Google Trends/alt data · AI research engine ·
natural-language query · alerts + delivery · watchlists UI · users/auth/billing ·
Next.js frontend · Redis/caching · job queue/worker · OpenSearch · observability
stack · backtesting harness

## 🚧 BLOCKED (needs a human decision or credential)

| Blocker | Needs |
|---|---|
| Live SEC ingest from this environment | Outbound HTTPS (sandbox proxy blocks it). Code is ready; run `--live` on a networked host. |
| Any paid/licensed market data | A provider decision + credentials (§7 of the spec). Nothing has been chosen. |
| Repo placement | Currently a subdirectory of `collaborativeconcepts`. See DECISIONS.md D-001 — extract to its own repo before it grows. |

## NEXT (recommended order)

1. **Verify FastAPI + docker-compose on a networked machine** — the only two
   artifacts here that have never executed.
2. **Prices/OHLCV collector** — the stock page has no price yet; pick a lawful
   source (needs the provider decision).
3. **Relationship extraction** — mine `filing_sections` for customer/supplier/
   competitor language so the graph is populated, not just modelled.
4. **Earnings transcripts** → the topic-frequency time series the product spec
   leads with ("AI mentions: 3 → 9 → 22 → 41").
5. **Backtest harness** before anyone tunes score weights, so v2 beats v1 on
   evidence rather than taste.
