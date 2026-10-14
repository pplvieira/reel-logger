from datetime import datetime, timedelta, timezone

from app.models import ContentRecord, Impression, Session as ScrollSession, User
from app.services.reconcile import reconcile_impressions


def _seed(db, *, shown_offset_s=0, watch_offset_s=5, url="https://www.instagram.com/reel/AAA/"):
    now = datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc)
    user = User(display_name="t", timezone="Europe/Copenhagen", created_at=now)
    db.add(user)
    db.flush()
    session = ScrollSession(
        user_id=user.id,
        platform="instagram",
        started_at=now,
        ended_at=now + timedelta(minutes=5),
        surface="for_you",
        capture_method="accessibility",
    )
    db.add(session)
    db.flush()
    imp = Impression(
        session_id=session.id,
        user_id=user.id,
        platform="instagram",
        position_in_session=1,
        shown_at=now + timedelta(seconds=shown_offset_s),
        hidden_at=now + timedelta(seconds=shown_offset_s + 12),
        dwell_ms=12000,
        caption_excerpt="coffee",
        confidence=0.7,
        match_status="unmatched",
    )
    db.add(imp)
    content = ContentRecord(
        user_id=user.id,
        platform="instagram",
        source="dyi",
        external_url=url,
        watched_at=now + timedelta(seconds=watch_offset_s),
        time_precision="second",
        raw_json={"label_values": [{"label": "Caption", "value": "coffee time"}]},
    )
    db.add(content)
    db.commit()
    return user.id, imp.id, content.id


def test_unique_time_window_match(client):
    # reuse client fixture's engine via override — open a session through API seed
    from app.core.db import SessionLocal
    from app.services.ingest import ensure_seed_user

    assert SessionLocal is not None
    db = SessionLocal()
    try:
        ensure_seed_user(db)
        user_id, imp_id, _ = _seed(db)
        result = reconcile_impressions(db, user_id=user_id, window_seconds=120)
        assert result.unique == 1
        imp = db.get(Impression, imp_id)
        assert imp is not None
        assert imp.match_status == "unique"
        assert imp.external_url == "https://www.instagram.com/reel/AAA/"
    finally:
        db.close()


def test_ambiguous_when_two_dyi_in_window(client):
    from app.core.db import SessionLocal
    from app.services.ingest import ensure_seed_user

    assert SessionLocal is not None
    db = SessionLocal()
    try:
        ensure_seed_user(db)
        user_id, imp_id, _ = _seed(db, watch_offset_s=2)
        now = datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc)
        db.add(
            ContentRecord(
                user_id=user_id,
                platform="instagram",
                source="dyi",
                external_url="https://www.instagram.com/reel/BBB/",
                watched_at=now + timedelta(seconds=8),
                time_precision="second",
                raw_json={},
            )
        )
        db.commit()
        # reset impression to unmatched if needed
        imp = db.get(Impression, imp_id)
        assert imp is not None
        imp.match_status = "unmatched"
        imp.external_url = None
        db.commit()
        result = reconcile_impressions(db, user_id=user_id, window_seconds=120)
        assert result.ambiguous == 1
        assert db.get(Impression, imp_id).match_status == "ambiguous"
    finally:
        db.close()
