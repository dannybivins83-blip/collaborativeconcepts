# API Spec (v1)

Base: `/api/v1`. All routes are GET and return JSON. Handlers live in
`apps/api/handlers.py`; the stdlib dev server and FastAPI adapter both delegate
to them.

| Route | Returns |
|---|---|
| `/health` | table counts + whether any stored record is DEMO |
| `/data-health` | per-collector last run, fetched/written/rejected, pending entity reviews |
| `/search?q=` | entities (name + alias match) and tags |
| `/stocks?limit=` | securities with latest composite score |
| `/stocks/{ticker}` | entity, security, identifiers, aliases, latest filing, demo flags |
| `/stocks/{ticker}/financials` | XBRL series by concept, each row with `source_record_id` |
| `/stocks/{ticker}/filings` | filing history |
| `/stocks/{ticker}/filing-changes` | added/removed/modified language vs prior comparable filing, grouped by section |
| `/stocks/{ticker}/tags` | tag graph with hierarchy path + monthly timeseries |
| `/stocks/{ticker}/signals` | latest signal observations with parsed evidence |
| `/stocks/{ticker}/score` | stored + freshly computed score, categories, coverage, disclaimer |
| `/stocks/{ticker}/relationships` | graph edges (⚠️ no collector populates these yet) |
| `/themes` | all tags with mention/entity counts |
| `/themes/{slug}` | tag, hierarchy path, entities ranked by mentions |
| `/signals` | registered signal definitions + observation counts |
| `/screener?tag=&signal=&min_zscore=&min_score=&limit=` | filtered cross-section |

## Conventions

- `404` unknown ticker/theme/route; `400` missing or **unknown** query params
  (the screener rejects unrecognised filters rather than ignoring them).
- Errors: `{"error": "message"}`.
- Any response containing derived numbers also carries provenance —
  `source_record_id`, `evidence`, or `as_of`.
- Score responses always include the "weights are a v1 prior, not backtested"
  disclaimer. Do not strip it in a client.

## Not implemented

POST/PUT anything (watchlists, alerts, auth), pagination cursors, rate limiting,
API keys. See BUILD_STATUS.
