"""Add ticket lifecycle tables and dictionaries.

Revision ID: 202604260003
Revises: 202604260002
Create Date: 2026-04-26 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202604260003"
down_revision: str | None = "202604260002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=48), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "ticket_statuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("ticket_categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status_id", sa.Integer(), sa.ForeignKey("ticket_statuses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high', 'critical')", name="ck_tickets_priority"),
    )
    op.create_index("ix_tickets_created_by_id", "tickets", ["created_by_id"])
    op.create_index("ix_tickets_assignee_id", "tickets", ["assignee_id"])
    op.create_index("ix_tickets_status_id", "tickets", ["status_id"])
    op.create_index("ix_tickets_category_id", "tickets", ["category_id"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])

    categories_table = sa.table(
        "ticket_categories",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
    )
    statuses_table = sa.table(
        "ticket_statuses",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        categories_table,
        [
            {"code": "it", "name": "ИТ-поддержка", "description": "Рабочие места, учетные записи, оборудование."},
            {"code": "facility", "name": "Хозяйственная служба", "description": "Помещения, мебель, бытовая инфраструктура."},
            {"code": "access", "name": "Доступы", "description": "Запросы на доступ к внутренним системам."},
            {"code": "other", "name": "Другое", "description": "Внутренние обращения вне основных категорий."},
        ],
    )
    op.bulk_insert(
        statuses_table,
        [
            {"code": "created", "name": "Создана", "sort_order": 10},
            {"code": "assigned", "name": "Назначена", "sort_order": 20},
            {"code": "in_progress", "name": "В работе", "sort_order": 30},
            {"code": "completed", "name": "Выполнена", "sort_order": 40},
            {"code": "closed", "name": "Закрыта", "sort_order": 50},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_category_id", table_name="tickets")
    op.drop_index("ix_tickets_status_id", table_name="tickets")
    op.drop_index("ix_tickets_assignee_id", table_name="tickets")
    op.drop_index("ix_tickets_created_by_id", table_name="tickets")
    op.drop_table("tickets")
    op.drop_table("ticket_statuses")
    op.drop_table("ticket_categories")
