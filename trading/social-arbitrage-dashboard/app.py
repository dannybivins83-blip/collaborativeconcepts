"""Social Arbitrage Investment Dashboard.

Maps consumer search-trend breakouts (Google Shopping search interest via pytrends)
against public-market pricing (yfinance) to flag tickers where consumer demand is
accelerating but the stock hasn't caught up yet ("Sleepy Wall St"), versus tickers
where the move is already priced in ("Hype Priced In"). Built for a small
(~$3,000) options-buying account: a research/screening tool, not investment advice.

Architecture:
  - Pure, network-free functions (compute_breakout_score, compute_pct_position,
    classify_signal, parse_google_news_rss, build_news_query_url) are unit-tested
    offline in _tests.py.
  - Network functions (fetch_trend_baseline/recent, fetch_market_data,
    fetch_news_headlines) each have a `_safe` wrapper that never raises — a
    failure on one keyword must not crash the whole scan.
  - A hard security gate (authenticate()) blocks ALL code below it — no dashboard
    render, no background network calls — until valid credentials are entered.

Known operational risk: Google Trends aggressively blocks requests from
datacenter/cloud IPs (exactly what Render/Heroku assign you). The randomized
delay loop reduces — it does not eliminate — 429/blocked responses. If Trends
calls fail consistently once deployed, that's Google's IP reputation system, not
a bug here; consider a residential/rotating proxy if reliability matters.
"""
import json
import os
import random
import secrets as pysecrets
import time
import urllib.parse
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from pytrends.request import TrendReq

# --------------------------------------------------------------------------- #
# Signal labels
# --------------------------------------------------------------------------- #
SLEEPY_WALL_ST = "🚨 ALERT: Sleepy Wall St"
HYPE_PRICED_IN = "🔥 Hype Priced In"
NO_ANOMALY = "💤 No Anomaly"
DATA_UNAVAILABLE = "⚠️ Data Unavailable"

DEFAULT_KEYWORD_MAP = {"Hoka shoes": "DECK", "Celsius energy": "CELH", "On running cloud": "ONON"}

GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"


# --------------------------------------------------------------------------- #
# Pure computation — no network, no Streamlit. Unit-tested in _tests.py.
# --------------------------------------------------------------------------- #
def compute_breakout_score(baseline_series, recent_series):
    """(true 7-day trailing mean) / (5-year baseline mean).

    `baseline_series` must come from a 5-year pull (Google Trends returns WEEKLY
    points at that range). `recent_series` must come from a short (<=3-month)
    pull, which Trends returns at DAILY granularity — only then does
    `.tail(7)` mean an actual trailing calendar week. Mixing this up (tailing
    the 5-year series directly) silently computes a ~7-WEEK average and mislabels
    it as 7-day; this function deliberately requires both series to avoid that.

    Returns None if either series is missing/empty or the baseline mean is 0.
    """
    if baseline_series is None or recent_series is None:
        return None
    baseline = baseline_series.dropna()
    recent = recent_series.dropna()
    if baseline.empty or recent.empty:
        return None
    baseline_mean = baseline.mean()
    if baseline_mean == 0:
        return None
    trailing_7d = recent.tail(7)
    if trailing_7d.empty:
        return None
    return float(trailing_7d.mean() / baseline_mean)


def compute_pct_position(price, low, high):
    """Current price's % position within the 52-week [low, high] range, clamped
    to [0, 100] (price can be briefly outside a stale/lagged 52wk band)."""
    if price is None or low is None or high is None:
        return None
    try:
        price, low, high = float(price), float(low), float(high)
    except (TypeError, ValueError):
        return None
    if high == low:
        return None
    pct = (price - low) / (high - low) * 100.0
    return max(0.0, min(100.0, pct))


def classify_signal(breakout_score, pct_position, min_score, max_pct):
    """Asymmetric-signal classifier.

    Sleepy Wall St: consumer demand breaking out (score >= threshold) but the
    stock is STILL below the 52-week position ceiling — the market hasn't
    reacted yet. Hype Priced In: same breakout, but price is already at/above
    the ceiling. No Anomaly: no breakout. Data Unavailable: missing inputs.
    """
    if breakout_score is None or pct_position is None:
        return DATA_UNAVAILABLE
    if breakout_score >= min_score:
        return SLEEPY_WALL_ST if pct_position <= max_pct else HYPE_PRICED_IN
    return NO_ANOMALY


def build_news_query_url(keyword: str, ticker: str) -> str:
    """Google News RSS search URL for `"keyword" OR TICKER`, most-recent-first."""
    query = f'"{keyword}" OR {ticker}'
    params = urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return f"{GOOGLE_NEWS_RSS_BASE}?{params}"


