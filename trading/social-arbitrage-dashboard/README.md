# Social Arbitrage Investment Dashboard

Maps consumer search-trend breakouts (Google Shopping search interest) against
public-market pricing to flag tickers where consumer demand is accelerating but
the stock hasn't caught up — versus tickers where the move is already priced in.
Built for a small (~$3,000) options-buying account.

**Educational research tool, not investment advice.**

## How it works

- **Sentiment layer** (`pytrends`, Google Shopping / `gprop=froogle`, US): pulls
  a 5-year weekly baseline and a 1-month daily window per keyword, and computes
  `Breakout Score = (true trailing-7-day mean) / (5-year baseline mean)`.
  **Why two calls, not one:** Google Trends returns *weekly*-granularity points
  for a 5-year pull — tailing that directly would silently average the last
  ~7 *weeks*, not 7 days. A short (`today 1-m`) daily-granularity pull is
  fetched separately so `.tail(7)` is an actual calendar week. See
  `compute_breakout_score`'s docstring in `app.py`.
- **Market layer** (`yfinance`): price, 52-week high/low → % position in that
  range, and whether an options chain exists.
- **News layer** (Google News RSS, `news.google.com/rss/search`): top 3–5
  headlines for `"keyword" OR TICKER`, shown under each keyword's chart.
- **Signals:** 🚨 *Sleepy Wall St* (breakout confirmed, price still low in its
  52-week range — asymmetric opportunity) · 🔥 *Hype Priced In* (breakout
  confirmed, price already near its high) · 💤 *No Anomaly*.

## Setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with real SECURITY_USERNAME / SECURITY_PASSWORD
streamlit run app.py
```

`.streamlit/secrets.toml` is gitignored — never commit it. On Render/Heroku,
set `SECURITY_USERNAME` / `SECURITY_PASSWORD` as environment variables instead
(the app checks `st.secrets` first, then falls back to `os.environ` — no code
change needed either way). Nothing renders and no network call fires until a
valid login submits.

## Deploy

The `Procfile` binds to `0.0.0.0:$PORT` for Render/Heroku-style hosts:

```
web: sh -c "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true"
```

## Known operational risk — read before relying on this in production

**Google Trends aggressively blocks requests from datacenter/cloud IPs** —
exactly what Render/Heroku assign you. The mandatory 3–5s randomized delay
between calls *reduces* 429/blocked responses; it does not eliminate them on a
cloud host the way it would from a residential IP. If Trends calls fail
consistently once deployed, that's Google's IP-reputation system, not a bug
here. If reliability matters, consider a residential/rotating proxy in front
of the `pytrends` calls.

Every network call (`fetch_trends_safe`, `fetch_market_data_safe`,
`fetch_news_safe`) is wrapped to degrade gracefully — one bad ticker or a
blocked Trends call shows an inline warning for that row/tab; it never crashes
the whole scan.

## Testing

Offline, no network — tests the pure functions only (score math, % position,
signal classification, RSS parsing):

```bash
python3 _tests.py
```
