"""Add raw_events.event_id for client idempotency.

Revision ID: 002_event_id
Revises: 001_initial
Create Date: 2026-10-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_event_id"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("raw_events") as batch:
        batch.add_column(sa.Column("event_id", sa.String(length=36), nullable=True))
    op.create_index("ix_raw_events_event_id", "raw_events", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_raw_events_event_id", table_name="raw_events")
    with op.batch_alter_table("raw_events") as batch:
        batch.drop_column("event_id")
