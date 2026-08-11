"""API handlers — framework-agnostic.

Each handler is `(db, params) -> (status_code, payload)` with no web framework
in sight. That keeps them unit-testable without spinning up a server, and lets
the same logic serve both the stdlib dev server (`server.py`, runs anywhere)
and the FastAPI app (`fastapi_app.py`, the production target). Adding a
framework later never means rewriting business logic.

Every response that carries a derived number also carries its provenance —
`sources`, `evidence`, or `as_of` — because an unsourced number on this
platform is a bug.
"""
import json

from packages.entity_resolution import EntityResolver
from packages.scoring_engine import score_entity
from packages.signal_engine import latest_for_entity
from packages.tag_engine import entities_for_tag, tag_timeseries, top_tags
from packages.tag_engine.taxonomy import tag_path
from pipelines.enrichment.filing_diff import diffs_for_entity

API_VERSION = "v1"


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _entity_for_ticker(db, ticker):
    row = db.one(
        "SELECT e.* FROM entities e JOIN entity_identifiers i ON i.entity_id = e.id "
        "WHERE i.scheme='ticker' AND i.value_norm=? LIMIT 1",
        (str(ticker).strip().lower().lstrip("0") or "0",))
    if not row:
        raise ApiError(404, f"unknown ticker '{ticker}'")
    return row


def _demo_flags(db, entity_id):
    """Surface whether the underlying records are DEMO fixtures. The UI must be
    able to say so; presenting fixture data as live is forbidden (see §39)."""
    n = db.scalar(
        "SELECT COUNT(*) FROM source_records WHERE payload LIKE '%\"_demo\":true%' "
        "OR payload LIKE '%DEMO FIXTURE%'") or 0
    total = db.scalar("SELECT COUNT(*) FROM source_records") or 0
    return {"demo_records": n, "total_records": total, "contains_demo_data": n > 0}


# ------------------------------------------------------------------ system --
def health(db, params=None):
    counts = {t: db.scalar(f"SELECT COUNT(*) FROM {t}") for t in
              ("entities", "source_records", "sec_filings", "filing_facts",
               "entity_tags", "signal_observations", "scores")}
    return 200, {"status": "ok", "version": API_VERSION, "counts": counts,
                 "data": _demo_flags(db, None)}


def data_health(db, params=None):
    """Collector freshness + reject rates — the internal data-health view."""
    runs = db.query(
        "SELECT source_id, collector, MAX(started_at) AS last_run, status, "
        "records_fetched, records_written, records_rejected, error "
        "FROM ingestion_runs GROUP BY source_id, collector ORDER BY last_run DESC")
    sources = db.query("SELECT id, name, category, license_class, enabled FROM data_sources")
    pending = db.scalar("SELECT COUNT(*) FROM resolution_candidates WHERE status='pending'")
    return 200, {"sources": sources, "collectors": runs,
                 "pending_entity_reviews": pending}


def search(db, params):
    q = (params.get("q") or "").strip()
    if len(q) < 1:
        raise ApiError(400, "q is required")
    like = f"%{q.lower()}%"
    entities = db.query(
        "SELECT DISTINCT e.id, e.name, e.type, "
        "(SELECT value FROM entity_identifiers WHERE entity_id=e.id AND scheme='ticker' "
        " LIMIT 1) AS ticker FROM entities e "
        "LEFT JOIN entity_aliases a ON a.entity_id = e.id "
        "WHERE lower(e.name) LIKE ? OR a.alias_norm LIKE ? LIMIT 20", (like, like))
    tags = db.query("SELECT id, name, slug, category FROM tags WHERE lower(name) LIKE ? "
                    "LIMIT 20", (like,))
    return 200, {"query": q, "entities": entities, "tags": tags}


# ------------------------------------------------------------------ stocks --
def list_stocks(db, params):
    limit = min(int(params.get("limit", 50)), 500)
    rows = db.query(
        "SELECT e.id AS entity_id, e.name, s.ticker, s.exchange, "
        "(SELECT composite FROM scores WHERE entity_id=e.id ORDER BY as_of DESC LIMIT 1) "
        " AS composite FROM securities s JOIN entities e ON e.id = s.entity_id "
        "WHERE s.active=1 ORDER BY s.ticker LIMIT ?", (limit,))
    return 200, {"count": len(rows), "stocks": rows}


def stock_detail(db, params):
    e = _entity_for_ticker(db, params["ticker"])
    ident = db.query("SELECT scheme, value FROM entity_identifiers WHERE entity_id=?",
                     (e["id"],))
    sec = db.one("SELECT ticker, exchange, currency FROM securities WHERE entity_id=? "
                 "LIMIT 1", (e["id"],))
    aliases = db.query("SELECT alias, kind FROM entity_aliases WHERE entity_id=?", (e["id"],))
    latest_filing = db.one("SELECT form, filed_at, period_end, doc_url FROM sec_filings "
                           "WHERE entity_id=? ORDER BY filed_at DESC LIMIT 1", (e["id"],))
    return 200, {"entity": e, "security": sec,
                 "identifiers": {i["scheme"]: i["value"] for i in ident},
                 "aliases": aliases, "latest_filing": latest_filing,
                 "data": _demo_flags(db, e["id"])}