def parse_google_news_rss(xml_text: str, limit: int = 5):
    """Parse a Google News RSS <item> list into
    [{title, link, pubDate, source}, ...], newest-first (feed order), capped at
    `limit`. Malformed XML or missing fields degrade to an empty/partial list
    rather than raising — a scraper must never crash the caller."""
    items = []
    if not xml_text:
        return items
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        items.append({"title": title, "link": link, "pubDate": pub_date, "source": source})
    return items


def random_delay(min_seconds: float = 3.0, max_seconds: float = 5.0):
    """Mandatory randomized delay between Trends calls — reduces (does not
    eliminate) HTTP 429 blocking. See module docstring re: datacenter IPs."""
    time.sleep(random.uniform(min_seconds, max_seconds))


# --------------------------------------------------------------------------- #
# Network layer — each has a `_safe` wrapper below that never raises.
# --------------------------------------------------------------------------- #
def fetch_trend_baseline(keyword: str) -> pd.DataFrame:
    """5-year Google Shopping search interest (WEEKLY granularity) — the
    long-run baseline for the breakout ratio's denominator."""
    client = TrendReq(hl="en-US", tz=360)
    client.build_payload([keyword], cat=0, timeframe="today 5-y", geo="US", gprop="froogle")
    df = client.interest_over_time()
    if df is None or df.empty:
        return pd.DataFrame()
    return df.drop(columns=["isPartial"], errors="ignore")


def fetch_trend_recent(keyword: str) -> pd.DataFrame:
    """~1-month Google Shopping search interest (DAILY granularity — Trends
    only returns daily points for ranges under ~3 months). Used to isolate a
    TRUE trailing 7-day window; see compute_breakout_score's docstring."""
    client = TrendReq(hl="en-US", tz=360)
    client.build_payload([keyword], cat=0, timeframe="today 1-m", geo="US", gprop="froogle")
    df = client.interest_over_time()
    if df is None or df.empty:
        return pd.DataFrame()
    return df.drop(columns=["isPartial"], errors="ignore")


def fetch_trends_safe(keyword: str):
    """Fetch both Trends windows with the mandatory delay between the two
    calls. Returns (baseline_df_or_None, recent_df_or_None, error_or_None)."""
    try:
        baseline_df = fetch_trend_baseline(keyword)
    except Exception as e:  # pytrends raises many third-party error types (429s,
        return None, None, f"Trends baseline fetch failed for '{keyword}': {e}"  # blocked JSON, timeouts) — one bad keyword must not kill the scan.
    if baseline_df.empty:
        return None, None, f"No baseline (5-year) trend data for '{keyword}'."

    random_delay()  # politeness delay between this keyword's two Trends calls

    try:
        recent_df = fetch_trend_recent(keyword)
    except Exception as e:
        return baseline_df, None, f"Trends recent-window fetch failed for '{keyword}': {e}"
    if recent_df.empty:
        return baseline_df, None, f"No recent (7-day) trend data for '{keyword}'."
    return baseline_df, recent_df, None


def _safe_get(mapping, *keys):
    """Try several key spellings against a dict-like/attr-like object (yfinance's
    fast_info has changed field naming across versions); first hit wins."""
    for key in keys:
        try:
            val = mapping[key]
            if val is not None:
                return val
        except Exception:
            pass
    return None


def fetch_market_data(ticker: str) -> dict:
    """Regular market price, 52-week high/low, and options-chain availability."""
    tk = yf.Ticker(ticker)
    price = low = high = None
    try:
        fast = tk.fast_info
        price = _safe_get(fast, "lastPrice", "last_price")
        low = _safe_get(fast, "yearLow", "year_low")
        high = _safe_get(fast, "yearHigh", "year_high")
    except Exception:
        pass
    if price is None or low is None or high is None:
        try:
            info = tk.info or {}
        except Exception:
            info = {}
        price = price if price is not None else (info.get("regularMarketPrice") or info.get("currentPrice"))
        low = low if low is not None else info.get("fiftyTwoWeekLow")
        high = high if high is not None else info.get("fiftyTwoWeekHigh")
    try:
        opts = tk.options
        options_available = "Yes" if opts and len(opts) > 0 else "No"
    except Exception:
        options_available = "No"
    return {"price": price, "low": low, "high": high, "options_available": options_available}


def fetch_market_data_safe(ticker: str):
    try:
        data = fetch_market_data(ticker)
        if data["price"] is None:
            return data, f"No price data returned for '{ticker}' — check the symbol."
        return data, None
    except Exception as e:
        return None, f"Market data fetch failed for '{ticker}': {e}"


def fetch_news_headlines(keyword: str, ticker: str, limit: int = 5, timeout: float = 8.0):
    url = build_news_query_url(keyword, ticker)
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return parse_google_news_rss(resp.text, limit=limit)


