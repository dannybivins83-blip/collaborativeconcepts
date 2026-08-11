"""Tag engine — the hierarchical taxonomy and the tagger that observes it.

A tag is not a label stapled to a company. Every hit is an OBSERVATION:
(entity, tag, source_record, when, how often, with what evidence). Strength
over time is then a query, which is what makes "AI mentions accelerating"
answerable at all.

Matching is lexical + alias-driven with word boundaries, because a substring
match ("ai" inside "aim") produces exactly the kind of silent garbage that
destroys trust in a signal. Embedding-based matching is a later addition
behind the same `Tagger` interface (see docs/TAG_GRAPH.md).
"""
import re

from packages.database import repositories as repo
from packages.shared.timeutil import iso, now_utc

from .taxonomy import TAXONOMY, seed_taxonomy   # noqa: F401  (re-exported)

# A tag must clear this to be recorded at all — one glancing mention of "AI" in
# a 200-page 10-K is noise, not exposure.
MIN_RELEVANCE = 0.01


def _pattern(alias: str):
    """Word-boundary regex for an alias. Multi-word aliases allow flexible
    whitespace; short all-caps aliases (GPU, AI) stay case-sensitive to avoid
    matching ordinary words."""
    parts = [re.escape(p) for p in alias.split()]
    body = r"\s+".join(parts)
    flags = 0 if (len(alias) <= 4 and alias.isupper()) else re.IGNORECASE
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", flags)


def _dedupe_aliases(aliases):
    """Collapse case-variants of the same surface form.

    A tag's display name and one of its aliases routinely differ only in case
    ("Artificial Intelligence" vs "artificial intelligence"). Compiling both
    made every mention count TWICE, silently inflating frequency and relevance
    on exactly the highest-traffic tags. Keep one variant per casefolded form,
    preferring an all-caps spelling because that is what makes short aliases
    (AI, GPU) match case-sensitively.
    """
    best = {}
    for a in aliases:
        key = a.casefold()
        current = best.get(key)
        if current is None or (a.isupper() and not current.isupper()):
            best[key] = a
    return sorted(best.values(), key=len, reverse=True)


class Tagger:
    """Scans text for taxonomy hits and writes temporal observations."""

    def __init__(self, db):
        self.db = db
        self._compiled = None

    def _load(self):
        if self._compiled is not None:
            return self._compiled
        rows = self.db.query(
            "SELECT t.id AS tag_id, t.name, t.slug, a.alias FROM tags t "
            "LEFT JOIN tag_aliases a ON a.tag_id = t.id")
        by_tag = {}
        for r in rows:
            entry = by_tag.setdefault(r["tag_id"], {"tag_id": r["tag_id"],
                                                    "name": r["name"], "aliases": set()})
            entry["aliases"].add(r["name"])
            if r["alias"]:
                entry["aliases"].add(r["alias"])
        self._compiled = [
            {"tag_id": e["tag_id"], "name": e["name"],
             "patterns": [(a, _pattern(a)) for a in _dedupe_aliases(e["aliases"])]}
            for e in by_tag.values()
        ]
        return self._compiled

    def scan(self, text: str) -> list:
        """Return [{tag_id, frequency, evidence, relevance}] for one document."""
        if not text:
            return []
        words = max(1, len(text.split()))
        out = []
        for tag in self._load():
            hits, snippet = 0, None
            for alias, pattern in tag["patterns"]:
                for m in pattern.finditer(text):
                    hits += 1
                    if snippet is None:
                        lo, hi = max(0, m.start() - 60), min(len(text), m.end() + 60)
                        snippet = ("…" if lo else "") + text[lo:hi].strip() + ("…" if hi < len(text) else "")
            if not hits:
                continue
            # Density per 1k words, damped: a doc with 40 mentions is stronger
            # than one with 4, but not 10x stronger.
            relevance = min(1.0, (hits / words * 1000.0) ** 0.5 / 3.0)
            if relevance < MIN_RELEVANCE:
                continue
            out.append({"tag_id": tag["tag_id"], "tag_name": tag["name"],
                        "frequency": hits, "evidence": snippet,
                        "relevance": round(relevance, 4)})
        return sorted(out, key=lambda t: t["frequency"], reverse=True)

    def tag_document(self, *, entity_id, text, source_record_id, observed_at,
                     effective_at=None, method="lexical", confidence=0.8):
        """Scan and persist. Returns the observations written."""
        hits = self.scan(text)
        now = iso(now_utc())
        for h in hits:
            repo.record_entity_tag(self.db, {
                "entity_id": entity_id, "tag_id": h["tag_id"],
                "source_record_id": source_record_id,
                "observed_at": observed_at, "effective_at": effective_at,
                "ingested_at": now, "frequency": h["frequency"],
                "confidence": confidence, "relevance": h["relevance"],
                "evidence": h["evidence"], "method": method,
            })
        return hits


def tag_timeseries(db, entity_id, tag_id, bucket="month"):
    """Mentions per period for one (entity, tag) — the raw material of
    topic-acceleration signals. Bucketing is done on observed_at (when the
    document is dated), not ingested_at."""
    fmt = {"day": 10, "month": 7, "year": 4}.get(bucket, 7)
    rows = db.query(
        f"SELECT substr(observed_at,1,{fmt}) AS period, "
        "SUM(frequency) AS mentions, COUNT(*) AS documents "
        "FROM entity_tags WHERE entity_id=? AND tag_id=? "
        "GROUP BY period ORDER BY period", (entity_id, tag_id))
    return rows


def top_tags(db, entity_id, limit=20):
    return db.query(
        "SELECT t.id AS tag_id, t.name, t.slug, SUM(et.frequency) AS mentions, "
        "COUNT(DISTINCT et.source_record_id) AS documents, "
        "MAX(et.observed_at) AS last_seen, AVG(et.relevance) AS avg_relevance "
        "FROM entity_tags et JOIN tags t ON t.id = et.tag_id "
        "WHERE et.entity_id = ? GROUP BY t.id ORDER BY mentions DESC LIMIT ?",
        (entity_id, limit))


def entities_for_tag(db, tag_id, limit=50):
    return db.query(
        "SELECT e.id AS entity_id, e.name, e.type, SUM(et.frequency) AS mentions, "
        "MAX(et.observed_at) AS last_seen FROM entity_tags et "
        "JOIN entities e ON e.id = et.entity_id WHERE et.tag_id = ? "
        "GROUP BY e.id ORDER BY mentions DESC LIMIT ?", (tag_id, limit))