def stock_financials(db, params):
    """Quarterly series per concept, straight from XBRL facts with lineage."""
    e = _entity_for_ticker(db, params["ticker"])
    rows = db.query(
        "SELECT concept, unit, period_start, period_end, value, fiscal_year, "
        "fiscal_period, form, filed_at, source_record_id FROM filing_facts "
        "WHERE entity_id=? ORDER BY concept, period_end", (e["id"],))
    series = {}
    for r in rows:
        series.setdefault(r["concept"], []).append(r)
    return 200, {"ticker": params["ticker"].upper(), "entity_id": e["id"],
                 "concepts": sorted(series), "series": series,
                 "provenance": "SEC XBRL companyfacts"}


def stock_filings(db, params):
    e = _entity_for_ticker(db, params["ticker"])
    limit = min(int(params.get("limit", 50)), 200)
    rows = db.query(
        "SELECT id, form, filed_at, period_end, accession_no, doc_url, items "
        "FROM sec_filings WHERE entity_id=? ORDER BY filed_at DESC LIMIT ?",
        (e["id"], limit))
    return 200, {"ticker": params["ticker"].upper(), "count": len(rows), "filings": rows}


def stock_filing_changes(db, params):
    """What changed vs the prior comparable filing — the SEC-intelligence view."""
    e = _entity_for_ticker(db, params["ticker"])
    rows = diffs_for_entity(db, e["id"], limit=int(params.get("limit", 100)))
    grouped = {}
    for r in rows:
        grouped.setdefault(r["section"], {"added": [], "removed": [], "modified": []})
        grouped[r["section"]][r["change_type"]].append(
            {"excerpt": r["excerpt"], "similarity": r["similarity"],
             "form": r["form"], "filed_at": r["filed_at"]})
    return 200, {"ticker": params["ticker"].upper(), "sections": grouped,
                 "total_changes": len(rows)}


def stock_tags(db, params):
    e = _entity_for_ticker(db, params["ticker"])
    tags = top_tags(db, e["id"], limit=int(params.get("limit", 25)))
    for t in tags:
        t["path"] = tag_path(db, t["tag_id"])
        t["timeseries"] = tag_timeseries(db, e["id"], t["tag_id"], bucket="month")
    return 200, {"ticker": params["ticker"].upper(), "count": len(tags), "tags": tags}


def stock_signals(db, params):
    e = _entity_for_ticker(db, params["ticker"])
    rows = latest_for_entity(db, e["id"])
    for r in rows:
        if r.get("evidence"):
            try:
                r["evidence"] = json.loads(r["evidence"])
            except json.JSONDecodeError:
                pass
    return 200, {"ticker": params["ticker"].upper(), "count": len(rows), "signals": rows}


def stock_score(db, params):
    e = _entity_for_ticker(db, params["ticker"])
    stored = db.one("SELECT * FROM scores WHERE entity_id=? ORDER BY as_of DESC LIMIT 1",
                    (e["id"],))
    live = score_entity(db, e["id"])
    if stored and stored.get("categories"):
        try:
            stored["categories"] = json.loads(stored["categories"])
        except json.JSONDecodeError:
            pass
    return 200, {"ticker": params["ticker"].upper(), "stored": stored, "computed": live,
                 "disclaimer": "Composite weights are a v1 prior and have NOT been "
                               "backtested. `coverage` shows how much of the model "
                               "actually had data."}


def stock_relationships(db, params):
    e = _entity_for_ticker(db, params["ticker"])
    rows = db.query(
        "SELECT r.type, r.confidence, r.observation_count, r.first_seen_at, "
        "r.last_seen_at, e2.id AS other_id, e2.name AS other_name, e2.type AS other_type "
        "FROM relationships r JOIN entities e2 ON e2.id = r.to_entity_id "
        "WHERE r.from_entity_id=? ORDER BY r.confidence DESC", (e["id"],))
    return 200, {"ticker": params["ticker"].upper(), "count": len(rows),
                 "relationships": rows}


# ------------------------------------------------------------------ themes --
def list_themes(db, params):
    rows = db.query(
        "SELECT t.id, t.name, t.slug, t.category, t.parent_id, "
        "COALESCE(SUM(et.frequency),0) AS mentions, "
        "COUNT(DISTINCT et.entity_id) AS entities "
        "FROM tags t LEFT JOIN entity_tags et ON et.tag_id = t.id "
        "GROUP BY t.id ORDER BY mentions DESC, t.name")
    return 200, {"count": len(rows), "themes": rows}


