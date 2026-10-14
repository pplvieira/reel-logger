from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Device, Impression, Interaction, RawEvent, Session as ScrollSession, User
from app.schemas.events import EventBatch, IngestResult
from app.services.sessionize import sessionize


def ingest_batch(db: Session, batch: EventBatch) -> IngestResult:
    settings = get_settings()
    user = db.get(User, batch.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"Unknown user_id: {batch.user_id}")

    device = db.get(Device, batch.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Unknown device_id: {batch.device_id}")
    if device.user_id != batch.user_id:
        raise HTTPException(status_code=400, detail="device_id does not belong to user_id")

    if batch.logger_version and device.logger_version != batch.logger_version:
        device.logger_version = batch.logger_version

    new_events = []
    duplicates = 0
    for event in batch.events:
        if event.event_id:
            exists = (
                db.query(RawEvent.id)
                .filter(
                    RawEvent.device_id == batch.device_id,
                    RawEvent.event_id == event.event_id,
                )
                .first()
            )
            if exists:
                duplicates += 1
                continue
        new_events.append(event)
        db.add(
            RawEvent(
                user_id=batch.user_id,
                device_id=batch.device_id,
                platform=batch.platform,
                schema_version=batch.schema_version,
                observed_at=event.observed_at,
                type=event.type,
                payload=event.payload,
                capture_method=batch.capture_method,
                event_id=event.event_id,
            )
        )

    if not new_events:
        db.commit()
        return IngestResult(
            accepted=0,
            duplicates=duplicates,
            sessionized_sessions=0,
            sessionized_impressions=0,
            sessionized_interactions=0,
            ignored_event_types=[],
        )

    try:
        derived = sessionize(
            (
                {
                    "type": e.type,
                    "observed_at": e.observed_at,
                    "payload": e.payload,
                }
                for e in new_events
            ),
            user_id=batch.user_id,
            device_id=batch.device_id,
            platform=batch.platform,
            capture_method=batch.capture_method,
            logger_version=batch.logger_version,
            session_gap_seconds=settings.session_gap_seconds,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for s in derived.sessions:
        db.add(
            ScrollSession(
                id=s.id,
                user_id=s.user_id,
                device_id=s.device_id,
                platform=s.platform,
                started_at=s.started_at,
                ended_at=s.ended_at,
                surface=s.surface,
                end_reason=s.end_reason,
                capture_method=s.capture_method,
                logger_version=s.logger_version,
            )
        )
    for imp in derived.impressions:
        db.add(
            Impression(
                id=imp.id,
                session_id=imp.session_id,
                user_id=imp.user_id,
                platform=imp.platform,
                position_in_session=imp.position_in_session,
                shown_at=imp.shown_at,
                hidden_at=imp.hidden_at,
                dwell_ms=imp.dwell_ms,
                creator_handle=imp.creator_handle,
                caption_excerpt=imp.caption_excerpt,
                confidence=imp.confidence,
                match_status="unmatched",
            )
        )
    for inter in derived.interactions:
        db.add(
            Interaction(
                id=inter.id,
                session_id=inter.session_id,
                impression_id=inter.impression_id,
                user_id=inter.user_id,
                platform=inter.platform,
                kind=inter.kind,
                observed_at=inter.observed_at,
            )
        )

    db.commit()
    return IngestResult(
        accepted=len(new_events),
        duplicates=duplicates,
        sessionized_sessions=len(derived.sessions),
        sessionized_impressions=len(derived.impressions),
        sessionized_interactions=len(derived.interactions),
        ignored_event_types=derived.ignored_event_types,
    )


def ensure_seed_user(db: Session) -> User:
    settings = get_settings()
    existing = db.query(User).order_by(User.created_at.asc()).first()
    if existing:
        return existing
    user = User(
        display_name=settings.seed_user_display_name,
        timezone=settings.default_timezone,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
