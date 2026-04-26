"""Add SLA fields and demonstration report data.

Revision ID: 202604260005
Revises: 202604260004
Create Date: 2026-04-26 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202604260005"
down_revision: str | None = "202604260004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE tickets
        SET sla_due_at = created_at +
            CASE priority
                WHEN 'critical' THEN INTERVAL '4 hours'
                WHEN 'high' THEN INTERVAL '24 hours'
                WHEN 'normal' THEN INTERVAL '48 hours'
                ELSE INTERVAL '72 hours'
            END
        WHERE sla_due_at IS NULL
        """
    )
    op.alter_column("tickets", "sla_due_at", nullable=False)
    op.create_index("ix_tickets_sla_due_at", "tickets", ["sla_due_at"])

    op.execute(
        """
        WITH demo_tickets AS (
            INSERT INTO tickets (
                title,
                description,
                priority,
                category_id,
                status_id,
                created_by_id,
                assignee_id,
                created_at,
                updated_at,
                assigned_at,
                completed_at,
                closed_at,
                sla_due_at
            )
            VALUES
                (
                    'Демо: срочный доступ к рабочей системе',
                    'Демонстрационная заявка без медицинских данных пациентов.',
                    'critical',
                    (SELECT id FROM ticket_categories WHERE code = 'access'),
                    (SELECT id FROM ticket_statuses WHERE code = 'in_progress'),
                    (SELECT id FROM users WHERE username = 'employee'),
                    (SELECT id FROM users WHERE username = 'executor'),
                    now() - INTERVAL '9 hours',
                    now() - INTERVAL '2 hours',
                    now() - INTERVAL '8 hours',
                    NULL,
                    NULL,
                    now() - INTERVAL '5 hours'
                ),
                (
                    'Демо: замена оборудования на посту',
                    'Демонстрационная заявка для проверки распределения по категориям.',
                    'high',
                    (SELECT id FROM ticket_categories WHERE code = 'it'),
                    (SELECT id FROM ticket_statuses WHERE code = 'assigned'),
                    (SELECT id FROM users WHERE username = 'employee'),
                    (SELECT id FROM users WHERE username = 'executor'),
                    now() - INTERVAL '12 hours',
                    now() - INTERVAL '11 hours',
                    now() - INTERVAL '11 hours',
                    NULL,
                    NULL,
                    now() + INTERVAL '12 hours'
                ),
                (
                    'Демо: заявка закрыта после выполнения',
                    'Демонстрационная закрытая заявка для отчетов за период.',
                    'normal',
                    (SELECT id FROM ticket_categories WHERE code = 'facility'),
                    (SELECT id FROM ticket_statuses WHERE code = 'closed'),
                    (SELECT id FROM users WHERE username = 'employee'),
                    (SELECT id FROM users WHERE username = 'executor'),
                    now() - INTERVAL '3 days',
                    now() - INTERVAL '2 days',
                    now() - INTERVAL '3 days',
                    now() - INTERVAL '2 days 6 hours',
                    now() - INTERVAL '2 days',
                    now() - INTERVAL '1 day'
                )
            RETURNING id, created_by_id
        )
        INSERT INTO ticket_history (ticket_id, event_type, field_name, old_value, new_value, actor_id, created_at)
        SELECT id, 'ticket_created', 'status', NULL, 'created', created_by_id, now() - INTERVAL '9 hours'
        FROM demo_tickets
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM tickets
        WHERE title IN (
            'Демо: срочный доступ к рабочей системе',
            'Демо: замена оборудования на посту',
            'Демо: заявка закрыта после выполнения'
        )
        """
    )
    op.drop_index("ix_tickets_sla_due_at", table_name="tickets")
    op.drop_column("tickets", "sla_due_at")
