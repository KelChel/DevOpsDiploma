"""Add users, roles and seed accounts.

Revision ID: 202604260002
Revises: 202604260001
Create Date: 2026-04-26 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202604260002"
down_revision: str | None = "202604260001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_PASSWORD_HASH = "$2b$12$Kqt2sfqNAE8GvfGnfK/smOl9ZED4kzcrDL7RpqtRcwv38hsOw2DF6"


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("position", sa.String(length=160), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    roles_table = sa.table(
        "roles",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
    )
    users_table = sa.table(
        "users",
        sa.column("username", sa.String),
        sa.column("full_name", sa.String),
        sa.column("position", sa.String),
        sa.column("password_hash", sa.String),
    )
    op.bulk_insert(
        roles_table,
        [
            {"code": "employee", "name": "Сотрудник", "description": "Создает заявки и просматривает свои обращения."},
            {"code": "executor", "name": "Исполнитель", "description": "Работает с назначенными заявками."},
            {"code": "admin", "name": "Администратор", "description": "Контролирует заявки, исполнителей и справочники."},
            {"code": "manager", "name": "Руководитель", "description": "Роль для отчетов и демонстрационного плюса."},
        ],
    )
    op.bulk_insert(
        users_table,
        [
            {
                "username": "employee",
                "full_name": "Иван Петров",
                "position": "Сотрудник отделения",
                "password_hash": DEMO_PASSWORD_HASH,
            },
            {
                "username": "executor",
                "full_name": "Мария Соколова",
                "position": "Инженер поддержки",
                "password_hash": DEMO_PASSWORD_HASH,
            },
            {
                "username": "admin",
                "full_name": "Алексей Морозов",
                "position": "Администратор системы",
                "password_hash": DEMO_PASSWORD_HASH,
            },
            {
                "username": "manager",
                "full_name": "Ольга Волкова",
                "position": "Руководитель службы",
                "password_hash": DEMO_PASSWORD_HASH,
            },
        ],
    )
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT users.id, roles.id
        FROM users
        JOIN roles ON roles.code = users.username
        WHERE users.username IN ('employee', 'executor', 'admin', 'manager')
        """
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("roles")
