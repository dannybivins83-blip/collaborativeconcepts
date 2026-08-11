"""Connection + migrations + the small query helpers everything else uses."""
import os
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB = os.environ.get("MI_DATABASE_URL", "sqlite:///data/market-intel.db")


def _sqlite_path(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    if url.startswith("sqlite://"):
        return url[len("sqlite://"):]
    return url


class Database:
    """Thin wrapper over a DB-API connection.

    Deliberately not an ORM: the analytical queries here are set-based and
    read better as SQL, and staying DB-API-shaped keeps the Postgres swap to a
    driver change rather than a rewrite.
    """

    def __init__(self, conn, dialect="sqlite"):
        self.conn = conn
        self.dialect = dialect
        self.conn.row_factory = sqlite3.Row if dialect == "sqlite" else None

    # -- lifecycle ----------------------------------------------------------
    @classmethod
    def open(cls, url=None):
        url = url or DEFAULT_DB
        if not url.startswith("sqlite"):
            raise NotImplementedError(
                "PostgreSQL driver not wired yet — see docs/DATABASE_SCHEMA.md. "
                "Set MI_DATABASE_URL to a sqlite:/// path for local runs.")
        path = _sqlite_path(url)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL") if path != ":memory:" else None
        return cls(conn)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- queries ------------------------------------------------------------
    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def executemany(self, sql, seq):
        return self.conn.executemany(sql, seq)

    def query(self, sql, params=()) -> list:
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql, params=()):
        row = self.conn.execute(sql, params).fetchone()
        return row[0] if row else None

    def commit(self):
        self.conn.commit()

    # -- writes -------------------------------------------------------------
    def upsert(self, table, row: dict, conflict_keys, update=True):
        """INSERT .. ON CONFLICT — the idempotency primitive.

        Every ingest path uses this: re-running a collector must converge on the
        same rows rather than accumulate duplicates.
        """
        cols = list(row.keys())
        placeholders = ",".join("?" for _ in cols)
        conflict = ",".join(conflict_keys)
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        if update:
            assign = ",".join(f"{c}=excluded.{c}" for c in cols if c not in conflict_keys)
            sql += (f" ON CONFLICT({conflict}) DO UPDATE SET {assign}"
                    if assign else f" ON CONFLICT({conflict}) DO NOTHING")
        else:
            sql += f" ON CONFLICT({conflict}) DO NOTHING"
        return self.conn.execute(sql, [row[c] for c in cols])

    def insert_ignore(self, table, row: dict, conflict_keys):
        return self.upsert(table, row, conflict_keys, update=False)


def migrate(db: Database) -> int:
    """Apply schema.sql (idempotent: every statement is IF NOT EXISTS)."""
    db.conn.executescript(SCHEMA_PATH.read_text())
    from packages.shared.timeutil import iso, now_utc
    db.insert_ignore("schema_migrations", {"version": 1, "applied_at": iso(now_utc())},
                     ["version"])
    db.commit()
    return 1


def connect(url=None, run_migrations=True) -> Database:
    db = Database.open(url)
    if run_migrations:
        migrate(db)
    return db
