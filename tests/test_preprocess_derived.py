from pathlib import Path

from app.services.derived.preprocess import (
    detect_era,
    extract_identity_from_texts,
    run_preprocess,
)


def test_extract_reel_by_beats_ui_tokens():
    texts = [
        "Like",
        "1199",
        "Comment",
        "Repost",
        "SeekBar",
        "Reel by wildlensviews1. Double-tap to play or pause.",
        "Home",
    ]
    creator, _, method, conf = extract_identity_from_texts(texts)
    assert creator == "wildlensviews1"
    assert method == "raw_reel_by"
    assert conf >= 0.75


def test_detect_era_b():
    events = [
        {"type": "reel_shown", "observed_at": "2026-10-15T09:00:00Z", "payload": {}},
        {
            "type": "raw_a11y",
            "observed_at": "2026-10-15T09:00:00Z",
            "payload": {"texts_sample": ["Reel by x. Double-tap to play or pause."]},
        },
    ]
    assert detect_era(events) == "B"


def test_preprocess_writes_manifest(tmp_path: Path):
    jsonl = tmp_path / "events.jsonl"
    jsonl.write_text(
        "\n".join(
            [
                '{"event_id":"1","type":"session_start","observed_at":"2026-10-15T09:00:00.000Z","payload":{"surface":"for_you"}}',
                '{"event_id":"2","type":"raw_a11y","observed_at":"2026-10-15T09:00:00.100Z","payload":{"texts_sample":["Reel by alice. Double-tap to play or pause.","Like","Home"]}}',
                '{"event_id":"3","type":"reel_shown","observed_at":"2026-10-15T09:00:00.100Z","payload":{"creator_handle":"Repost","caption_excerpt":"x","identity_source":"on_device_heuristic_v1"}}',
                '{"event_id":"4","type":"reel_hidden","observed_at":"2026-10-15T09:00:05.100Z","payload":{}}',
                '{"event_id":"5","type":"session_end","observed_at":"2026-10-15T09:00:05.100Z","payload":{"end_reason":"leave"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "derived"
    result = run_preprocess(jsonl, out_root=out, min_dwell_ms=2000.0)
    assert result.schema_era == "B"
    assert result.impressions_path.exists()
    text = result.impressions_path.read_text(encoding="utf-8")
    assert "alice" in text
    assert "raw_reel_by" in text
    assert result.manifest_path.exists()
