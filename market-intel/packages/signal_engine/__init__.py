"""Signal engine.

A signal is a *registered definition* plus a compute function, never logic
buried in a UI component. Adding one means writing a `SignalDef` and a
function that returns observations — the API, scoring and alerts pick it up
automatically.

Every observation stores:
  raw_value        the number in its own units
  normalized_value 0..1 within its own cross-section
  zscore / percentile  cross-sectional standing on that date
  ingested_at      when it BECAME COMPUTABLE — the only field a backtest may
                   filter on. observed_at is the period it describes and is
                   knowable only in hindsight.
  evidence         JSON pointing at the source records behind it

Nothing here claims predictive power. These are measurements; whether any of
them forecasts returns is an empirical question the scoring backtest must
answer (see docs/SIGNAL_ENGINE.md).
"""
import json
import statistics
from dataclasses import dataclass, field
from typing import Callable

from packages.database import repositories as repo
from packages.shared.timeutil import iso, now_utc

REGISTRY = {}


@dataclass
class SignalDef:
    id: str
    name: str
    description: str
    category: str                      # fundamental|alt|flow|technical|text
    direction: str = "higher_is_bullish"
    version: int = 1
    params: dict = field(default_factory=dict)
    compute: Callable = None

    def register(self):
        REGISTRY[self.id] = self
        return self


def signal(**kwargs):
    """Decorator: turn a compute function into a registered signal."""
    def wrap(fn):
        SignalDef(compute=fn, **kwargs).register()
        return fn
    return wrap


def sync_definitions(db):
    for s in REGISTRY.values():
        repo.upsert_signal_def(db, signal_id=s.id, name=s.name, description=s.description,
                               category=s.category, direction=s.direction,
                               version=s.version, definition=s.params)
    db.commit()
    return len(REGISTRY)


# ------------------------------------------------------------------ maths ---
def pct_change(current, previous):
    if previous in (None, 0) or current is None:
        return None
    return (current - previous) / abs(previous)


def zscores(values):
    """Cross-sectional z-scores. Returns zeros when the sample is too small or
    degenerate rather than dividing by ~0 and emitting nonsense."""
    clean = [v for v in values if v is not None]
    if len(clean) < 3:
        return [0.0 for _ in values]
    mu = statistics.fmean(clean)
    sd = statistics.pstdev(clean)
    if sd < 1e-12:
        return [0.0 for _ in values]
    return [None if v is None else (v - mu) / sd for v in values]


def percentiles(values):
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return [None for _ in values]
    out = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        below = sum(1 for c in clean if c < v)
        out.append(round(below / len(clean), 4))
    return out


def squash(z):
    """z-score -> 0..1 without the tails saturating the whole scale."""
    if z is None:
        return None
    return round(1.0 / (1.0 + pow(2.718281828, -z)), 4)


# ---------------------------------------------------------------- signals ---
@signal(id="topic_acceleration", name="Topic Acceleration",
        description="Growth in mentions of a tag by an entity vs its own trailing "
                    "baseline. The core alternative-data primitive.",
        category="text", params={"lookback_periods": 3, "min_mentions": 3})
def topic_acceleration(db, entity_id, tag_id=None, bucket="month", **_):
    """Per-tag acceleration for one entity. Compares the latest period against
    the mean of the prior N — so a jump from 3 to 41 mentions registers."""
    from packages.tag_engine import tag_timeseries

    tag_ids = ([tag_id] if tag_id else
               [r["tag_id"] for r in db.query(
                   "SELECT DISTINCT tag_id FROM entity_tags WHERE entity_id=?",
                   (entity_id,))])
    out = []
    for tid in tag_ids:
        series = tag_timeseries(db, entity_id, tid, bucket=bucket)
        if len(series) < 2:
            continue
        latest = series[-1]
        prior = series[-4:-1] or series[:-1]
        base = statistics.fmean([p["mentions"] for p in prior]) if prior else 0
        if latest["mentions"] < 3 and base < 3:
            continue   # too thin to mean anything
        change = pct_change(latest["mentions"], base)
        if change is None:
            continue
        out.append({
            "entity_id": entity_id, "tag_id": tid,
            "observed_at": latest["period"],
            "raw_value": round(change, 4),
            "detail": {"latest": latest["mentions"], "baseline": round(base, 2),
                       "periods": len(series)},
        })
    return out


