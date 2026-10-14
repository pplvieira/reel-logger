"""Timezone helpers that behave the same on SQLite and Postgres."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def local_day(dt: datetime, tz_name: str) -> date:
    """Calendar day for an instant in the user's IANA timezone."""
    return ensure_utc(dt).astimezone(ZoneInfo(tz_name)).date()