def fetch_news_safe(keyword: str, ticker: str):
    try:
        return fetch_news_headlines(keyword, ticker), None
    except Exception as e:
        return [], f"News fetch failed: {e}"


# --------------------------------------------------------------------------- #
# Security gate — must run (and block) before ANY dashboard code or network call.
# --------------------------------------------------------------------------- #
def _get_secret(key: str):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass  # no secrets.toml configured — fall through to env vars
    return os.environ.get(key)


def authenticate() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.title("🔒 Social Arbitrage Dashboard")

    expected_user = _get_secret("SECURITY_USERNAME")
    expected_pass = _get_secret("SECURITY_PASSWORD")
    if not expected_user or not expected_pass:
        st.error(
            "Security credentials are not configured. Set `SECURITY_USERNAME` and "
            "`SECURITY_PASSWORD` in `.streamlit/secrets.toml` or as environment "
            "variables before running this app. See `.streamlit/secrets.toml.example`."
        )
        return False

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        user_ok = pysecrets.compare_digest(username, str(expected_user))
        pass_ok = pysecrets.compare_digest(password, str(expected_pass))
        if user_ok and pass_ok:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid username or password.")
    return False


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def render_sidebar():
    st.sidebar.header("⚙️ Configuration")
    raw_json = st.sidebar.text_area(
        "Tracked Keywords → Tickers (JSON)",
        value=json.dumps(DEFAULT_KEYWORD_MAP, indent=2),
        height=180,
        help='e.g. {"Hoka shoes": "DECK", "Celsius energy": "CELH"}',
    )
    keyword_map = None
    try:
        parsed = json.loads(raw_json)
        if not isinstance(parsed, dict) or not parsed:
            raise ValueError("must be a non-empty JSON object of \"keyword\": \"TICKER\" pairs")
        keyword_map = {str(k): str(v).upper() for k, v in parsed.items()}
    except (json.JSONDecodeError, ValueError) as e:
        st.sidebar.error(f"Invalid JSON: {e}")

    min_score = st.sidebar.slider("Minimum Breakout Score Alert Trigger", 1.0, 5.0, 2.0, 0.1)
    max_pct = st.sidebar.slider("Maximum 52-Week Price Position %", 10, 100, 50, 5)

    n = len(keyword_map) if keyword_map else 0
    if n:
        est_s = n * (2 * 4 + 2)  # ~4s avg delay x2 calls/keyword + slack, ignoring HTTP latency
        st.sidebar.caption(f"⏱️ ~{n} asset(s) → roughly {est_s // 60}m {est_s % 60}s to scan "
                           f"(rate-limit delays dominate).")

    run = st.sidebar.button("🚀 Run Live Social Arbitrage Report", type="primary", disabled=(keyword_map is None))
    st.sidebar.caption(
        "⚠️ Google Trends blocks many datacenter/cloud IPs regardless of delay. "
        "Educational research tool — not investment advice."
    )
    return keyword_map, min_score, max_pct, run


# --------------------------------------------------------------------------- #
# Scan pipeline
# --------------------------------------------------------------------------- #
def run_scan(keyword_map: dict, min_score: float, max_pct: float):
    results = []
    trend_frames = {}
    news_by_keyword = {}
    n = len(keyword_map)
    progress = st.progress(0.0)
    status = st.empty()

    for i, (keyword, ticker) in enumerate(keyword_map.items()):
        status.text(f"Scanning {i + 1}/{n}: {keyword} → {ticker}")

        baseline_df, recent_df, trend_err = fetch_trends_safe(keyword)
        market, market_err = fetch_market_data_safe(ticker)
        news_items, news_err = fetch_news_safe(keyword, ticker)

        baseline_series = baseline_df[keyword] if baseline_df is not None and keyword in baseline_df else None
        recent_series = recent_df[keyword] if recent_df is not None and keyword in recent_df else None
        breakout = compute_breakout_score(baseline_series, recent_series)

        price = (market or {}).get("price")
        low = (market or {}).get("low")
        high = (market or {}).get("high")
        pct_pos = compute_pct_position(price, low, high)
        signal = classify_signal(breakout, pct_pos, min_score, max_pct)

        results.append({
            "keyword": keyword,
            "ticker": ticker,
            "breakout_score": breakout,
            "pct_52wk": pct_pos,
            "price": price,
            "options": (market or {}).get("options_available", "No"),
            "signal": signal,
            "notes": " / ".join(filter(None, [trend_err, market_err])),
        })
        trend_frames[keyword] = baseline_df
        news_by_keyword[keyword] = (news_items, news_err)

        progress.progress((i + 1) / n)
        if i < n - 1:
            random_delay()  # mandatory delay BETWEEN asset evaluations

    status.empty()
    progress.empty()
    st.session_state["sa_results"] = pd.DataFrame(results)
    st.session_state["sa_trends"] = trend_frames
    st.session_state["sa_news"] = news_by_keyword


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _style_results(df: pd.DataFrame):
    def _row_style(row):
        if row["signal"] == SLEEPY_WALL_ST:
            return ["background-color: #ffd6d6"] * len(row)
        if row["signal"] == HYPE_PRICED_IN:
            return ["background-color: #ffe8b3"] * len(row)
        return [""] * len(row)

    fmt = {
        "breakout_score": lambda v: f"{v:.2f}x" if pd.notna(v) else "n/a",
        "pct_52wk": lambda v: f"{v:.0f}%" if pd.notna(v) else "n/a",
        "price": lambda v: f"${v:.2f}" if pd.notna(v) else "n/a",
    }
    return df.reset_index(drop=True).style.apply(_row_style, axis=1).format(fmt)