def _quarterly(rows, max_days=110):
    """Keep only ~quarterly durations. Mixing annual totals into a quarterly
    series is the classic way to manufacture a fake 300% 'acceleration'."""
    from packages.shared.timeutil import parse_date

    out = []
    for r in rows:
        start, end = parse_date(r.get("period_start")), parse_date(r.get("period_end"))
        if not start or not end:
            continue
        days = (end - start).days
        if 60 <= days <= max_days:
            out.append(dict(r, days=days))
    return out


@signal(id="revenue_acceleration", name="Revenue Acceleration",
        description="Change in the quarter-over-quarter revenue growth RATE — the "
                    "second derivative, not growth itself.",
        category="fundamental", params={"min_quarters": 3})
def revenue_acceleration(db, entity_id, **_):
    from collectors.sec.edgar import REVENUE_CONCEPTS

    rows = []
    for concept in REVENUE_CONCEPTS:
        rows = db.query(
            "SELECT period_start, period_end, value, fiscal_year, fiscal_period, "
            "filed_at, source_record_id FROM filing_facts WHERE entity_id=? AND "
            "concept=? AND unit='USD' ORDER BY period_end", (entity_id, concept))
        if rows:
            break
    q = _quarterly(rows)
    if len(q) < 3:
        return []
    latest, prev, prev2 = q[-1], q[-2], q[-3]
    g1 = pct_change(latest["value"], prev["value"])
    g0 = pct_change(prev["value"], prev2["value"])
    if g1 is None or g0 is None:
        return []
    return [{
        "entity_id": entity_id,
        "observed_at": latest["period_end"],
        # ingested_at defaults to now, but the honest "knowable from" date is
        # the filing date — that is what a backtest must respect.
        "knowable_at": latest.get("filed_at") or latest["period_end"],
        "raw_value": round(g1 - g0, 4),
        "detail": {"growth_latest": round(g1, 4), "growth_prior": round(g0, 4),
                   "revenue_latest": latest["value"], "quarters": len(q)},
        "source_record_ids": [latest.get("source_record_id")],
    }]


@signal(id="margin_expansion", name="Margin Expansion",
        description="Change in gross margin vs the prior quarter.",
        category="fundamental")
def margin_expansion(db, entity_id, **_):
    from collectors.sec.edgar import REVENUE_CONCEPTS

    gross = _quarterly(db.query(
        "SELECT period_start, period_end, value, filed_at, source_record_id "
        "FROM filing_facts WHERE entity_id=? AND concept='GrossProfit' AND unit='USD' "
        "ORDER BY period_end", (entity_id,)))
    revenue = []
    for concept in REVENUE_CONCEPTS:
        revenue = _quarterly(db.query(
            "SELECT period_start, period_end, value FROM filing_facts WHERE entity_id=? "
            "AND concept=? AND unit='USD' ORDER BY period_end", (entity_id, concept)))
        if revenue:
            break
    rev_by_end = {r["period_end"]: r["value"] for r in revenue}
    margins = [(g["period_end"], g["value"] / rev_by_end[g["period_end"]], g)
               for g in gross
               if rev_by_end.get(g["period_end"])]
    if len(margins) < 2:
        return []
    (end, m1, g), (_, m0, _p) = margins[-1], margins[-2]
    return [{
        "entity_id": entity_id, "observed_at": end,
        "knowable_at": g.get("filed_at") or end,
        "raw_value": round(m1 - m0, 5),
        "detail": {"margin_latest": round(m1, 4), "margin_prior": round(m0, 4)},
        "source_record_ids": [g.get("source_record_id")],
    }]


