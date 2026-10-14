def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ingest_roundtrip(client):
    user_id = client.seed_user_id
    device = client.post(
        "/devices",
        json={
            "user_id": user_id,
            "platform_os": "android",
            "label": "test-phone",
            "logger_version": "0.0.1-test",
        },
    )
    assert device.status_code == 200
    device_id = device.json()["id"]

    batch = {
        "schema_version": "1",
        "device_id": device_id,
        "user_id": user_id,
        "platform": "instagram",
        "capture_method": "accessibility",
        "events": [
            {
                "type": "session_start",
                "observed_at": "2026-10-14T10:00:00Z",
                "payload": {"surface": "for_you"},
            },
            {
                "type": "raw_a11y",
                "observed_at": "2026-10-14T10:00:01Z",
                "payload": {"debug": True},
            },
            {
                "type": "reel_shown",
                "observed_at": "2026-10-14T10:00:02Z",
                "payload": {"creator_handle": "demo", "confidence": 0.7},
            },
            {
                "type": "reel_hidden",
                "observed_at": "2026-10-14T10:00:12Z",
                "payload": {},
            },
            {
                "type": "session_end",
                "observed_at": "2026-10-14T10:01:00Z",
                "payload": {"end_reason": "leave"},
            },
        ],
    }
    ingest = client.post("/ingest/events", json=batch)
    assert ingest.status_code == 200, ingest.text
    body = ingest.json()
    assert body["accepted"] == 5
    assert body["sessionized_sessions"] == 1
    assert body["sessionized_impressions"] == 1
    assert "raw_a11y" in body["ignored_event_types"]

    sessions = client.get("/sessions", params={"user_id": user_id})
    assert sessions.status_code == 200
    assert len(sessions.json()) == 1
    assert sessions.json()[0]["impression_count"] == 1
