from app.services.importers.dyi import parse_videos_watched_document, parse_videos_watched_record


def test_dyi_with_href():
    record = {
        "timestamp": 1728900000,
        "label_values": [
            {"label": "Author", "value": "creator_one"},
            {"label": "Time", "href": "https://www.instagram.com/reel/ABC123/"},
        ],
    }
    parsed = parse_videos_watched_record(record)
    assert parsed.creator_handle == "creator_one"
    assert parsed.external_url == "https://www.instagram.com/reel/ABC123/"
    assert parsed.watched_at is not None
    assert parsed.time_precision == "second"


def test_dyi_without_href():
    record = {
        "timestamp": 1728900000,
        "label_values": [
            {"label": "Author", "value": "creator_two"},
        ],
    }
    parsed = parse_videos_watched_record(record)
    assert parsed.creator_handle == "creator_two"
    assert parsed.external_url is None
    assert parsed.raw_json is record


def test_dyi_document_array():
    doc = [
        {
            "timestamp": 1728900000,
            "label_values": [{"label": "Author", "value": "a"}],
        },
        {
            "timestamp": 1728900100,
            "label_values": [
                {"label": "Author", "value": "b"},
                {"href": "https://www.instagram.com/reel/XYZ/"},
            ],
        },
    ]
    rows = parse_videos_watched_document(doc)
    assert len(rows) == 2
    assert rows[0].external_url is None
    assert rows[1].external_url == "https://www.instagram.com/reel/XYZ/"