def _render_keyword_tab(row, trend_df, news_tuple):
    news_items, news_err = news_tuple
    badge = {SLEEPY_WALL_ST: "🚨", HYPE_PRICED_IN: "🔥", NO_ANOMALY: "💤"}.get(row["signal"], "⚠️")
    st.markdown(f"### {badge} {row['signal']}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Breakout Score", f"{row['breakout_score']:.2f}x" if pd.notna(row["breakout_score"]) else "n/a")
    m2.metric("52-Wk Position", f"{row['pct_52wk']:.0f}%" if pd.notna(row["pct_52wk"]) else "n/a")
    m3.metric("Price", f"${row['price']:.2f}" if pd.notna(row["price"]) else "n/a")

    if row["notes"]:
        st.caption(f"⚠️ {row['notes']}")

    if trend_df is not None and not trend_df.empty and row["keyword"] in trend_df.columns:
        st.line_chart(trend_df[row["keyword"]])
    else:
        st.info("5-year trend chart unavailable for this keyword.")

    st.markdown("**📰 Recent headlines**")
    if news_err:
        st.warning(news_err)
    elif not news_items:
        st.caption("No recent headlines found.")
    else:
        for item in news_items:
            st.markdown(f"- [{item['title']}]({item['link']})")
            meta = " · ".join(filter(None, [item.get("source"), item.get("pubDate")]))
            if meta:
                st.caption(meta)


def render_results():
    if "sa_results" not in st.session_state:
        st.info("Configure your keyword → ticker map in the sidebar, then click "
                "**🚀 Run Live Social Arbitrage Report** to begin.")
        return

    df = st.session_state["sa_results"]
    trend_frames = st.session_state["sa_trends"]
    news_by_keyword = st.session_state["sa_news"]

    alerts = df[df["signal"] == SLEEPY_WALL_ST]

    st.subheader("🎯 Signal Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚨 Sleepy Wall St", len(alerts))
    c2.metric("🔥 Hype Priced In", len(df[df["signal"] == HYPE_PRICED_IN]))
    c3.metric("💤 No Anomaly", len(df[df["signal"] == NO_ANOMALY]))
    c4.metric("Tracked Assets", len(df))

    if len(alerts):
        st.markdown("#### 🚨 Active Sleepy Wall St Signals")
        for _, row in alerts.iterrows():
            st.error(
                f"**{row['keyword']}** ({row['ticker']}) — Breakout Score "
                f"**{row['breakout_score']:.2f}x** baseline, only **{row['pct_52wk']:.0f}%** "
                f"of its 52-week range. Options available: {row['options']}."
            )
    else:
        st.caption("No asymmetric 'Sleepy Wall St' signals on this scan.")

    st.subheader("📊 Full Scan Grid")
    st.dataframe(_style_results(df), use_container_width=True)

    st.subheader("📈 Keyword Detail — Trend Charts & News")
    tabs = st.tabs([f"{r.keyword} ({r.ticker})" for r in df.itertuples()])
    for tab, (_, row) in zip(tabs, df.iterrows()):
        with tab:
            _render_keyword_tab(row, trend_frames.get(row["keyword"]),
                                news_by_keyword.get(row["keyword"], ([], None)))


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    st.set_page_config(page_title="Social Arbitrage Dashboard", page_icon="📈", layout="wide")

    if not authenticate():
        st.stop()  # blocks everything below: no dashboard, no network calls

    st.title("📈 Social Arbitrage Investment Dashboard")
    st.caption(
        "Consumer search-trend breakouts mapped to public tickers, sized for a small "
        "options-buying account. Educational research tool — not investment advice."
    )

    keyword_map, min_score, max_pct, run = render_sidebar()

    if run and keyword_map:
        run_scan(keyword_map, min_score, max_pct)

    render_results()


if __name__ == "__main__":
    main()
