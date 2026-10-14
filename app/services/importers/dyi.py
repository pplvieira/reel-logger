"""Shape-tolerant Instagram Download Your Information reader.

Never invents `external_url` or creator when absent. Never derives dwell
from inter-row gaps.
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
    caption: Optional[str] = None
    fbid: Optional[str] = None


def parse_videos_watched_record(record: dict[str, Any]) -> ParsedWatchRow:
    """Accept several Instagram export shapes; fill fields only when present."""
    creator: Optional[str] = None
    url: Optional[str] = None
    caption: Optional[str] = None
    watched_at: Optional[datetime] = None
    precision = "unknown"
    fbid = str(record["fbid"]) if record.get("fbid") is not None else None

    if "timestamp" in record:
        watched_at = _from_unix(record.get("timestamp"))
        if watched_at:
            precision = "second"

    label_values = record.get("label_values")
    if isinstance(label_values, list):
        for item in label_values:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            label_l = label.lower()
            href = item.get("href")
            value = item.get("value")

            # Prefer the explicit URL label (real 2026 export shape).
            if label_l == "url" and href:
                url = str(href)
            elif href and not url and "instagram.com" in str(href):
                # Fallback: first Instagram href if URL label missing
                if "facebook.com/ads" not in str(href):
                    url = str(href)

            if label_l == "caption" and value:
                caption = str(value)
            if value and label_l in {"author", "account", "username", "autor"}:
                creator = str(value)

    smd = record.get("string_map_data")
    if isinstance(smd, dict):
        for key, entry in smd.items():
            if not isinstance(entry, dict):
                continue
            key_l = str(key).lower()
            if entry.get("href") and not url and "instagram.com" in str(entry["href"]):
                url = str(entry["href"])
            if entry.get("timestamp") and watched_at is None:
                watched_at = _from_unix(entry.get("timestamp"))
                if watched_at:
                    precision = "second"
            if entry.get("value") and key_l in {"author", "account", "username"}:
                creator = str(entry["value"])
            if entry.get("value") and key_l == "caption":
                caption = str(entry["value"])

    sld = record.get("string_list_data")
    if isinstance(sld, list):
        for entry in sld:
            if not isinstance(entry, dict):
                continue
            if entry.get("href") and not url and "instagram.com" in str(entry["href"]):
                url = str(entry["href"])
            if entry.get("value") and creator is None and entry.get("href"):
                # title next to href sometimes is author — only if looks like a handle
                val = str(entry["value"])
                if val.startswith("@") or (len(val) <= 30 and " " not in val):
                    creator = val.lstrip("@")
            if entry.get("timestamp") and watched_at is None:
                watched_at = _from_unix(entry.get("timestamp"))
                if watched_at:
                    precision = "second"

    return ParsedWatchRow(
        creator_handle=creator,
        external_url=url,
        watched_at=watched_at,
        time_precision=precision,
        raw_json=record,
        caption=caption,
        fbid=fbid,
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


def parse_liked_or_saved_document(document: Any) -> list[ParsedWatchRow]:
    """liked_posts.json / saved_posts.json use the same label_values envelope."""
    return parse_videos_watched_document(document)


def _from_unix(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    if ts > 10_000_000_000:
        ts = ts // 1000
    return datetime.fromtimestamp(ts, tz=timezone.utc)