def theme_detail(db, params):
    slug = params["slug"]
    tag = db.one("SELECT * FROM tags WHERE slug=?", (slug,))
    if not tag:
        raise ApiError(404, f"unknown theme '{slug}'")
    return 200, {"theme": tag, "path": tag_path(db, tag["id"]),
                 "entities": entities_for_tag(db, tag["id"], limit=50)}


def list_signals(db, params):
    return 200, {"signals": db.query(
        "SELECT s.*, (SELECT COUNT(*) FROM signal_observations WHERE signal_id=s.id) "
        "AS observations FROM signals s ORDER BY s.category, s.name")}


def screener(db, params):
    """Filter the cross-section. Every filter is optional; unknown params are
    rejected rather than silently ignored."""
    allowed = {"min_score", "max_score", "tag", "signal", "min_zscore", "limit"}
    unknown = set(params) - allowed - {"ticker", "slug"}
    if unknown:
        raise ApiError(400, f"unknown filter(s): {', '.join(sorted(unknown))}")
    where, args = ["1=1"], []
    sql = ("SELECT e.id AS entity_id, e.name, "
           "(SELECT value FROM entity_identifiers WHERE entity_id=e.id AND scheme='ticker' "
           " LIMIT 1) AS ticker, "
           "(SELECT composite FROM scores WHERE entity_id=e.id ORDER BY as_of DESC LIMIT 1) "
           " AS composite FROM entities e WHERE e.type='PUBLIC_COMPANY'")
    if params.get("tag"):
        sql += (" AND EXISTS (SELECT 1 FROM entity_tags et JOIN tags t ON t.id=et.tag_id "
                "WHERE et.entity_id=e.id AND t.slug=?)")
        args.append(params["tag"])
    if params.get("signal"):
        sql += (" AND EXISTS (SELECT 1 FROM signal_observations so WHERE so.entity_id=e.id "
                "AND so.signal_id=?" + (" AND so.zscore >= ?" if params.get("min_zscore")
                                        else "") + ")")
        args.append(params["signal"])
        if params.get("min_zscore"):
            args.append(float(params["min_zscore"]))
    rows = db.query(sql + " ORDER BY composite DESC NULLS LAST LIMIT ?",
                    tuple(args) + (min(int(params.get("limit", 50)), 200),))
    if params.get("min_score"):
        rows = [r for r in rows if (r["composite"] or 0) >= float(params["min_score"])]
    if params.get("max_score"):
        rows = [r for r in rows if (r["composite"] or 0) <= float(params["max_score"])]
    return 200, {"count": len(rows), "results": rows, "filters": params}


ROUTES = [
    ("GET", r"^/api/v1/health$", health),
    ("GET", r"^/api/v1/data-health$", data_health),
    ("GET", r"^/api/v1/search$", search),
    ("GET", r"^/api/v1/stocks$", list_stocks),
    ("GET", r"^/api/v1/stocks/(?P<ticker>[A-Za-z.\-]+)$", stock_detail),
    ("GET", r"^/api/v1/stocks/(?P<ticker>[A-Za-z.\-]+)/financials$", stock_financials),
    ("GET", r"^/api/v1/stocks/(?P<ticker>[A-Za-z.\-]+)/filings$", stock_filings),
    ("GET", r"^/api/v1/stocks/(?P<ticker>[A-Za-z.\-]+)/filing-changes$",
     stock_filing_changes),
    ("GET", r"^/api/v1/stocks/(?P<ticker>[A-Za-z.\-]+)/tags$", stock_tags),
    ("GET", r"^/api/v1/stocks/(?P<ticker>[A-Za-z.\-]+)/signals$", stock_signals),
    ("GET", r"^/api/v1/stocks/(?P<ticker>[A-Za-z.\-]+)/score$", stock_score),
    ("GET", r"^/api/v1/stocks/(?P<ticker>[A-Za-z.\-]+)/relationships$",
     stock_relationships),
    ("GET", r"^/api/v1/themes$", list_themes),
    ("GET", r"^/api/v1/themes/(?P<slug>[a-z0-9\-]+)$", theme_detail),
    ("GET", r"^/api/v1/signals$", list_signals),
    ("GET", r"^/api/v1/screener$", screener),
]


def dispatch(db, method, path, params=None):
    """Route -> handler. Returns (status, payload) and never raises to callers."""
    import re
    params = dict(params or {})
    for verb, pattern, fn in ROUTES:
        if verb != method:
            continue
        m = re.match(pattern, path)
        if m:
            params.update(m.groupdict())
            try:
                return fn(db, params)
            except ApiError as e:
                return e.status, {"error": e.message}
            except Exception as e:
                return 500, {"error": f"{type(e).__name__}: {e}"}
    return 404, {"error": f"no route for {method} {path}"}
