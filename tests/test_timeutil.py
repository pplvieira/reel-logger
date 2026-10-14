from datetime import datetime, timezone

from app.core.timeutil import local_day


def test_europe_copenhagen_day_bucketing_before_midnight_utc():
    # 2026-10-14 22:30 UTC = 2026-10-15 00:30 in Copenhagen (CEST, UTC+2)
    dt = datetime(2026, 10, 14, 22, 30, tzinfo=timezone.utc)
    assert local_day(dt, "Europe/Copenhagen").isoformat() == "2026-10-15"


def test_europe_copenhagen_same_utc_morning():
    dt = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
    assert local_day(dt, "Europe/Copenhagen").isoformat() == "2026-10-14"
