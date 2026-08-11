# Market Intelligence Terminal

Turns fragmented public financial data into structured investment intelligence:
**raw data → entities → tags → relationships → time series → signals → scores.**

The differentiator is not a screener. It is a temporal **entity/tag/relationship
graph**: we record not just that NVIDIA relates to "AI data centers", but when
that relationship appeared, how often it is asserted, by which document, and
whether it is strengthening.

> **Status: foundation + one proven vertical slice.** SEC EDGAR flows end to end
> to a stock page. Most subsystems in the product spec are not built yet — see
> [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md) for an honest per-subsystem state.

## Quickstart (no dependencies, no network, ~10 seconds)

```bash
cd market-intel
make demo          # migrate + ingest fixtures + tag + signal + score
make api           # http://127.0.0.1:8787/?ticker=NVDA
make test          # 69 offline tests
```

`make demo` runs the real collectors against **recorded fixtures** (clearly
labelled `_demo: true`), so the whole pipeline is provable with the network off.
The stock page shows a DEMO banner whenever any underlying record is a fixture.

## Live SEC ingest

```bash
export MI_USER_AGENT='MarketIntel/1.0 (you@example.com)'   # SEC requires a contact
python3 pipelines/run_pipeline.py --tickers NVDA AAPL --live
```

Only the bytes-over-the-wire step differs between fixture and live mode — the
parsing, validation, resolution and persistence code paths are identical.

## What actually works today

| Capability | State |
|---|---|
| SEC EDGAR: ticker map, submissions, XBRL facts, primary documents | ✅ real collectors, fixture-proven |
| Raw → normalized → derived with full provenance | ✅ every derived row references a source record |
| Idempotent ingestion (re-run converges, never duplicates) | ✅ tested |
| Entity resolution (CIK/ticker/alias/fuzzy, ambiguity → review queue) | ✅ never auto-merges |
| Hierarchical tag graph + temporal observations | ✅ 34 tags, word-boundary matching |
| Filing diffs (added/removed/modified risk language) | ✅ sentence-level |
| Signal framework + 4 signals with z-scores and evidence | ✅ |
| Composite score with explicit `coverage` | ✅ weights are a v1 prior, **not backtested** |
| REST API (17 routes) + stock page | ✅ stdlib server; FastAPI adapter written, unrun |
| Postgres, Redis, Next.js, workers, alerts, AI research | ❌ designed, not built |

## Layout

```
apps/        api (handlers + stdlib server + FastAPI adapter), web (stock page)
packages/    shared, database, entity_resolution, tag_engine, signal_engine, scoring_engine
collectors/  sec/ (edgar, documents), common/ (transport, collector contract)
pipelines/   run_pipeline.py (the end-to-end slice), enrichment/filing_diff.py
tests/       test_all.py + fixtures/  (69 tests, all offline)
docs/        architecture, schema, data catalog, licensing, roadmap, build status
```

## Ground rules

1. **No fake implementations.** Demo data is labelled DEMO everywhere it surfaces.
2. **Provenance or it didn't happen.** Derived rows carry `source_record_id`.
3. **Never destroy raw.** `source_records` is append/upsert only.
4. **Temporal honesty.** `observed_at` (when true) vs `ingested_at` (when knowable).
   Backtests filter on the latter.
5. **Never silently merge entities.** Ambiguity goes to a review queue.
6. **Lawful sources only.** No auth circumvention, no paywall bypass. See
   [docs/DATA_LICENSING.md](docs/DATA_LICENSING.md).
