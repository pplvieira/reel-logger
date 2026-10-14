"""Shape-tolerant Instagram Download Your Information reader.

Contract only for this slice: parse known shapes when present; never invent
`external_url` or creator when absent. Parsing a real zip is wired later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class ParsedWatchRow:
    creator_handle: Optional[str]
    external_url: Optional[str]
    watched_at: Optional[datetime]
    time_precision: str
    raw_json: dict[str, Any]


def parse_videos_watched_record(record: dict[str, Any]) -> ParsedWatchRow:
    """Accept several Instagram export shapes; fill fields only when present."""
    creator: Optional[str] = None
    url: Optional[str] = None
    watched_at: Optional[datetime] = None
    precision = "unknown"

    # Shape A: top-level timestamp + label_values[{label, value, href}, ...]
    if "timestamp" in record:
        watched_at = _from_unix(record.get("timestamp"))
        if watched_at:
            precision = "second"

    label_values = record.get("label_values")
    if isinstance(label_values, list):
        for item in label_values:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").lower()
            href = item.get("href")
            value = item.get("value")
            if href and not url:
                url = str(href)
            if value and ("author" in label or "account" in label or "username" in label):
                creator = str(value)
            # Some exports put the author in the first label without a clear name.
            if creator is None and value and not href and "time" not in label:
                creator = str(value)

    # Shape B: impressions_history_videos_watched style string_map_data / string_list_data
    smd = record.get("string_map_data")
    if isinstance(smd, dict):
        for key, entry in smd.items():
            if not isinstance(entry, dict):
                continue
            key_l = str(key).lower()
            if entry.get("href") and not url:
                url = str(entry["href"])
            if entry.get("timestamp") and watched_at is None:
                watched_at = _from_unix(entry.get("timestamp"))
                if watched_at:
                    precision = "second"
            if entry.get("value") and (
                "author" in key_l or "account" in key_l or "username" in key_l or "title" in key_l
            ):
                creator = str(entry["value"])

    sld = record.get("string_list_data")
    if isinstance(sld, list):
        for entry in sld:
            if not isinstance(entry, dict):
                continue
            if entry.get("href") and not url:
                url = str(entry["href"])
            if entry.get("value") and creator is None:
                creator = str(entry["value"])
            if entry.get("timestamp") and watched_at is None:
                watched_at = _from_unix(entry.get("timestamp"))
                if watched_at:
                    precision = "second"

    # Never invent a URL.
    return ParsedWatchRow(
        creator_handle=creator,
        external_url=url,
        watched_at=watched_at,
        time_precision=precision,
        raw_json=record,
    )


def parse_videos_watched_document(document: Any) -> list[ParsedWatchRow]:
    """Parse a videos_watched.json document (array or wrapped object)."""
    rows: list[dict[str, Any]] = []
    if isinstance(document, list):
        rows = [r for r in document if isinstance(r, dict)]
    elif isinstance(document, dict):
        for key in (
            "impressions_history_videos_watched",
            "videos_watched",
            "label_values",
        ):
            if key in document and isinstance(document[key], list):
                rows = [r for r in document[key] if isinstance(r, dict)]
                break
        if not rows and "timestamp" in document:
            rows = [document]
    return [parse_videos_watched_record(r) for r in rows]


def _from_unix(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    # ms vs s heuristic
    if ts > 10_000_000_000:
        ts = ts // 1000
    return datetime.fromtimestamp(ts, tz=timezone.utc)
