# Roadmap

## Phase 0 — Foundation ✅ (done)
Monorepo, schema, provenance, idempotency, collector contract, SEC EDGAR,
entity resolution, tag graph, filing diffs, signal framework, scoring, API,
stock page, 69 tests.

## Phase 1 — Make the slice real (next)
1. Verify FastAPI + docker-compose on a networked host (only unrun artifacts).
2. Extract to its own repo (D-001) before adding contributors.
3. Prices/OHLCV — requires the provider decision.
4. Relationship extraction from `filing_sections` (customer/supplier/competitor)
   so the graph is populated, not just modelled.
5. Backfill the S&P 500 by CIK; measure ingest cost and query latency at scale.

## Phase 2 — Intelligence depth
Earnings transcripts + topic frequency time series · insider Form 4 ·
13F institutional flow · cross-source confirmation scoring · backtest harness
(prerequisite for any weight tuning) · alerts + delivery · watchlists as feeds.

## Phase 3 — Product surface
Next.js frontend · dashboard (trending tags, emerging themes, unusual signals) ·
full screener · saved screens · users/auth/billing · public API keys.

## Phase 4 — AI research layer
Retrieval over stored evidence only (never free-form generation of financial
facts) · per-domain analyst agents · natural-language → structured query.

## Phase 5 — Alternative data
Web traffic · app ranks · job postings · patents · government contracts · FDA ·
trade data. Only after the architecture is proven and licensing is cleared.

## Standing rules
- No new data source without a `license_class` and a catalog entry.
- No claim of predictive edge without a backtest.
- Demo data always labelled DEMO.
