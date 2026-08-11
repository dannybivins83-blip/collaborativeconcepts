"""Repositories — the only place that writes to the core tables.

Keeping writes here (rather than scattered through collectors) is what makes
the provenance and idempotency invariants enforceable: every function below
takes a source_record_id and upserts on a natural key.
"""
import json
import re
import unicodedata

from packages.shared.timeutil import iso, now_utc

# Legal-form suffixes stripped before name matching. "Apple Inc." and "Apple"
# must normalize to the same key, but stripping happens ONLY for matching —
# the display name keeps whatever the source said.
_SUFFIXES = (
    "incorporated", "inc", "corporation", "corp", "company", "co", "limited",
    "ltd", "llc", "lp", "plc", "holdings", "holding", "group", "sa", "nv", "ag",
    "the",
)


def norm_name(value: str) -> str:
    """Casefold, strip accents/punctuation and legal suffixes for alias matching."""
    if not value:
        return ""
    s = unicodedata.normalize("NFKD", str(value))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    words = [w for w in s.split() if w]
    while words and words[-1] in _SUFFIXES:
        words.pop()
    while words and words[0] in _SUFFIXES:
        words.pop(0)
    return " ".join(words)


def slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return s or "unnamed"


# ------------------------------------------------------------- ingestion ----
def register_source(db, **row):
    row.setdefault("license_class", "REVIEW_REQUIRED")
    db.upsert("data_sources", row, ["id"])
    db.commit()
    return row["id"]


def start_run(db, source_id, collector):
    cur = db.execute(
        "INSERT INTO ingestion_runs (source_id, collector, started_at, status) "
        "VALUES (?,?,?,'running')", (source_id, collector, iso(now_utc())))
    db.commit()
    return cur.lastrowid


def finish_run(db, run_id, status, fetched=0, written=0, rejected=0,
               checkpoint=None, error=None):
    db.execute(
        "UPDATE ingestion_runs SET finished_at=?, status=?, records_fetched=?, "
        "records_written=?, records_rejected=?, checkpoint=?, error=? WHERE id=?",
        (iso(now_utc()), status, fetched, written, rejected, checkpoint, error, run_id))
    db.commit()


def put_source_record(db, record: dict) -> str:
    """Write a RAW record. Never updated destructively: a re-fetch with different
    content updates payload/hash but keeps the same natural id and lineage."""
    db.upsert("source_records", record, ["id"])
    return record["id"]


# ---------------------------------------------------------------- entities --
def upsert_entity(db, *, entity_id, type, name, description=None, slug=None):
    now = iso(now_utc())
    slug = slug or slugify(name)
    existing = db.one("SELECT id FROM entities WHERE id=?", (entity_id,))
    row = {"id": entity_id, "type": type, "name": name, "slug": slug,
           "description": description, "updated_at": now,
           "created_at": existing["created_at"] if existing and "created_at" in existing else now}
    db.upsert("entities", row, ["id"])
    return entity_id


def add_alias(db, entity_id, alias, kind="name", source_record_id=None, confidence=1.0):
    if not alias:
        return
    db.insert_ignore("entity_aliases", {
        "entity_id": entity_id, "alias": alias, "alias_norm": norm_name(alias),
        "kind": kind, "source_record_id": source_record_id, "confidence": confidence,
    }, ["entity_id", "alias_norm", "kind"])


def add_identifier(db, entity_id, scheme, value, source_record_id=None,
                   valid_from=None, valid_to=None):
    if value in (None, ""):
        return
    db.upsert("entity_identifiers", {
        "entity_id": entity_id, "scheme": scheme, "value": str(value),
        "value_norm": str(value).strip().lower().lstrip("0") or "0",
        "source_record_id": source_record_id,
        "valid_from": valid_from, "valid_to": valid_to,
    }, ["scheme", "value_norm", "entity_id"])


def upsert_security(db, *, security_id, entity_id, ticker, exchange=None):
    db.upsert("securities", {
        "id": security_id, "entity_id": entity_id, "ticker": ticker.upper(),
        "exchange": exchange, "currency": "USD", "security_type": "common", "active": 1,
    }, ["ticker", "exchange"])
    return security_id


# --------------------------------------------------------------------- SEC --
def upsert_filing(db, filing: dict):
    db.upsert("sec_filings", filing, ["cik", "accession_no"])
    return filing["id"]


def upsert_fact(db, fact: dict):
    db.upsert("filing_facts", fact,
              ["entity_id", "taxonomy", "concept", "unit", "period_start",
               "period_end", "form"])


# ---------------------------------------------------------------- tagging ---
def upsert_tag(db, *, tag_id, name, slug=None, parent_id=None, category=None,
               description=None):
    db.upsert("tags", {
        "id": tag_id, "name": name, "slug": slug or slugify(name),
        "description": description, "parent_id": parent_id, "category": category,
        "created_at": iso(now_utc()),
    }, ["id"])
    return tag_id


def add_tag_alias(db, tag_id, alias):
    db.insert_ignore("tag_aliases", {"tag_id": tag_id, "alias": alias,
                                     "alias_norm": norm_name(alias)},
                     ["tag_id", "alias_norm"])


def record_entity_tag(db, obs: dict):
    """One (entity, tag, source_record) observation. Repeats collapse; the same
    document can never inflate a tag's strength twice."""
    db.upsert("entity_tags", obs, ["entity_id", "tag_id", "source_record_id"])


# ---------------------------------------------------------- relationships ---
def record_relationship(db, *, rel_id, from_entity_id, to_entity_id, type,
                        observed_at, source_record_id, excerpt=None, confidence=0.5):
    existing = db.one("SELECT id, first_seen_at, observation_count FROM relationships "
                      "WHERE from_entity_id=? AND to_entity_id=? AND type=?",
                      (from_entity_id, to_entity_id, type))
    if existing:
        db.execute("UPDATE relationships SET last_seen_at=?, observation_count=?, "
                   "confidence=? WHERE id=?",
                   (observed_at, existing["observation_count"] + 1,
                    min(0.99, confidence + 0.05 * existing["observation_count"]),
                    existing["id"]))
        rel_id = existing["id"]
    else:
        db.upsert("relationships", {
            "id": rel_id, "from_entity_id": from_entity_id,
            "to_entity_id": to_entity_id, "type": type,
            "first_seen_at": observed_at, "last_seen_at": observed_at,
            "observation_count": 1, "confidence": confidence, "status": "active",
        }, ["from_entity_id", "to_entity_id", "type"])
    db.insert_ignore("relationship_evidence", {
        "relationship_id": rel_id, "source_record_id": source_record_id,
        "observed_at": observed_at, "excerpt": excerpt, "confidence": confidence,
    }, ["relationship_id", "source_record_id", "excerpt"])
    return rel_id


# ---------------------------------------------------------------- signals ---
def upsert_signal_def(db, *, signal_id, name, description=None, category=None,
                      direction="higher_is_bullish", version=1, definition=None):
    db.upsert("signals", {
        "id": signal_id, "name": name, "description": description,
        "category": category, "direction": direction, "version": version,
        "definition": json.dumps(definition or {}), "enabled": 1,
    }, ["id"])
    return signal_id


def record_signal_observation(db, obs: dict):
    obs.setdefault("subject_id", "")
    db.upsert("signal_observations", obs,
              ["signal_id", "entity_id", "subject_id", "observed_at", "signal_version"])


def record_score(db, score: dict):
    db.upsert("scores", score, ["entity_id", "model_id", "model_version", "as_of"])
