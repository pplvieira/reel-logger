def test_event_id_dedupe(client):
    user_id = client.seed_user_id
    device = client.post(
        "/devices",
        json={"user_id": user_id, "platform_os": "android", "label": "dedupe"},
    ).json()
    event = {
        "event_id": "11111111-1111-1111-1111-111111111111",
        "type": "session_start",
        "observed_at": "2026-10-14T12:00:00Z",
        "payload": {"surface": "for_you"},
    }
    batch = {
        "schema_version": "1",
        "device_id": device["id"],
        "user_id": user_id,
        "platform": "instagram",
        "capture_method": "accessibility",
        "events": [event, {**event, "type": "session_end", "observed_at": "2026-10-14T12:01:00Z", "event_id": "22222222-2222-2222-2222-222222222222", "payload": {"end_reason": "leave"}}],
    }
    first = client.post("/ingest/events", json=batch)
    assert first.status_code == 200
    assert first.json()["accepted"] == 2
    second = client.post("/ingest/events", json=batch)
    assert second.status_code == 200
    assert second.json()["accepted"] == 0
    assert second.json()["duplicates"] == 2
