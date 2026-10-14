"""Match impressions to content records by time window (+ URL/caption).

Does not invent URLs. Does not derive dwell from DYI gaps.
Ambiguous pairs stay ambiguous.
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
    """Attach content records to unmatched impressions when the match is unique.

    Primary strategy (matches real DYI exports without Author):
    content.watched_at falls near impression shown_at..hidden_at (or shown±window).
    Prefer URL/caption agreement when both sides have them; creator is optional.
    """
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
        if impression.shown_at is None:
            result.unmatched += 1
            continue

        start = impression.shown_at - window
        end = (impression.hidden_at or impression.shown_at) + window

        candidates: list[ContentRecord] = []
        for content in contents:
            if content.watched_at is None:
                continue
            if not (start <= content.watched_at <= end):
                continue
            if not _compatible(impression, content):
                continue
            candidates.append(content)

        if len(candidates) == 0:
            result.unmatched += 1
            continue
        if len(candidates) > 1:
            # Prefer single URL agreement if it uniquely identifies
            if impression.external_url:
                url_hits = [
                    c for c in candidates if c.external_url == impression.external_url
                ]
                if len(url_hits) == 1:
                    candidates = url_hits
                else:
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
            else:
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


def _compatible(impression: Impression, content: ContentRecord) -> bool:
    """Reject obvious mismatches; allow null creator on either side."""
    if impression.external_url and content.external_url:
        return impression.external_url == content.external_url
    if impression.creator_handle and content.creator_handle:
        a = impression.creator_handle.lstrip("@").lower()
        b = content.creator_handle.lstrip("@").lower()
        if a != b:
            return False
    if impression.caption_excerpt and content.raw_json:
        cap = None
        # caption may live in raw_json label_values
        for item in content.raw_json.get("label_values") or []:
            if isinstance(item, dict) and str(item.get("label") or "").lower() == "caption":
                cap = item.get("value")
                break
        if isinstance(cap, str) and cap and impression.caption_excerpt:
            # soft check: require short overlap, not full equality
            left = impression.caption_excerpt[:40].lower()
            if left and left not in cap.lower() and cap[:40].lower() not in left:
                # still allow — captions often truncated differently
                pass
    return True
