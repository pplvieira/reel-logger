from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

Platform = Literal["instagram", "tiktok", "youtube_shorts"]
CaptureMethod = Literal[
    "accessibility",
    "screen_time",
    "manual",
    "dyi",
    "share_sheet",
]
SemanticEventType = Literal[
    "session_start",
    "session_end",
    "reel_shown",
    "reel_hidden",
    "interaction",
]
# Debug / unknown types are allowed as plain strings; sessionize ignores them.
InteractionKind = Literal[
    "like",
    "unlike",
    "comment_open",
    "comment_send",
    "share_open",
    "send",
    "save",
    "profile_open",
]


class EventIn(BaseModel):
    """One semantic (or debug) event from a client.

    Extra top-level OS fields are rejected. Debug bags belong inside payload
    under a non-required key if a calibration build needs them.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., min_length=1, max_length=64)
    observed_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def payload_must_be_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value is None:
            return {}
        return value


class EventBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1"
    device_id: str
    user_id: str
    platform: Platform
    capture_method: CaptureMethod
    logger_version: Optional[str] = None
    events: list[EventIn] = Field(default_factory=list)


class IngestResult(BaseModel):
    accepted: int
    sessionized_sessions: int
    sessionized_impressions: int
    sessionized_interactions: int
    ignored_event_types: list[str] = Field(default_factory=list)


class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    platform_os: Literal["android", "ios", "other"]
    label: str = ""
    logger_version: Optional[str] = None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    platform_os: str
    label: str
    logger_version: Optional[str]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    timezone: str
