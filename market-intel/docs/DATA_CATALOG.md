# Data Catalog

Every source must be registered in `data_sources` with a `license_class` before
a collector for it may run. `enabled` is a per-source kill switch.

## Implemented

### SEC EDGAR — `sec`
| Field | Value |
|---|---|
| Category | filings |
| Official URL | https://www.sec.gov/edgar |
| Endpoints | `files/company_tickers.json`, `data.sec.gov/submissions/CIK{10}.json`, `data.sec.gov/api/xbrl/companyfacts/CIK{10}.json`, `www.sec.gov/Archives/...` primary documents |
| Auth | none |
| Access rules | declared User-Agent **with contact email** required; ≤10 req/s. Both enforced in `HttpTransport`. |
| Update frequency | continuous |
| Historical depth | 1993–present |
| License class | **PUBLIC** (US government work) |
| Collector status | ✅ ticker map, submissions, companyfacts, documents |
| Fields used | CIK, ticker, name, former names, exchange, accession, form, filed/period dates, primary doc, 8-K items, XBRL concept/unit/value/period/form/filed |

## Investigated, not implemented

| Source | Category | Auth | License class | Priority | Note |
|---|---|---|---|---|---|
| FRED (St. Louis Fed) | macro | API key (free) | OPEN_DATA | high | series-level macro context |
| BLS | macro | key (free) | OPEN_DATA | medium | employment/CPI |
| BEA | macro | key (free) | OPEN_DATA | medium | GDP/industry |
| US Census | macro/trade | key (free) | OPEN_DATA | medium | import/export detail |
| USPTO PatentsView | innovation | none | OPEN_DATA | medium | patent → company mapping |
| FDA (openFDA) | health | none | OPEN_DATA | medium | approvals, adverse events |
| USASpending / SAM.gov | gov contracts | none/key | OPEN_DATA | medium | contract awards by vendor |
| Company IR / press releases | corporate | none | REVIEW_REQUIRED | high | per-site terms differ |
| Earnings transcripts | corporate | varies | **LICENSE_REQUIRED** | high | most vendors prohibit redistribution |
| Market prices / OHLCV | market | key | **LICENSE_REQUIRED** | high | needs a paid provider decision |
| Options chains / flow | market | key | **LICENSE_REQUIRED** | medium | |
| News APIs | news | key | **LICENSE_REQUIRED** | medium | headline redistribution usually restricted |
| Google Trends | alt | — | REVIEW_REQUIRED | low | official API still application-gated alpha; index is rescaled per request |
| App ranks / web traffic / satellite | alt | key | LICENSE_REQUIRED | later | expensive; defer until architecture is proven |

## Rules

1. No collector may bypass authentication, paywalls, robots directives or rate
   limits. If a source needs a login we do not have, it does not get a collector.
2. Accessible ≠ redistributable. Classify before building (see DATA_LICENSING.md).
3. Vendor-specific logic stays inside its collector so providers are swappable.
