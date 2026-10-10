"""create resume grants

Revision ID: 20261005_0002
Revises: 20261003_0001
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261005_0002"
down_revision: Union[str, Sequence[str], None] = "20261003_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resume_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.String(length=64), nullable=False),
        sa.Column("tid", sa.String(length=64), nullable=False),
        sa.Column("oid", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resume_grants_resume_id", "resume_grants", ["resume_id"])
    op.create_index(
        "uq_resume_grants_oid",
        "resume_grants",
        ["resume_id", "tid", "oid"],
        unique=True,
        postgresql_where=sa.text("oid IS NOT NULL"),
    )
    op.create_index(
        "uq_resume_grants_email",
        "resume_grants",
        ["resume_id", "tid", "email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_resume_grants_email", table_name="resume_grants")
    op.drop_index("uq_resume_grants_oid", table_name="resume_grants")
    op.drop_index("ix_resume_grants_resume_id", table_name="resume_grants")
    op.drop_table("resume_grants")
