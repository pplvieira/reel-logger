"""Match impressions to content records (creator + nearby watch time).

Does not invent URLs. Ambiguous pairs stay ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import ContentRecord, Impression, ImpressionMatch


@dataclass
class ReconcileResult:
    unique: int = 0
    ambiguous: int = 0
    unmatched: int = 0


def reconcile_impressions(
    db: Session,
    *,
    user_id: str,
    platform: str = "instagram",
    window_seconds: int = 120,
) -> ReconcileResult:
    """Attach content records to unmatched impressions when the match is unique."""
    window = timedelta(seconds=window_seconds)
    impressions = (
        db.query(Impression)
        .filter(
            Impression.user_id == user_id,
            Impression.platform == platform,
            Impression.match_status == "unmatched",
        )
        .all()
    )
    contents = (
        db.query(ContentRecord)
        .filter(ContentRecord.user_id == user_id, ContentRecord.platform == platform)
        .all()
    )

    result = ReconcileResult()
    for impression in impressions:
        if not impression.creator_handle or impression.shown_at is None:
            result.unmatched += 1
            continue

        candidates: list[ContentRecord] = []
        for content in contents:
            if not content.creator_handle:
                continue
            if content.creator_handle.lstrip("@").lower() != impression.creator_handle.lstrip(
                "@"
            ).lower():
                continue
            if content.watched_at is None:
                continue
            delta = abs(content.watched_at - impression.shown_at)
            if delta <= window:
                candidates.append(content)

        if len(candidates) == 0:
            result.unmatched += 1
            continue
        if len(candidates) > 1:
            impression.match_status = "ambiguous"
            for content in candidates:
                db.add(
                    ImpressionMatch(
                        impression_id=impression.id,
                        content_record_id=content.id,
                        status="ambiguous",
                    )
                )
            result.ambiguous += 1
            continue

        content = candidates[0]
        impression.match_status = "unique"
        if content.external_url:
            impression.external_url = content.external_url
        db.add(
            ImpressionMatch(
                impression_id=impression.id,
                content_record_id=content.id,
                status="unique",
            )
        )
        result.unique += 1

    db.commit()
    return result
