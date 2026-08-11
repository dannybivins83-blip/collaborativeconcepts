"""The collector contract every data source implements.

    fetch()              -> iterable of raw documents (paginated, checkpointed)
    validate(doc)        -> [] or a list of problems (rejected, counted, logged)
    normalize(doc)       -> list of normalized rows
    persist_raw(doc)     -> writes source_records, returns source_record_id
    persist_normalized() -> writes domain tables, all carrying source_record_id
    health_check()       -> cheap liveness probe for the data-health dashboard

`run()` wires them together with per-source isolation: a failure is recorded on
the ingestion_run and raised as CollectorError, so an orchestrator can keep
every other source going.
"""
from dataclasses import dataclass, field

from packages.database import repositories as repo
from packages.shared.errors import CollectorError, ValidationError
from packages.shared.provenance import content_hash
from packages.shared.timeutil import iso, now_utc


@dataclass
class RunResult:
    source: str
    collector: str
    run_id: int = 0
    fetched: int = 0
    written: int = 0
    rejected: int = 0
    status: str = "ok"
    error: str = None
    problems: list = field(default_factory=list)

    def as_dict(self):
        return {"source": self.source, "collector": self.collector,
                "run_id": self.run_id, "fetched": self.fetched,
                "written": self.written, "rejected": self.rejected,
                "status": self.status, "error": self.error}


class Collector:
    source_id = "unknown"
    name = "unnamed collector"
    kind = "record"

    def __init__(self, db, transport, checkpoint=None):
        self.db = db
        self.transport = transport
        self.checkpoint = checkpoint

    # -- contract -----------------------------------------------------------
    def fetch(self):  # pragma: no cover - interface
        raise NotImplementedError

    def validate(self, doc) -> list:
        return []

    def normalize(self, doc, source_record_id) -> list:
        return []

    def persist_normalized(self, rows) -> int:
        return 0

    def health_check(self) -> dict:  # pragma: no cover - overridden per source
        return {"source": self.source_id, "ok": True, "checked_at": iso(now_utc())}

    # -- raw layer ----------------------------------------------------------
    def persist_raw(self, doc, run_id) -> str:
        import json
        rec = {
            "id": doc["source_record_id"],
            "source_id": self.source_id,
            "kind": doc.get("kind", self.kind),
            "source_url": doc.get("url"),
            "payload": json.dumps(doc["payload"], separators=(",", ":")),
            "content_hash": content_hash(doc["payload"]),
            "observed_at": doc.get("observed_at"),
            "effective_at": doc.get("effective_at"),
            "ingested_at": iso(now_utc()),
            "run_id": run_id,
        }
        return repo.put_source_record(self.db, rec)

    # -- orchestration ------------------------------------------------------
    def run(self) -> RunResult:
        result = RunResult(source=self.source, collector=self.name)
        result.run_id = repo.start_run(self.db, self.source_id, self.name)
        try:
            for doc in self.fetch():
                result.fetched += 1
                problems = self.validate(doc)
                if problems:
                    result.rejected += 1
                    result.problems.append({"url": doc.get("url"), "problems": problems})
                    continue
                srid = self.persist_raw(doc, result.run_id)
                rows = self.normalize(doc, srid)
                result.written += self.persist_normalized(rows)
            self.db.commit()
            result.status = "partial" if result.rejected else "ok"
        except CollectorError as e:
            self.db.commit()          # keep whatever was already ingested
            result.status, result.error = "failed", str(e)
        except Exception as e:        # a bug must not lose the run record
            self.db.commit()
            result.status, result.error = "failed", f"{type(e).__name__}: {e}"
        repo.finish_run(self.db, result.run_id, result.status, result.fetched,
                        result.written, result.rejected, self.checkpoint, result.error)
        return result

    @property
    def source(self):
        return self.source_id
