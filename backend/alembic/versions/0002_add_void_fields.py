"""add void fields to observation_entries

Adds the audit-correct equivalent of "delete": observations can be voided
by an admin (with a reason), but the row + entry_hash + prev_hash stay
immutable so the chain remains verifiable forever.

Revision ID: 0002_add_void_fields
Revises: 0001_initial
Create Date: 2026-05-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_void_fields"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "observation_entries",
        sa.Column("voided", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "observation_entries",
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "observation_entries",
        sa.Column(
            "voided_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "observation_entries",
        sa.Column("void_reason", sa.Text, nullable=True),
    )
    op.create_index("ix_observation_voided", "observation_entries", ["voided"])


def downgrade() -> None:
    op.drop_index("ix_observation_voided", table_name="observation_entries")
    op.drop_column("observation_entries", "void_reason")
    op.drop_column("observation_entries", "voided_by")
    op.drop_column("observation_entries", "voided_at")
    op.drop_column("observation_entries", "voided")
