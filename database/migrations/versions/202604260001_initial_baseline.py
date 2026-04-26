"""Initial database baseline without business tables.

Revision ID: 202604260001
Revises:
Create Date: 2026-04-26 00:00:00
"""
from collections.abc import Sequence

revision: str = "202604260001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
