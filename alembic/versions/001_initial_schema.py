"""Initial schema from SQLAlchemy models.

Revision ID: 001_initial
Revises:
Create Date: 2026-10-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("platform_os", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("logger_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("surface", sa.String(length=64), nullable=False),
        sa.Column("end_reason", sa.String(length=64), nullable=True),
        sa.Column("capture_method", sa.String(length=32), nullable=False),
        sa.Column("logger_version", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_device_id", "sessions", ["device_id"])
    op.create_index("ix_sessions_platform", "sessions", ["platform"])
    op.create_index("ix_sessions_started_at", "sessions", ["started_at"])

    op.create_table(
        "raw_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("capture_method", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_events_user_id", "raw_events", ["user_id"])
    op.create_index("ix_raw_events_device_id", "raw_events", ["device_id"])
    op.create_index("ix_raw_events_platform", "raw_events", ["platform"])
    op.create_index("ix_raw_events_observed_at", "raw_events", ["observed_at"])
    op.create_index("ix_raw_events_type", "raw_events", ["type"])

    op.create_table(
        "impressions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("position_in_session", sa.Integer(), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dwell_ms", sa.Integer(), nullable=True),
        sa.Column("creator_handle", sa.String(length=256), nullable=True),
        sa.Column("caption_excerpt", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("match_status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_impressions_session_id", "impressions", ["session_id"])
    op.create_index("ix_impressions_user_id", "impressions", ["user_id"])
    op.create_index("ix_impressions_platform", "impressions", ["platform"])
    op.create_index("ix_impressions_shown_at", "impressions", ["shown_at"])
    op.create_index("ix_impressions_creator_handle", "impressions", ["creator_handle"])

    op.create_table(
        "interactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("impression_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["impression_id"], ["impressions.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interactions_session_id", "interactions", ["session_id"])
    op.create_index("ix_interactions_impression_id", "interactions", ["impression_id"])
    op.create_index("ix_interactions_user_id", "interactions", ["user_id"])
    op.create_index("ix_interactions_platform", "interactions", ["platform"])
    op.create_index("ix_interactions_observed_at", "interactions", ["observed_at"])

    op.create_table(
        "content_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("creator_handle", sa.String(length=256), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("watched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_precision", sa.String(length=32), nullable=False),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_records_user_id", "content_records", ["user_id"])
    op.create_index("ix_content_records_platform", "content_records", ["platform"])
    op.create_index("ix_content_records_creator_handle", "content_records", ["creator_handle"])
    op.create_index("ix_content_records_watched_at", "content_records", ["watched_at"])

    op.create_table(
        "impression_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("impression_id", sa.String(length=36), nullable=False),
        sa.Column("content_record_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["content_record_id"], ["content_records.id"]),
        sa.ForeignKeyConstraint(["impression_id"], ["impressions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("impression_id", "content_record_id", name="uq_impression_content"),
    )
    op.create_index("ix_impression_matches_impression_id", "impression_matches", ["impression_id"])
    op.create_index(
        "ix_impression_matches_content_record_id", "impression_matches", ["content_record_id"]
    )


def downgrade() -> None:
    op.drop_table("impression_matches")
    op.drop_table("content_records")
    op.drop_table("interactions")
    op.drop_table("impressions")
    op.drop_table("raw_events")
    op.drop_table("sessions")
    op.drop_table("devices")
    op.drop_table("users")
