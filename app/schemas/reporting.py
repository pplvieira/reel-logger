from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    device_id: Optional[str]
    platform: str
    started_at: datetime
    ended_at: Optional[datetime]
    surface: str
    end_reason: Optional[str]
    capture_method: str
    impression_count: int = 0
    local_day: Optional[date] = None


class DaySummary(BaseModel):
    local_day: date
    user_id: str
    timezone: str
    session_count: int
    impression_count: int
    total_dwell_ms: int
    interaction_count: int


class ImpressionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: str
    platform: str
    position_in_session: int
    shown_at: datetime
    hidden_at: Optional[datetime]
    dwell_ms: Optional[int]
    creator_handle: Optional[str]
    caption_excerpt: Optional[str]
    confidence: Optional[float]
    external_url: Optional[str]
    match_status: str
