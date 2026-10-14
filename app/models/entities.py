from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.types import PortableJSON


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Copenhagen")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    devices: Mapped[list[Device]] = relationship(back_populates="user")
    sessions: Mapped[list[Session]] = relationship(back_populates="user")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    platform_os: Mapped[str] = mapped_column(String(32), nullable=False)  # android | ios | other
    label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    logger_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="devices")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    device_id: Mapped[Optional[str]] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    surface: Mapped[str] = mapped_column(String(64), nullable=False, default="for_you")
    end_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    capture_method: Mapped[str] = mapped_column(String(32), nullable=False)
    logger_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    impressions: Mapped[list[Impression]] = relationship(back_populates="session")
    interactions: Mapped[list[Interaction]] = relationship(back_populates="session")


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    device_id: Mapped[Optional[str]] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(PortableJSON, nullable=False, default=dict)
    capture_method: Mapped[str] = mapped_column(String(32), nullable=False)
    # Client-supplied idempotency key (phone JSONL event_id)
    event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)


class Impression(Base):
    __tablename__ = "impressions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    position_in_session: Mapped[int] = mapped_column(Integer, nullable=False)
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    hidden_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dwell_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    creator_handle: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    caption_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    match_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unmatched")

    session: Mapped[Session] = relationship(back_populates="impressions")
    interactions: Mapped[list[Interaction]] = relationship(back_populates="impression")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    impression_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("impressions.id"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    session: Mapped[Session] = relationship(back_populates="interactions")
    impression: Mapped[Optional[Impression]] = relationship(back_populates="interactions")


class ContentRecord(Base):
    __tablename__ = "content_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    creator_handle: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    external_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    watched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    time_precision: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    raw_json: Mapped[dict[str, Any]] = mapped_column(PortableJSON, nullable=False, default=dict)


class ImpressionMatch(Base):
    __tablename__ = "impression_matches"
    __table_args__ = (
        UniqueConstraint("impression_id", "content_record_id", name="uq_impression_content"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    impression_id: Mapped[str] = mapped_column(ForeignKey("impressions.id"), nullable=False, index=True)
    content_record_id: Mapped[str] = mapped_column(
        ForeignKey("content_records.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # unique | ambiguous
