"""Time handling.

Rule for this platform: every timestamp stored is UTC, ISO-8601, with an
explicit offset. Naive datetimes are rejected at the boundary rather than
silently assumed to be local — a look-ahead-bias bug in a backtest usually
starts as a naive timestamp.
"""
from datetime import date, datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt) -> str:
    """Serialize a datetime/date to a storable ISO-8601 string (UTC)."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.isoformat()
    if dt.tzinfo is None:
        raise ValueError("naive datetime rejected: attach a timezone (UTC)")
    return dt.astimezone(timezone.utc).isoformat()


def parse_ts(value):
    """Parse an ISO-8601 string (accepting a trailing 'Z') to an aware datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
