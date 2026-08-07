"""
Google Search Console puller — real query/page/geo performance for the
Collaborative Concepts properties (apex, wwslgc, roofanchorcert, davit).

Why this and not Google Trends: Trends returns a *normalized 0-100 index* that
is rescaled per request, so two pulls aren't comparable and niche B2B terms
("walking working surfaces compliance") often don't register at all. Search
Console returns *your actual* impressions, clicks, CTR and average position,
per query and per page — the real demand signal for these pages.

Architecture:
  1. AUTH     — OAuth2 refresh-token grant (stdlib-style POST, same shape as the
                tastytrade broker) OR a Google service account (RS256 JWT signed
                with `cryptography`, already a dependency). Service account is
                preferred for cron: no interactive consent, no token expiry
                babysitting. Add the service-account email as a *user* on the
                Search Console property (Settings -> Users and permissions).
  2. FETCH    — searchAnalytics/query with startRow pagination (API caps a page
                at 25k rows) and backoff on 429/5xx.
  3. ANALYZE  — pure functions over rows (no I/O, unit-tested offline):
                period comparison, striking-distance opportunities, CTR gaps,
                per-city/per-county rollups.
  4. REPORT   — markdown + CSV written to disk for the SEO log.

Cross-reference: `by_county()` rolls page-level rows up to the same four
counties the permits engine covers (api/permits.py), so search demand can be
paired with real permit volume — `cross_permits()` builds that table and flags
counties with permit activity but no landing page.

Config (env):
  GSC_SITE                  default property, e.g. https://wwslgc.collaborativeconceptsfl.com
  GSC_SERVICE_ACCOUNT_JSON  path to (or inline) service-account JSON   [preferred]
  GSC_CLIENT_ID / GSC_CLIENT_SECRET / GSC_REFRESH_TOKEN                [OAuth alt]

No new dependencies: requests + cryptography (both already in requirements).
"""

import base64
import csv
import io
import json
import os
import time
from datetime import date, datetime, timedelta

import requests

API_ROOT = "https://searchconsole.googleapis.com/webmasters/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
UA = "CollaborativeConcepts-GSC/1.0 (+https://collaborativeconceptsfl.com)"

HTTP_TIMEOUT = 30
PAGE_ROWS = 25000          # API maximum rows per request
MAX_PAGES = 20             # safety ceiling: 500k rows
RETRIES = 4

# Search Console finalizes data on a lag; anything newer is partial and will
# revise upward. Reports end at this offset unless told otherwise.
DATA_LAG_DAYS = 3

# wwslgc city landing pages -> county. Keep in sync with wwslgc/*.html; the
# permits engine (api/permits.py) covers the same four counties.
CITY_COUNTY = {
    "miami": "Miami-Dade",
    "aventura": "Miami-Dade",
    "fort-lauderdale": "Broward",
    "hollywood": "Broward",
    "pompano-beach": "Broward",
    "west-palm-beach": "Palm Beach",
    "boca-raton": "Palm Beach",
    "boynton-beach": "Palm Beach",
    "delray-beach": "Palm Beach",
    "highland-beach": "Palm Beach",
    "hypoluxo": "Palm Beach",
    "lake-worth": "Palm Beach",
    "north-palm-beach": "Palm Beach",
    "riviera-beach": "Palm Beach",
}
COUNTIES = ["Martin", "Palm Beach", "Broward", "Miami-Dade"]


class GSCError(Exception):
    pass


