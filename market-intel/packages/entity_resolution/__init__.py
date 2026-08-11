"""Entity resolution — turning "Apple", "Apple Inc.", "AAPL" and CIK 320193
into one identity, without ever silently merging two different companies.

Resolution order (highest evidence first):
  1. IDENTIFIER  — CIK / ticker / domain / LEI. Authoritative, score 1.0.
  2. ALIAS       — exact normalized-name hit. Score 0.9.
  3. FUZZY       — difflib ratio over normalized names. Only accepted above
                   ACCEPT_THRESHOLD *and* only when the runner-up is clearly
                   worse (MARGIN); otherwise the match is AMBIGUOUS.

An ambiguous or weak match is never applied. It is written to
resolution_candidates with status='pending' for human review. Two different
companies merged by a fuzzy name match corrupts every downstream signal, so
the default is always "don't guess".
"""
import difflib

from packages.database.repositories import norm_name
from packages.shared.provenance import source_id
from packages.shared.timeutil import iso, now_utc

ACCEPT_THRESHOLD = 0.92   # fuzzy score required to auto-accept
REVIEW_THRESHOLD = 0.75   # below this we don't even record a candidate
MARGIN = 0.05             # winner must beat runner-up by this much


def canonical_entity_id(scheme: str, value: str) -> str:
    """Deterministic entity id from a strong identifier, so re-ingestion of the
    same company always lands on the same row (idempotency across runs)."""
    v = str(value).strip().lower().lstrip("0") or "0"
    return "ent_" + source_id("entity", scheme, v)[:24]


class Resolution:
    __slots__ = ("entity_id", "score", "method", "candidates", "status")

    def __init__(self, entity_id=None, score=0.0, method="none", candidates=None,
                 status="unresolved"):
        self.entity_id = entity_id
        self.score = round(float(score), 4)
        self.method = method
        self.candidates = candidates or []
        self.status = status   # resolved|ambiguous|unresolved

    @property
    def resolved(self):
        return self.status == "resolved"

    def as_dict(self):
        return {"entity_id": self.entity_id, "score": self.score,
                "method": self.method, "status": self.status,
                "candidates": self.candidates}

    def __repr__(self):
        return f"<Resolution {self.status} {self.entity_id} {self.score} via {self.method}>"


class EntityResolver:
    def __init__(self, db):
        self.db = db

    # -- lookups ------------------------------------------------------------
    def by_identifier(self, scheme, value):
        if value in (None, ""):
            return None
        v = str(value).strip().lower().lstrip("0") or "0"
        row = self.db.one(
            "SELECT entity_id FROM entity_identifiers WHERE scheme=? AND value_norm=? "
            "AND (valid_to IS NULL OR valid_to > ?) LIMIT 1",
            (scheme, v, iso(now_utc())))
        return row["entity_id"] if row else None

    def by_alias(self, mention, entity_type=None):
        n = norm_name(mention)
        if not n:
            return []
        sql = ("SELECT a.entity_id, e.type, e.name FROM entity_aliases a "
               "JOIN entities e ON e.id = a.entity_id WHERE a.alias_norm = ?")
        params = [n]
        if entity_type:
            sql += " AND e.type = ?"
            params.append(entity_type)
        return self.db.query(sql, tuple(params))

    def _fuzzy_pool(self, entity_type=None):
        sql = ("SELECT a.alias_norm, a.entity_id, e.name, e.type FROM entity_aliases a "
               "JOIN entities e ON e.id = a.entity_id WHERE e.status = 'active'")
        params = ()
        if entity_type:
            sql += " AND e.type = ?"
            params = (entity_type,)
        return self.db.query(sql, params)

    # -- main entry point ---------------------------------------------------
    def resolve(self, mention, *, identifiers=None, entity_type=None,
                source_record_id=None, context=None, record_candidates=True):
        """Resolve a mention to an entity. Identifiers win; names are evidence."""
        for scheme, value in (identifiers or {}).items():
            hit = self.by_identifier(scheme, value)
            if hit:
                return Resolution(hit, 1.0, f"identifier:{scheme}", status="resolved")

        exact = self.by_alias(mention, entity_type=entity_type)
        distinct = {r["entity_id"] for r in exact}
        if len(distinct) == 1:
            return Resolution(exact[0]["entity_id"], 0.9, "alias", status="resolved")
        if len(distinct) > 1:
            cands = [{"entity_id": r["entity_id"], "name": r["name"], "score": 0.9}
                     for r in exact]
            self._queue(mention, cands, "alias", source_record_id, context,
                        record_candidates)
            return Resolution(None, 0.9, "alias", cands, status="ambiguous")

        n = norm_name(mention)
        if not n:
            return Resolution(status="unresolved")
        pool = self._fuzzy_pool(entity_type)
        scored = []
        for row in pool:
            ratio = difflib.SequenceMatcher(None, n, row["alias_norm"]).ratio()
            if ratio >= REVIEW_THRESHOLD:
                scored.append({"entity_id": row["entity_id"], "name": row["name"],
                               "score": round(ratio, 4)})
        if not scored:
            return Resolution(status="unresolved")
        scored.sort(key=lambda r: r["score"], reverse=True)
        best = scored[0]
        runner = next((s for s in scored[1:] if s["entity_id"] != best["entity_id"]), None)
        clear = runner is None or (best["score"] - runner["score"]) >= MARGIN
        if best["score"] >= ACCEPT_THRESHOLD and clear:
            return Resolution(best["entity_id"], best["score"], "fuzzy", scored[:5],
                              status="resolved")
        self._queue(mention, scored[:5], "fuzzy", source_record_id, context,
                    record_candidates)
        return Resolution(None, best["score"], "fuzzy", scored[:5], status="ambiguous")

    def _queue(self, mention, candidates, method, source_record_id, context, enabled):
        if not enabled:
            return
        now = iso(now_utc())
        for c in candidates:
            self.db.insert_ignore("resolution_candidates", {
                "mention": mention, "context": context,
                "candidate_entity_id": c["entity_id"], "score": c["score"],
                "method": method, "status": "pending",
                "source_record_id": source_record_id, "created_at": now,
            }, ["id"])

    def pending_reviews(self, limit=50):
        return self.db.query(
            "SELECT rc.*, e.name AS candidate_name FROM resolution_candidates rc "
            "LEFT JOIN entities e ON e.id = rc.candidate_entity_id "
            "WHERE rc.status='pending' ORDER BY rc.score DESC LIMIT ?", (limit,))
