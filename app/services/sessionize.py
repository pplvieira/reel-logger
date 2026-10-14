"""Pure sessionizer: semantic events → sessions, impressions, interactions.

No FastAPI imports. Ignores unknown / debug event types. Does not read
Android accessibility dumps to build derived rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional
from uuid import uuid4

from app.core.timeutil import ensure_utc
from app.services.platforms import get_adapter

SEMANTIC_TYPES = frozenset(
    {
        "session_start",
        "session_end",
        "reel_shown",
        "reel_hidden",
        "interaction",
    }
)


@dataclass
class SessionDraft:
    id: str
    user_id: str
    device_id: Optional[str]
    platform: str
    started_at: datetime
    ended_at: Optional[datetime]
    surface: str
    end_reason: Optional[str]
    capture_method: str
    logger_version: Optional[str]


@dataclass
class ImpressionDraft:
    id: str
    session_id: str
    user_id: str
    platform: str
    position_in_session: int
    shown_at: datetime
    hidden_at: Optional[datetime]
    dwell_ms: Optional[int]
    creator_handle: Optional[str]
    caption_excerpt: Optional[str]
    confidence: Optional[float]


@dataclass
class InteractionDraft:
    id: str
    session_id: str
    impression_id: Optional[str]
    user_id: str
    platform: str
    kind: str
    observed_at: datetime


@dataclass
class SessionizeResult:
    sessions: list[SessionDraft] = field(default_factory=list)
    impressions: list[ImpressionDraft] = field(default_factory=list)
    interactions: list[InteractionDraft] = field(default_factory=list)
    ignored_event_types: list[str] = field(default_factory=list)


@dataclass
class _OpenImpression:
    draft: ImpressionDraft


def sessionize(
    events: Iterable[dict[str, Any]],
    *,
    user_id: str,
    device_id: Optional[str],
    platform: str,
    capture_method: str,
    logger_version: Optional[str] = None,
    session_gap_seconds: int = 60,
) -> SessionizeResult:
    """Build derived rows from semantic events only.

    Each event dict needs: type, observed_at, payload (dict).
    """
    adapter = get_adapter(platform)
    gap = timedelta(seconds=session_gap_seconds)
    result = SessionizeResult()
    ignored: set[str] = set()

    ordered = sorted(
        (_normalize_event(e) for e in events),
        key=lambda e: e["observed_at"],
    )

    open_session: Optional[SessionDraft] = None
    open_impression: Optional[_OpenImpression] = None
    position = 0
    last_activity: Optional[datetime] = None

    def close_impression(at: datetime) -> None:
        nonlocal open_impression
        if open_impression is None:
            return
        draft = open_impression.draft
        if draft.hidden_at is None:
            draft.hidden_at = at
            draft.dwell_ms = max(
                0, int((ensure_utc(at) - ensure_utc(draft.shown_at)).total_seconds() * 1000)
            )
        result.impressions.append(draft)
        open_impression = None

    def close_session(at: datetime, reason: str) -> None:
        nonlocal open_session, position
        if open_session is None:
            return
        close_impression(at)
        open_session.ended_at = at
        open_session.end_reason = reason
        result.sessions.append(open_session)
        open_session = None
        position = 0

    for event in ordered:
        etype = event["type"]
        if etype not in SEMANTIC_TYPES:
            ignored.add(etype)
            continue

        at = event["observed_at"]
        payload = event["payload"]

        if open_session is not None and last_activity is not None:
            if at - last_activity > gap and etype != "session_end":
                close_session(last_activity, "gap")

        if etype == "session_start":
            if open_session is not None:
                close_session(at, "explicit")
            open_session = SessionDraft(
                id=str(uuid4()),
                user_id=user_id,
                device_id=device_id,
                platform=platform,
                started_at=at,
                ended_at=None,
                surface=adapter.normalize_surface(payload),
                end_reason=None,
                capture_method=capture_method,
                logger_version=logger_version,
            )
            last_activity = at
            continue

        if open_session is None:
            # Implicit session for orphan reel/interaction events.
            open_session = SessionDraft(
                id=str(uuid4()),
                user_id=user_id,
                device_id=device_id,
                platform=platform,
                started_at=at,
                ended_at=None,
                surface=adapter.normalize_surface(payload),
                end_reason=None,
                capture_method=capture_method,
                logger_version=logger_version,
            )

        if etype == "reel_shown":
            close_impression(at)
            position += 1
            open_impression = _OpenImpression(
                draft=ImpressionDraft(
                    id=str(uuid4()),
                    session_id=open_session.id,
                    user_id=user_id,
                    platform=platform,
                    position_in_session=position,
                    shown_at=at,
                    hidden_at=None,
                    dwell_ms=None,
                    creator_handle=_str_or_none(payload.get("creator_handle")),
                    caption_excerpt=_str_or_none(payload.get("caption_excerpt")),
                    confidence=_float_or_none(payload.get("confidence")),
                )
            )
        elif etype == "reel_hidden":
            close_impression(at)
        elif etype == "interaction":
            kind = adapter.normalize_interaction_kind(payload)
            if kind:
                impression_id = open_impression.draft.id if open_impression else None
                result.interactions.append(
                    InteractionDraft(
                        id=str(uuid4()),
                        session_id=open_session.id,
                        impression_id=impression_id,
                        user_id=user_id,
                        platform=platform,
                        kind=kind,
                        observed_at=at,
                    )
                )
        elif etype == "session_end":
            reason = _str_or_none(payload.get("end_reason")) or "explicit"
            close_session(at, reason)
            last_activity = at
            continue

        last_activity = at

    if open_session is not None and last_activity is not None:
        # Leave open sessions closed at last activity with end_reason leave
        # so reporting always has an end; re-sessionize can refine later.
        close_session(last_activity, open_session.end_reason or "leave")

    result.ignored_event_types = sorted(ignored)
    return result


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": str(event["type"]),
        "observed_at": ensure_utc(event["observed_at"]),
        "payload": event.get("payload") or {},
    }


def _str_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