# ---------------------------------------------------------------- auth ------
def _jwt_assertion(sa: dict) -> str:
    """Signed RS256 assertion for the service-account token exchange."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    def seg(obj):
        raw = json.dumps(obj, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=")

    now = int(time.time())
    header = seg({"alg": "RS256", "typ": "JWT"})
    claims = seg({
        "iss": sa["client_email"],
        "scope": SCOPE,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    })
    body = header + b"." + claims
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = key.sign(body, padding.PKCS1v15(), hashes.SHA256())
    return (body + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()


def _load_service_account(raw: str):
    """Accept a path to the JSON key file or the JSON itself (env-friendly)."""
    if not raw:
        return None
    try:
        if os.path.exists(raw):
            with open(raw) as f:
                return json.load(f)
        return json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        raise GSCError(f"GSC_SERVICE_ACCOUNT_JSON unreadable: {e}") from e


class Auth:
    """Mints and caches an access token. Never logs a secret value."""

    def __init__(self, service_account=None, client_id="", client_secret="", refresh_token=""):
        self.sa = service_account
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._token = None
        self._expiry = 0.0

    @classmethod
    def from_env(cls, env=None):
        env = env if env is not None else os.environ
        sa = _load_service_account(env.get("GSC_SERVICE_ACCOUNT_JSON", ""))
        return cls(service_account=sa,
                   client_id=env.get("GSC_CLIENT_ID", ""),
                   client_secret=env.get("GSC_CLIENT_SECRET", ""),
                   refresh_token=env.get("GSC_REFRESH_TOKEN", ""))

    def configured(self) -> list:
        """Missing-config problems, by NAME only (never values)."""
        if self.sa:
            missing = [k for k in ("client_email", "private_key") if not self.sa.get(k)]
            return [f"service account JSON missing {k}" for k in missing]
        missing = [n for n, v in (("GSC_CLIENT_ID", self.client_id),
                                  ("GSC_CLIENT_SECRET", self.client_secret),
                                  ("GSC_REFRESH_TOKEN", self.refresh_token)) if not v]
        if len(missing) == 3:
            return ["no credentials: set GSC_SERVICE_ACCOUNT_JSON (preferred) "
                    "or GSC_CLIENT_ID + GSC_CLIENT_SECRET + GSC_REFRESH_TOKEN"]
        return [f"{n} is not set" for n in missing]

    def token(self) -> str:
        if self._token and time.time() < self._expiry - 60:
            return self._token
        problems = self.configured()
        if problems:
            raise GSCError("; ".join(problems))
        if self.sa:
            payload = {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                       "assertion": _jwt_assertion(self.sa)}
        else:
            payload = {"grant_type": "refresh_token",
                       "client_id": self.client_id,
                       "client_secret": self.client_secret,
                       "refresh_token": self.refresh_token}
        r = requests.post(TOKEN_URL, data=payload, timeout=HTTP_TIMEOUT,
                          headers={"User-Agent": UA})
        if r.status_code != 200:
            raise GSCError(f"token exchange failed: HTTP {r.status_code} {r.text[:300]}")
        data = r.json()
        if not data.get("access_token"):
            raise GSCError("token exchange returned no access_token")
        self._token = data["access_token"]
        self._expiry = time.time() + int(data.get("expires_in", 3600))
        return self._token


# --------------------------------------------------------------- client -----
class SearchConsole:
    def __init__(self, auth: Auth, session=None):
        self.auth = auth
        self.session = session or requests.Session()

    def _post(self, url, payload):
        last = ""
        for attempt in range(RETRIES):
            r = self.session.post(url, json=payload, timeout=HTTP_TIMEOUT, headers={
                "Authorization": f"Bearer {self.auth.token()}",
                "Content-Type": "application/json",
                "User-Agent": UA,
            })
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code} {r.text[:300]}"
            # 429 = per-minute quota, 5xx = transient. Back off and retry.
            if r.status_code in (429, 500, 502, 503, 504) and attempt < RETRIES - 1:
                time.sleep(min(2 ** attempt * 2, 30))
                continue
            break
        raise GSCError(f"searchAnalytics query failed: {last}")

    def sites(self) -> list:
        r = self.session.get(f"{API_ROOT}/sites", timeout=HTTP_TIMEOUT, headers={
            "Authorization": f"Bearer {self.auth.token()}", "User-Agent": UA})
        if r.status_code != 200:
            raise GSCError(f"site list failed: HTTP {r.status_code} {r.text[:200]}")
        return [s.get("siteUrl") for s in (r.json().get("siteEntry") or [])]

    def query(self, site, start, end, dimensions=("query",), row_limit=PAGE_ROWS,
              search_type="web", data_state="final", filters=None):
        """All rows for a date range, paginated. Returns list of dicts:
        {keys: [...], clicks, impressions, ctr, position}."""
        url = f"{API_ROOT}/sites/{requests.utils.quote(site, safe='')}/searchAnalytics/query"
        out, start_row = [], 0
        for _ in range(MAX_PAGES):
            payload = {"startDate": str(start), "endDate": str(end),
                       "dimensions": list(dimensions), "rowLimit": row_limit,
                       "startRow": start_row, "type": search_type,
                       "dataState": data_state}
            if filters:
                payload["dimensionFilterGroups"] = filters
            rows = self._post(url, payload).get("rows") or []
            out.extend(rows)
            if len(rows) < row_limit:
                break
            start_row += len(rows)
        return out


# ------------------------------------------------------------- analysis -----
def _key(row, i=0):
    keys = row.get("keys") or []
    return keys[i] if i < len(keys) else ""


def to_records(rows, dimensions):
    """Flatten API rows into dicts with named dimension columns."""
    recs = []
    for r in rows:
        rec = {d: _key(r, i) for i, d in enumerate(dimensions)}
        rec.update({
            "clicks": int(r.get("clicks") or 0),
            "impressions": int(r.get("impressions") or 0),
            "ctr": round(float(r.get("ctr") or 0.0), 6),
            "position": round(float(r.get("position") or 0.0), 2),
        })
        recs.append(rec)
    return recs


def totals(recs):
    clicks = sum(r["clicks"] for r in recs)
    impr = sum(r["impressions"] for r in recs)
    # Position must be impression-weighted; a plain mean over-weights long-tail rows.
    pos = (sum(r["position"] * r["impressions"] for r in recs) / impr) if impr else 0.0
    return {"clicks": clicks, "impressions": impr,
            "ctr": round(clicks / impr, 6) if impr else 0.0,
            "position": round(pos, 2), "rows": len(recs)}


def top(recs, by="clicks", n=20):
    return sorted(recs, key=lambda r: r.get(by, 0), reverse=True)[:n]


def compare(current, previous, key, min_impressions=10):
    """Period-over-period movers keyed by `key` (e.g. 'query' or 'page').

    Includes rows that DISAPPEARED (present last period, absent now) — a term
    that fell off entirely is usually the biggest loss on the page, and it is
    invisible if you only walk the current period.
    """
    prev = {r[key]: r for r in previous}
    out = []
    for r in current:
        p = prev.get(r[key])
        if max(r["impressions"], p["impressions"] if p else 0) < min_impressions:
            continue
        out.append({
            key: r[key],
            "clicks": r["clicks"], "clicks_prev": p["clicks"] if p else 0,
            "clicks_delta": r["clicks"] - (p["clicks"] if p else 0),
            "impressions": r["impressions"],
            "impressions_delta": r["impressions"] - (p["impressions"] if p else 0),
            "position": r["position"],
            # Position: LOWER is better, so improvement is prev - current.
            "position_delta": round((p["position"] - r["position"]), 2) if p else None,
            "is_new": p is None, "is_lost": False,
        })
    seen = {r[key] for r in current}
    for k, p in prev.items():
        if k in seen or p["impressions"] < min_impressions:
            continue
        out.append({
            key: k, "clicks": 0, "clicks_prev": p["clicks"],
            "clicks_delta": -p["clicks"],
            "impressions": 0, "impressions_delta": -p["impressions"],
            "position": p["position"], "position_delta": None,
            "is_new": False, "is_lost": True,
        })
    return sorted(out, key=lambda r: r["clicks_delta"], reverse=True)


# Rough organic CTR-by-position curve. A heuristic for spotting underperformers,
# not a promise — real CTR varies hugely by SERP features and intent.
_CTR_CURVE = {1: .28, 2: .15, 3: .11, 4: .08, 5: .06, 6: .05,
              7: .04, 8: .033, 9: .028, 10: .025}


def expected_ctr(position):
    if position <= 0:
        return 0.0
    p = int(round(position))
    if p in _CTR_CURVE:
        return _CTR_CURVE[p]
    if p < 1:
        return _CTR_CURVE[1]
    return max(0.002, 0.025 * (10.0 / p) ** 1.2)   # decay past page one


def striking_distance(recs, key="query", min_impressions=20, lo=4.0, hi=20.0, n=25):
    """Queries ranking 4-20 with real impressions: the cheapest wins available.
    `upside` = clicks/period if the page reached position 3."""
    out = []
    for r in recs:
        if r["impressions"] < min_impressions or not (lo <= r["position"] <= hi):
            continue
        upside = r["impressions"] * (_CTR_CURVE[3] - r["ctr"])
        if upside <= 0:
            continue
        out.append(dict(r, upside_clicks=round(upside, 1)))
    return sorted(out, key=lambda r: r["upside_clicks"], reverse=True)[:n]


def ctr_gaps(recs, key="query", min_impressions=50, n=25):
    """Ranking well but under-clicked vs the position curve — a title/meta problem,
    not a ranking problem."""
    out = []
    for r in recs:
        if r["impressions"] < min_impressions or r["position"] > 10:
            continue
        exp = expected_ctr(r["position"])
        if r["ctr"] >= exp * 0.75:
            continue
        out.append(dict(r, expected_ctr=round(exp, 4),
                        missed_clicks=round((exp - r["ctr"]) * r["impressions"], 1)))
    return sorted(out, key=lambda r: r["missed_clicks"], reverse=True)[:n]


def city_of(page_or_query):
    """Longest-match city slug in a URL path or query string."""
    s = (page_or_query or "").lower()
    hay = s.replace(" ", "-")
    best = ""
    for city in CITY_COUNTY:
        if city in hay and len(city) > len(best):
            best = city
    return best


def by_city(recs, key="page"):
    agg = {}
    for r in recs:
        city = city_of(r.get(key, ""))
        if not city:
            continue
        d = agg.setdefault(city, {"city": city, "county": CITY_COUNTY[city],
                                  "clicks": 0, "impressions": 0, "_pos_w": 0.0})
        d["clicks"] += r["clicks"]
        d["impressions"] += r["impressions"]
        d["_pos_w"] += r["position"] * r["impressions"]
    for d in agg.values():
        d["position"] = round(d["_pos_w"] / d["impressions"], 2) if d["impressions"] else 0.0
        d["ctr"] = round(d["clicks"] / d["impressions"], 6) if d["impressions"] else 0.0
        d.pop("_pos_w")
    return sorted(agg.values(), key=lambda d: d["impressions"], reverse=True)


def by_county(recs, key="page"):
    agg = {}
    for d in by_city(recs, key=key):
        c = agg.setdefault(d["county"], {"county": d["county"], "clicks": 0,
                                         "impressions": 0, "_pos_w": 0.0, "cities": 0})
        c["clicks"] += d["clicks"]
        c["impressions"] += d["impressions"]
        c["_pos_w"] += d["position"] * d["impressions"]
        c["cities"] += 1
    for c in agg.values():
        c["position"] = round(c["_pos_w"] / c["impressions"], 2) if c["impressions"] else 0.0
        c.pop("_pos_w")
    return sorted(agg.values(), key=lambda c: c["impressions"], reverse=True)


def cross_permits(county_rows, permit_counts):
    """Search demand vs real permit volume, per county. `permit_counts` is
    {county: n} (e.g. from the permits engine CSV export). Counties with permit
    activity but no landing-page impressions are flagged as coverage gaps."""
    seen = {c["county"]: c for c in county_rows}
    out = []
    for county in COUNTIES:
        g = seen.get(county, {"clicks": 0, "impressions": 0, "position": 0.0, "cities": 0})
        permits = int(permit_counts.get(county, 0) or 0)
        out.append({
            "county": county,
            "permits": permits,
            "clicks": g.get("clicks", 0),
            "impressions": g.get("impressions", 0),
            "position": g.get("position", 0.0),
            "city_pages": g.get("cities", 0),
            # impressions earned per permit issued: low = under-covered market
            "impr_per_permit": round(g.get("impressions", 0) / permits, 2) if permits else None,
            "gap": permits > 0 and g.get("impressions", 0) == 0,
        })
    return sorted(out, key=lambda r: r["permits"], reverse=True)


def permit_counts_from_csv(text):
    """County -> permit count from the permits dashboard CSV export."""
    counts = {}
    for row in csv.DictReader(io.StringIO(text or "")):
        county = (row.get("county") or row.get("County") or "").strip()
        if county:
            counts[county] = counts.get(county, 0) + 1
    return counts


# --------------------------------------------------------------- output -----
def date_range(days, end=None, lag=DATA_LAG_DAYS):
    """(start, end) ending `lag` days back so only finalized data is reported."""
    end = end or (date.today() - timedelta(days=lag))
    return end - timedelta(days=days - 1), end


def previous_range(start, end):
    span = (end - start).days + 1
    return start - timedelta(days=span), start - timedelta(days=1)


def to_csv(recs, columns=None):
    if not recs:
        return ""
    columns = columns or list(recs[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    w.writeheader()
    for r in recs:
        w.writerow(r)
    return buf.getvalue()


def _pct(x):
    return f"{x * 100:.1f}%"


def render_report(site, start, end, data):
    """Markdown report. `data` carries the analysed slices (see _gsc_pull.py)."""
    t, tp = data["totals"], data.get("totals_prev")
    L = [f"# Search Console — {site}",
         f"**{start} → {end}** · generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
         "",
         "## Totals",
         "| Metric | This period | Previous | Change |",
         "|---|---|---|---|"]
    for label, k, fmt in (("Clicks", "clicks", str), ("Impressions", "impressions", str),
                          ("CTR", "ctr", _pct), ("Avg position", "position", str)):
        cur = t[k]
        if tp:
            prev = tp[k]
            delta = cur - prev
            # position improves downward
            arrow = "→" if delta == 0 else ("↑" if (delta > 0) != (k == "position") else "↓")
            L.append(f"| {label} | {fmt(cur)} | {fmt(prev)} | {arrow} {fmt(abs(delta)) if k == 'ctr' else round(abs(delta), 2)} |")
        else:
            L.append(f"| {label} | {fmt(cur)} | — | — |")

    def table(title, rows, cols, note=""):
        L.extend(["", f"## {title}"])
        if note:
            L.append(f"*{note}*")
        if not rows:
            L.append("_(none)_")
            return
        L.append("| " + " | ".join(h for h, _ in cols) + " |")
        L.append("|" + "|".join("---" for _ in cols) + "|")
        for r in rows:
            L.append("| " + " | ".join(str(f(r)) for _, f in cols) + " |")

    table("Top queries", data.get("top_queries", [])[:15],
          [("Query", lambda r: r["query"]), ("Clicks", lambda r: r["clicks"]),
           ("Impr", lambda r: r["impressions"]), ("CTR", lambda r: _pct(r["ctr"])),
           ("Pos", lambda r: r["position"])])
    table("Top pages", data.get("top_pages", [])[:15],
          [("Page", lambda r: r["page"]), ("Clicks", lambda r: r["clicks"]),
           ("Impr", lambda r: r["impressions"]), ("Pos", lambda r: r["position"])])
    table("Striking distance (positions 4–20)", data.get("striking", [])[:15],
          [("Query", lambda r: r["query"]), ("Pos", lambda r: r["position"]),
           ("Impr", lambda r: r["impressions"]),
           ("Upside clicks", lambda r: r["upside_clicks"])],
          "Ranking just off the money. Cheapest wins available — one section or "
          "internal link often moves these.")
    table("CTR gaps (top-10 but under-clicked)", data.get("ctr_gaps", [])[:10],
          [("Query", lambda r: r["query"]), ("Pos", lambda r: r["position"]),
           ("CTR", lambda r: _pct(r["ctr"])), ("Expected", lambda r: _pct(r["expected_ctr"])),
           ("Missed", lambda r: r["missed_clicks"])],
          "Title/meta-description problem, not a ranking problem.")
    def movement(r):
        if r.get("is_new"):
            return "new"
        if r.get("is_lost"):
            return "dropped out"
        return r["position_delta"] if r["position_delta"] is not None else "—"

    table("Biggest gainers", [r for r in data.get("movers", []) if r["clicks_delta"] > 0][:10],
          [("Query", lambda r: r["query"]), ("Clicks", lambda r: r["clicks"]),
           ("Δ Clicks", lambda r: f"+{r['clicks_delta']}"), ("Δ Pos", movement)])
    table("Biggest losers", sorted([r for r in data.get("movers", []) if r["clicks_delta"] < 0],
                                   key=lambda r: r["clicks_delta"])[:10],
          [("Query", lambda r: r["query"]), ("Clicks", lambda r: r["clicks"]),
           ("Δ Clicks", lambda r: r["clicks_delta"]), ("Δ Pos", movement)],
          "Includes queries that vanished from the results entirely.")
    table("City pages", data.get("cities", []),
          [("City", lambda r: r["city"]), ("County", lambda r: r["county"]),
           ("Clicks", lambda r: r["clicks"]), ("Impr", lambda r: r["impressions"]),
           ("Pos", lambda r: r["position"])])
    if data.get("permits"):
        table("Search demand vs permit volume", data["permits"],
              [("County", lambda r: r["county"]), ("Permits", lambda r: r["permits"]),
               ("Impr", lambda r: r["impressions"]), ("Clicks", lambda r: r["clicks"]),
               ("City pages", lambda r: r["city_pages"]),
               ("Impr/permit", lambda r: r["impr_per_permit"] if r["impr_per_permit"] is not None else "—"),
               ("Gap", lambda r: "⚠️ no coverage" if r["gap"] else "")],
              "Where real construction activity isn't matched by search presence.")
    L.extend(["", "---",
              f"_Data ends {end} ({DATA_LAG_DAYS}-day finalization lag). "
              "Position is impression-weighted. CTR curve is a heuristic._"])
    return "\n".join(L)