@signal(id="filing_velocity", name="Filing Velocity",
        description="8-K filings in the trailing 90 days vs the prior 90 — a proxy "
                    "for corporate event intensity.",
        category="flow", params={"window_days": 90, "form": "8-K"})
def filing_velocity(db, entity_id, as_of=None, **_):
    from datetime import timedelta

    from packages.shared.timeutil import parse_date

    rows = db.query("SELECT filed_at, source_record_id FROM sec_filings "
                    "WHERE entity_id=? AND form='8-K' ORDER BY filed_at", (entity_id,))
    if not rows:
        return []
    dates = [parse_date(r["filed_at"]) for r in rows if r.get("filed_at")]
    if not dates:
        return []
    anchor = parse_date(as_of) if as_of else max(dates)
    recent = sum(1 for d in dates if anchor - timedelta(days=90) <= d <= anchor)
    prior = sum(1 for d in dates
                if anchor - timedelta(days=180) <= d < anchor - timedelta(days=90))
    return [{
        "entity_id": entity_id, "observed_at": anchor.isoformat(),
        "knowable_at": anchor.isoformat(),
        "raw_value": float(recent - prior),
        "detail": {"recent_90d": recent, "prior_90d": prior},
        "source_record_ids": [r.get("source_record_id") for r in rows[:5]],
    }]


# -------------------------------------------------------------- execution ---
def compute_for_entities(db, signal_id, entity_ids, **kwargs):
    """Run one signal across a cross-section, then z-score/percentile WITHIN
    that cross-section so values are comparable between companies."""
    sig = REGISTRY[signal_id]
    produced = []
    for eid in entity_ids:
        try:
            produced.extend(sig.compute(db, eid, **kwargs) or [])
        except Exception as e:                       # one bad entity != dead run
            produced.append({"entity_id": eid, "error": f"{type(e).__name__}: {e}"})
    good = [p for p in produced if "error" not in p]
    values = [p["raw_value"] for p in good]
    zs, ps = zscores(values), percentiles(values)
    now = iso(now_utc())
    for p, z, pct in zip(good, zs, ps):
        p["zscore"] = None if z is None else round(z, 4)
        p["percentile"] = pct
        p["normalized_value"] = squash(z)
        p["signal_id"] = sig.id
        p["signal_version"] = sig.version
        p["ingested_at"] = p.get("knowable_at") or now
    return good, [p for p in produced if "error" in p]


def persist(db, observations):
    for o in observations:
        repo.record_signal_observation(db, {
            "signal_id": o["signal_id"], "entity_id": o["entity_id"],
            "subject_id": o.get("tag_id") or "",
            "observed_at": str(o["observed_at"]), "ingested_at": o["ingested_at"],
            "raw_value": o.get("raw_value"),
            "normalized_value": o.get("normalized_value"),
            "zscore": o.get("zscore"), "percentile": o.get("percentile"),
            "confidence": o.get("confidence", 1.0),
            "signal_version": o.get("signal_version", 1),
            "evidence": json.dumps({"detail": o.get("detail"),
                                    "source_record_ids": o.get("source_record_ids", []),
                                    "tag_id": o.get("tag_id")}),
        })
    db.commit()
    return len(observations)


def latest_for_entity(db, entity_id):
    return db.query(
        "SELECT so.*, s.name, s.category, s.direction FROM signal_observations so "
        "JOIN signals s ON s.id = so.signal_id WHERE so.entity_id = ? "
        "AND so.observed_at = (SELECT MAX(observed_at) FROM signal_observations "
        "                      WHERE signal_id = so.signal_id AND entity_id = so.entity_id "
        "                        AND subject_id = so.subject_id) "
        "ORDER BY s.category, s.name", (entity_id,))
