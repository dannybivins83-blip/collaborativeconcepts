"""Provenance — the non-negotiable spine of the platform.

Every normalized row and every derived observation carries a pointer back to
the raw record it came from. A signal you cannot trace to evidence is a rumour,
so `source_record_id` is required (not nullable) on derived tables.

`source_id` builds the STABLE natural key that makes ingestion idempotent:
running the same collector twice must upsert, never duplicate. It is a hash of
(source, kind, natural key parts) — deliberately not of the payload, so a
re-fetch of the same document with a cosmetic difference still collapses onto
one row.
"""
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional

from .timeutil import iso, now_utc


def source_id(source: str, kind: str, *parts) -> str:
    """Stable id for a source record, e.g. source_id('sec', 'filing', cik, accession)."""
    key = "|".join([source, kind] + [str(p) for p in parts if p is not None])
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def content_hash(payload) -> str:
    """Hash of the payload itself — used to detect that a re-fetch actually changed."""
    if not isinstance(payload, (str, bytes)):
        import json
        payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if isinstance(payload, str):
        payload = payload.encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass
class Provenance:
    """Where an observation came from and when it was true vs. when we learned it.

    observed_at  — when the source says the thing happened
    effective_at — when it became true for the world (filing period end, trade date)
    ingested_at  — when WE learned it. Backtests must filter on this, not observed_at,
                   or they inherit look-ahead bias.
    """
    source: str
    source_record_id: str
    source_url: Optional[str] = None
    observed_at: Optional[str] = None
    effective_at: Optional[str] = None
    ingested_at: str = field(default_factory=lambda: iso(now_utc()))
    confidence: float = 1.0

    def as_row(self) -> dict:
        d = asdict(self)
        d["confidence"] = round(float(self.confidence), 4)
        return d
