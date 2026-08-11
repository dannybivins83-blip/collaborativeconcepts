"""Database access.

SQLite is the dev/test engine (zero infrastructure, runs anywhere); PostgreSQL
is the production target. Everything here goes through `Database`, which speaks
plain SQL with `?` placeholders — the one dialect difference that matters is
translated in `_sql()` so callers never write engine-specific code.
"""
from .db import Database, connect, migrate
from . import repositories

__all__ = ["Database", "connect", "migrate", "repositories"]
