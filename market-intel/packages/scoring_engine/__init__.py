"""Composite scoring — explicitly a FRAMEWORK, not a validated alpha model.

The v1 weights below are a reasonable prior, nothing more. They have not been
backtested and must not be presented to a user as if they were. Two properties
make that honest rather than hand-wavy:

  1. Weights are stored as a VERSIONED model row, so a future backtest can
     compare v1 against v2 on identical history.
  2. Every score carries `coverage` — the share of its inputs that actually had
     data. A 78 built from one signal is not a 78 built from eight, and the UI
     shows the difference instead of hiding it.
"""
import json

from packages.database import repositories as repo
from packages.shared.timeutil import iso, now_utc

MODEL_ID = "composite"
MODEL_VERSION = 1

# category -> (weight, [signal ids])
WEIGHTS = {
    "fundamental_quality": (0.15, []),
    "growth":              (0.20, ["revenue_acceleration"]),
    "earnings_momentum":   (0.15, ["margin_expansion"]),
    "insider_activity":    (0.10, []),
    "institutional":       (0.10, []),
    "alt_data_momentum":   (0.20, ["topic_acceleration"]),
    "news_sentiment":      (0.05, []),
    "technical":           (0.05, ["filing_velocity"]),
}


def register_model(db):
    db.upsert("score_models", {
        "id": MODEL_ID, "version": MODEL_VERSION,
        "weights": json.dumps({k: v[0] for k, v in WEIGHTS.items()}),
        "created_at": iso(now_utc()),
        "notes": "v1 prior — NOT backtested. Weights are a starting point for "
                 "comparison against future versions.",
    }, ["id", "version"])
    db.commit()


def score_entity(db, entity_id, as_of=None):
    """Blend the latest normalized signal values into 0..100 by category.

    Categories with no data are EXCLUDED and their weight redistributed, rather
    than scored as zero — a missing input is ignorance, not a bad reading.
    """
    from packages.signal_engine import latest_for_entity

    latest = {r["signal_id"]: r for r in latest_for_entity(db, entity_id)}
    as_of = as_of or max([r["observed_at"] for r in latest.values()], default=None) \
        or iso(now_utc())[:10]

    categories, used_weight, inputs_possible, inputs_present = {}, 0.0, 0, 0
    for cat, (weight, signal_ids) in WEIGHTS.items():
        vals = []
        for sid in signal_ids:
            inputs_possible += 1
            row = latest.get(sid)
            if row and row.get("normalized_value") is not None:
                inputs_present += 1
                v = row["normalized_value"]
                # A bearish-direction signal is inverted before blending.
                if row.get("direction") == "higher_is_bearish":
                    v = 1.0 - v
                vals.append(v)
        if not vals:
            categories[cat] = None          # explicit "no data", not 0
            continue
        cat_score = sum(vals) / len(vals)
        categories[cat] = round(cat_score * 100, 1)
        used_weight += weight

    if used_weight <= 0:
        composite = None
    else:
        composite = round(sum(
            (categories[c] or 0) * (w / used_weight)
            for c, (w, _s) in WEIGHTS.items() if categories.get(c) is not None), 1)

    coverage = round(inputs_present / inputs_possible, 4) if inputs_possible else 0.0
    return {"entity_id": entity_id, "as_of": str(as_of)[:10], "composite": composite,
            "categories": categories, "coverage": coverage,
            "model_id": MODEL_ID, "model_version": MODEL_VERSION}


def persist_score(db, score):
    if score["composite"] is None:
        return 0
    repo.record_score(db, {
        "entity_id": score["entity_id"], "model_id": score["model_id"],
        "model_version": score["model_version"], "as_of": score["as_of"],
        "composite": score["composite"], "categories": json.dumps(score["categories"]),
        "coverage": score["coverage"], "computed_at": iso(now_utc()),
    })
    db.commit()
    return 1
