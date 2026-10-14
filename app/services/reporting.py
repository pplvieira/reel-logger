from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.timeutil import local_day
from app.models import Impression, Interaction, Session as ScrollSession, User
from app.schemas.reporting import DaySummary, ImpressionOut, SessionOut


def list_sessions(
    db: Session,
    *,
    user_id: str,
    platform: Optional[str] = None,
) -> list[SessionOut]:
    user = db.get(User, user_id)
    if user is None:
        return []

    q = db.query(ScrollSession).filter(ScrollSession.user_id == user_id)
    if platform:
        q = q.filter(ScrollSession.platform == platform)
    sessions = q.order_by(ScrollSession.started_at.asc()).all()

    counts = dict(
        db.query(Impression.session_id, func.count(Impression.id))
        .filter(Impression.user_id == user_id)
        .group_by(Impression.session_id)
        .all()
    )

    out: list[SessionOut] = []
    for s in sessions:
        out.append(
            SessionOut(
                id=s.id,
                user_id=s.user_id,
                device_id=s.device_id,
                platform=s.platform,
                started_at=s.started_at,
                ended_at=s.ended_at,
                surface=s.surface,
                end_reason=s.end_reason,
                capture_method=s.capture_method,
                impression_count=int(counts.get(s.id, 0)),
                local_day=local_day(s.started_at, user.timezone),
            )
        )
    return out


def day_summaries(db: Session, *, user_id: str) -> list[DaySummary]:
    user = db.get(User, user_id)
    if user is None:
        return []

    sessions = (
        db.query(ScrollSession)
        .filter(ScrollSession.user_id == user_id)
        .order_by(ScrollSession.started_at.asc())
        .all()
    )
    impressions = db.query(Impression).filter(Impression.user_id == user_id).all()
    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()

    by_day_sessions: dict[date, int] = defaultdict(int)
    by_day_imps: dict[date, int] = defaultdict(int)
    by_day_dwell: dict[date, int] = defaultdict(int)
    by_day_inter: dict[date, int] = defaultdict(int)

    session_day = {s.id: local_day(s.started_at, user.timezone) for s in sessions}
    for s in sessions:
        by_day_sessions[session_day[s.id]] += 1

    for imp in impressions:
        day = session_day.get(imp.session_id) or local_day(imp.shown_at, user.timezone)
        by_day_imps[day] += 1
        by_day_dwell[day] += int(imp.dwell_ms or 0)

    for inter in interactions:
        day = session_day.get(inter.session_id) or local_day(inter.observed_at, user.timezone)
        by_day_inter[day] += 1

    days = sorted(set(by_day_sessions) | set(by_day_imps) | set(by_day_inter))
    return [
        DaySummary(
            local_day=d,
            user_id=user_id,
            timezone=user.timezone,
            session_count=by_day_sessions[d],
            impression_count=by_day_imps[d],
            total_dwell_ms=by_day_dwell[d],
            interaction_count=by_day_inter[d],
        )
        for d in days
    ]


def list_impressions(
    db: Session,
    *,
    user_id: str,
    session_id: Optional[str] = None,
) -> list[ImpressionOut]:
    q = db.query(Impression).filter(Impression.user_id == user_id)
    if session_id:
        q = q.filter(Impression.session_id == session_id)
    rows = q.order_by(Impression.shown_at.asc()).all()
    return [ImpressionOut.model_validate(r) for r in rows]
