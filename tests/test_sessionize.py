from datetime import datetime, timedelta, timezone

from app.services.sessionize import sessionize

UTC = timezone.utc


def _e(etype: str, minutes: float, **payload):
    base = datetime(2026, 10, 14, 10, 0, tzinfo=UTC)
    return {
        "type": etype,
        "observed_at": base + timedelta(minutes=minutes),
        "payload": payload,
    }


def test_two_visits_same_day_are_two_sessions():
    # Gap > 60s between visits
    events = [
        _e("session_start", 0, surface="for_you"),
        _e("reel_shown", 0.1, creator_handle="a", confidence=0.9),
        _e("reel_hidden", 0.2),
        _e("session_end", 0.3, end_reason="leave"),
        _e("session_start", 5.0, surface="for_you"),
        _e("reel_shown", 5.1, creator_handle="b"),
        _e("reel_hidden", 5.3),
        _e("session_end", 5.4, end_reason="leave"),
    ]
    result = sessionize(
        events,
        user_id="u1",
        device_id="d1",
        platform="instagram",
        capture_method="accessibility",
        session_gap_seconds=60,
    )
    assert len(result.sessions) == 2
    assert len(result.impressions) == 2
    assert result.impressions[0].dwell_ms == 6000  # 0.1 min = 6s
    assert result.impressions[0].position_in_session == 1
    assert result.impressions[1].creator_handle == "b"


def test_session_with_zero_impressions():
    events = [
        _e("session_start", 0, surface="for_you"),
        _e("session_end", 2.0, end_reason="leave"),
    ]
    result = sessionize(
        events,
        user_id="u1",
        device_id="d1",
        platform="instagram",
        capture_method="screen_time",
    )
    assert len(result.sessions) == 1
    assert len(result.impressions) == 0


def test_raw_a11y_ignored_but_sessionizes():
    events = [
        _e("session_start", 0),
        {
            "type": "raw_a11y",
            "observed_at": datetime(2026, 10, 14, 10, 0, 5, tzinfo=UTC),
            "payload": {"nodes": ["should-not-affect-sessionize"]},
        },
        _e("reel_shown", 0.1, creator_handle="x"),
        _e("interaction", 0.15, kind="like"),
        _e("reel_hidden", 0.2),
        _e("session_end", 0.3, end_reason="leave"),
    ]
    result = sessionize(
        events,
        user_id="u1",
        device_id="d1",
        platform="instagram",
        capture_method="accessibility",
    )
    assert result.ignored_event_types == ["raw_a11y"]
    assert len(result.sessions) == 1
    assert len(result.impressions) == 1
    assert len(result.interactions) == 1
    assert result.interactions[0].kind == "like"


def test_gap_splits_without_explicit_session_end():
    events = [
        _e("reel_shown", 0, creator_handle="a"),
        _e("reel_hidden", 0.1),
        # 3 minutes later → gap
        _e("reel_shown", 3.0, creator_handle="b"),
        _e("reel_hidden", 3.1),
    ]
    result = sessionize(
        events,
        user_id="u1",
        device_id="d1",
        platform="instagram",
        capture_method="accessibility",
        session_gap_seconds=60,
    )
    assert len(result.sessions) == 2
    assert result.sessions[0].end_reason == "gap"
