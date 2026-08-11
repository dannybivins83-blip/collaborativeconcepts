# CLAUDE.md — Market Intelligence Terminal

Guide for agents (and humans) working in `market-intel/`.

## What this is

A financial + alternative-data intelligence platform. The core is a **temporal
entity/tag/relationship graph**, not a stock screener. Read
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) then
[docs/BUILD_STATUS.md](docs/BUILD_STATUS.md) before planning any work —
BUILD_STATUS is the honest state, not the aspiration.

## ‼️ This is a subdirectory of an unrelated repo

`market-intel/` lives inside `collaborativeconcepts` (a construction-business
marketing site + permits engine). See DECISIONS.md **D-001**.

- Nothing here is deployed by Vercel; the directory is in `.vercelignore`.
- Do **not** import from the parent repo, and do not let parent tooling
  (`package.json`, `tailwind.config.js`, `api/`) leak into this tree.
- Extraction path when it grows:
  `git subtree split --prefix=market-intel -b market-intel-only`.

## Run it

```bash
make demo    # offline: real collectors against labelled fixtures
make api     # http://127.0.0.1:8787/?ticker=NVDA
make test    # 69 tests, no network, no dependencies
make lint    # byte-compile everything
```

The core is **stdlib-only** and must stay that way (D-005): the build
environment has no network, so anything requiring `pip install` cannot be
verified and must be marked unverified in BUILD_STATUS.

## The six rules

1. **Provenance or it didn't happen.** Every normalized/derived row carries
   `source_record_id`. The e2e test asserts zero orphans.
2. **Never destroy raw.** `source_records` is append/upsert only.
3. **Idempotency.** Every ingested row has a natural UNIQUE key; collectors
   upsert. Re-running a collector must converge, never duplicate.
4. **Temporal honesty.** `observed_at` = when it was true. `ingested_at` /
   `knowable_at` = when we could know it. Backtests filter on the latter.
   Getting this wrong silently buys the future.
5. **Never silently merge entities.** Ambiguity → `resolution_candidates`.
6. **No fake implementations.** Demo data is labelled DEMO everywhere it
   surfaces, including the API response and the UI banner. If something was
   written but never executed, say so in BUILD_STATUS.

## Where things live

| Path | Contents |
|---|---|
| `packages/shared` | time (rejects naive datetimes), provenance, typed errors |
| `packages/database` | `schema.sql` (28 tables), `db.py`, `repositories.py` — the only writer |
| `packages/entity_resolution` | identifier → alias → fuzzy, with a review queue |
| `packages/tag_engine` | taxonomy + word-boundary tagger + timeseries |
| `packages/signal_engine` | signal registry, z-scores, persistence |
| `packages/scoring_engine` | versioned composite weights + coverage |
| `collectors/common` | collector contract, HTTP/fixture transport |
| `collectors/sec` | edgar (ticker map, submissions, XBRL), documents (sections) |
| `pipelines/run_pipeline.py` | the end-to-end slice |
| `apps/api` | handlers (framework-agnostic) + stdlib server + FastAPI adapter |
| `apps/web/index.html` | the stock page (no build step) |
| `tests/test_all.py` | 69 offline tests + fixtures |

## Adding things

Use the skills in `.claude/skills/`: `add-data-source`, `build-collector`,
`create-tag`, `create-signal`, `build-api-endpoint`. Each encodes the
non-negotiables above.

A new data source is **registered with a `license_class` before a collector
exists** — accessible does not mean redistributable
(docs/DATA_LICENSING.md). No collector may bypass authentication, paywalls,
robots directives or rate limits.

## Claims discipline

Do not state that a signal predicts anything. There is no backtest harness yet,
so any edge claim is unsupported. The composite score ships with an explicit
"weights are a v1 prior, not backtested" disclaimer in both the API and the UI —
do not remove it.
