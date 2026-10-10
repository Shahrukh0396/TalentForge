"""create users

Revision ID: 20261003_0001
Revises:
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261003_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tid", sa.String(length=64), nullable=False),
        sa.Column("oid", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("preferred_username", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tid", "oid", name="uq_users_tid_oid"),
    )


def downgrade() -> None:
    op.drop_table("users")
