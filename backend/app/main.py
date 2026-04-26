from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authenticate_user, get_current_user, issue_user_token, require_roles
from app.config import get_settings
from app.db import engine, get_db_session
from app.notifications import build_notification_provider
from app.schemas import (
    AssigneeLoadItem,
    LoginRequest,
    NotificationLogRead,
    OverdueTicketRead,
    ReportMetricItem,
    ReportSummaryRead,
    RoleRead,
    TicketAssignRequest,
    TicketCategoryRead,
    TicketCommentCreate,
    TicketCommentRead,
    TicketCreate,
    TicketHistoryRead,
    TicketRead,
    TicketStatusRead,
    TicketStatusUpdateRequest,
    TokenResponse,
    UserRead,
)
from app.structured_logging import configure_structured_logging, get_app_logger, safe_log_fields


settings = get_settings()
configure_structured_logging(app_name=settings.app_name, app_env=settings.app_env)
logger = get_app_logger("api")
notification_provider = build_notification_provider(
    settings.notification_provider,
    max_api_base_url=settings.max_api_base_url,
    max_bot_token=settings.max_bot_token,
)

ALLOWED_STATUS_TRANSITIONS = {
    "created": {"assigned"},
    "assigned": {"in_progress"},
    "in_progress": {"completed"},
    "completed": {"closed"},
    "closed": set(),
}

SLA_HOURS_BY_PRIORITY = {
    "low": 72,
    "normal": 48,
    "high": 24,
    "critical": 4,
}

TICKET_SELECT = """
SELECT
    tickets.id,
    tickets.title,
    tickets.description,
    tickets.priority,
    tickets.category_id,
    ticket_categories.code AS category_code,
    ticket_categories.name AS category_name,
    tickets.status_id,
    ticket_statuses.code AS status_code,
    ticket_statuses.name AS status_name,
    tickets.created_by_id,
    creators.full_name AS created_by_name,
    tickets.assignee_id,
    assignees.full_name AS assignee_name,
    tickets.created_at,
    tickets.updated_at,
    tickets.assigned_at,
    tickets.completed_at,
    tickets.closed_at,
    tickets.sla_due_at,
    (
        tickets.sla_due_at < now()
        AND ticket_statuses.code NOT IN ('completed', 'closed')
    ) AS is_overdue
FROM tickets
JOIN ticket_categories ON ticket_categories.id = tickets.category_id
JOIN ticket_statuses ON ticket_statuses.id = tickets.status_id
JOIN users AS creators ON creators.id = tickets.created_by_id
LEFT JOIN users AS assignees ON assignees.id = tickets.assignee_id
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


def _has_role(user: UserRead, role: str) -> bool:
    return role in user.roles


def _can_read_ticket(user: UserRead, ticket: TicketRead) -> bool:
    return _has_role(user, "admin") or ticket.created_by_id == user.id or ticket.assignee_id == user.id


async def _load_ticket(session: AsyncSession, ticket_id: int) -> TicketRead:
    result = await session.execute(text(f"{TICKET_SELECT} WHERE tickets.id = :ticket_id"), {"ticket_id": ticket_id})
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return TicketRead(**dict(row))


async def _get_status_id(session: AsyncSession, status_code: str) -> int:
    result = await session.execute(
        text("SELECT id FROM ticket_statuses WHERE code = :status_code"),
        {"status_code": status_code},
    )
    status_id = result.scalar_one_or_none()
    if status_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown ticket status")
    return int(status_id)


async def _ensure_active_category(session: AsyncSession, category_id: int) -> None:
    result = await session.execute(
        text("SELECT 1 FROM ticket_categories WHERE id = :category_id AND is_active IS TRUE"),
        {"category_id": category_id},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown or inactive ticket category")


async def _ensure_executor(session: AsyncSession, assignee_id: int) -> None:
    result = await session.execute(
        text(
            """
            SELECT 1
            FROM users
            JOIN user_roles ON user_roles.user_id = users.id
            JOIN roles ON roles.id = user_roles.role_id
            WHERE users.id = :assignee_id
              AND users.is_active IS TRUE
              AND roles.code = 'executor'
            """
        ),
        {"assignee_id": assignee_id},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee must be an active executor")


def _sla_hours(priority: str) -> int:
    return SLA_HOURS_BY_PRIORITY[priority]


async def _add_ticket_history(
    session: AsyncSession,
    *,
    ticket_id: int,
    event_type: str,
    actor_id: int | None,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO ticket_history (ticket_id, event_type, field_name, old_value, new_value, actor_id)
            VALUES (:ticket_id, :event_type, :field_name, :old_value, :new_value, :actor_id)
            """
        ),
        {
            "ticket_id": ticket_id,
            "event_type": event_type,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
            "actor_id": actor_id,
        },
    )


def _notification_recipients(ticket: TicketRead, event_type: str, actor_id: int) -> list[int]:
    recipients = {ticket.created_by_id}
    if ticket.assignee_id is not None:
        recipients.add(ticket.assignee_id)
    if event_type == "ticket_assigned" and ticket.assignee_id is not None:
        recipients = {ticket.assignee_id}
    recipients.discard(actor_id)
    return sorted(recipients)


async def _log_notifications(
    session: AsyncSession,
    *,
    ticket: TicketRead,
    event_type: str,
    actor_id: int,
) -> None:
    recipients = _notification_recipients(ticket, event_type, actor_id)
    if not recipients:
        recipients = [ticket.created_by_id]

    for recipient_id in recipients:
        result = await notification_provider.send(event_type=event_type, ticket_id=ticket.id, recipient_user_id=recipient_id)
        await session.execute(
            text(
                """
                INSERT INTO notification_logs (
                    ticket_id,
                    event_type,
                    provider,
                    recipient_user_id,
                    status,
                    error_message,
                    sent_at
                )
                VALUES (
                    :ticket_id,
                    :event_type,
                    :provider,
                    :recipient_user_id,
                    :status,
                    :error_message,
                    :sent_at
                )
                """
            ),
            {
                "ticket_id": ticket.id,
                "event_type": event_type,
                "provider": notification_provider.name,
                "recipient_user_id": recipient_id,
                "status": result.status,
                "error_message": result.error_message,
                "sent_at": result.sent_at,
            },
        )
        if result.status != "sent":
            logger.error(
                "notification_delivery_failed",
                extra={
                    "event": "notification_delivery_failed",
                    **safe_log_fields(
                        ticket_id=ticket.id,
                        notification_event_type=event_type,
                        provider=notification_provider.name,
                        recipient_user_id=recipient_id,
                        error_message=result.error_message,
                    ),
                },
            )


app = FastAPI(
    title="DevOps Ticket System API",
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health(session: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    await session.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "database": "ok",
    }


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    user = await authenticate_user(session, payload.username, payload.password)
    if user is None:
        from fastapi import HTTPException, status

        logger.warning(
            "authorization_failed",
            extra={
                "event": "authorization_failed",
                **safe_log_fields(username=payload.username, reason="invalid_credentials"),
            },
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    return TokenResponse(
        access_token=issue_user_token(user),
        expires_in_minutes=settings.jwt_access_token_expire_minutes,
    )


@app.get("/auth/me", response_model=UserRead, tags=["auth"])
async def read_current_user(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    return current_user


@app.get("/roles", response_model=list[RoleRead], tags=["auth"])
async def read_roles(_: UserRead = Depends(get_current_user)) -> list[RoleRead]:
    return [
        RoleRead(code="employee", name="Сотрудник", description="Создает и закрывает свои заявки."),
        RoleRead(code="executor", name="Исполнитель", description="Обрабатывает назначенные заявки."),
        RoleRead(code="admin", name="Администратор", description="Назначает исполнителей и контролирует справочники."),
        RoleRead(code="manager", name="Руководитель", description="Роль зафиксирована для отчетов и демонстрационного плюса."),
    ]


@app.get("/admin/users", response_model=list[UserRead], tags=["auth"])
async def read_users(
    _: UserRead = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserRead]:
    result = await session.execute(
        text(
            """
            SELECT
                users.id,
                users.username,
                users.full_name,
                users.position,
                users.is_active,
                COALESCE(array_agg(roles.code ORDER BY roles.code) FILTER (WHERE roles.code IS NOT NULL), '{}') AS roles
            FROM users
            LEFT JOIN user_roles ON user_roles.user_id = users.id
            LEFT JOIN roles ON roles.id = user_roles.role_id
            GROUP BY users.id
            ORDER BY users.id
            """
        )
    )
    return [UserRead(**dict(row)) for row in result.mappings().all()]


@app.get("/ticket-categories", response_model=list[TicketCategoryRead], tags=["tickets"])
async def read_ticket_categories(_: UserRead = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> list[TicketCategoryRead]:
    result = await session.execute(
        text(
            """
            SELECT id, code, name, description, is_active
            FROM ticket_categories
            WHERE is_active IS TRUE
            ORDER BY name
            """
        )
    )
    return [TicketCategoryRead(**dict(row)) for row in result.mappings().all()]


@app.get("/ticket-statuses", response_model=list[TicketStatusRead], tags=["tickets"])
async def read_ticket_statuses(_: UserRead = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> list[TicketStatusRead]:
    result = await session.execute(
        text(
            """
            SELECT id, code, name, sort_order
            FROM ticket_statuses
            ORDER BY sort_order
            """
        )
    )
    return [TicketStatusRead(**dict(row)) for row in result.mappings().all()]


@app.get("/reports/summary", response_model=ReportSummaryRead, tags=["reports"])
async def read_report_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    _: UserRead = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_db_session),
) -> ReportSummaryRead:
    clauses = []
    join_clauses = []
    params: dict[str, Any] = {}
    if date_from:
        clauses.append("tickets.created_at >= :date_from")
        join_clauses.append("tickets.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("tickets.created_at < (CAST(:date_to AS date) + INTERVAL '1 day')")
        join_clauses.append("tickets.created_at < (CAST(:date_to AS date) + INTERVAL '1 day')")
        params["date_to"] = date_to
    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    join_sql = f" AND {' AND '.join(join_clauses)}" if join_clauses else ""

    total_result = await session.execute(
        text(
            f"""
            SELECT
                COUNT(*) AS total_count,
                COUNT(*) FILTER (WHERE ticket_statuses.code NOT IN ('completed', 'closed')) AS open_count,
                COUNT(*) FILTER (WHERE ticket_statuses.code IN ('completed', 'closed')) AS closed_count,
                COUNT(*) FILTER (
                    WHERE tickets.sla_due_at < now()
                      AND ticket_statuses.code NOT IN ('completed', 'closed')
                ) AS overdue_count
            FROM tickets
            JOIN ticket_statuses ON ticket_statuses.id = tickets.status_id
            {where_sql}
            """
        ),
        params,
    )
    totals = dict(total_result.mappings().one())

    status_result = await session.execute(
        text(
            f"""
            SELECT ticket_statuses.code, ticket_statuses.name, COUNT(tickets.id) AS count
            FROM ticket_statuses
            LEFT JOIN tickets ON tickets.status_id = ticket_statuses.id {join_sql}
            GROUP BY ticket_statuses.id
            ORDER BY ticket_statuses.sort_order
            """
        ),
        params,
    )
    category_result = await session.execute(
        text(
            f"""
            SELECT ticket_categories.code, ticket_categories.name, COUNT(tickets.id) AS count
            FROM ticket_categories
            LEFT JOIN tickets ON tickets.category_id = ticket_categories.id {join_sql}
            GROUP BY ticket_categories.id
            ORDER BY ticket_categories.name
            """
        ),
        params,
    )
    assignee_result = await session.execute(
        text(
            f"""
            SELECT
                tickets.assignee_id,
                COALESCE(users.full_name, 'Не назначен') AS assignee_name,
                COUNT(*) FILTER (WHERE ticket_statuses.code NOT IN ('completed', 'closed')) AS open_count,
                COUNT(*) FILTER (
                    WHERE tickets.sla_due_at < now()
                      AND ticket_statuses.code NOT IN ('completed', 'closed')
                ) AS overdue_count
            FROM tickets
            JOIN ticket_statuses ON ticket_statuses.id = tickets.status_id
            LEFT JOIN users ON users.id = tickets.assignee_id
            {where_sql}
            GROUP BY tickets.assignee_id, users.full_name
            ORDER BY overdue_count DESC, open_count DESC, assignee_name
            """
        ),
        params,
    )
    overdue_result = await session.execute(
        text(
            f"""
            SELECT
                tickets.id,
                tickets.title,
                tickets.priority,
                ticket_statuses.code AS status_code,
                ticket_statuses.name AS status_name,
                ticket_categories.name AS category_name,
                assignees.full_name AS assignee_name,
                tickets.created_at,
                tickets.sla_due_at
            FROM tickets
            JOIN ticket_statuses ON ticket_statuses.id = tickets.status_id
            JOIN ticket_categories ON ticket_categories.id = tickets.category_id
            LEFT JOIN users AS assignees ON assignees.id = tickets.assignee_id
            {where_sql}
            {"AND" if where_sql else "WHERE"} tickets.sla_due_at < now()
              AND ticket_statuses.code NOT IN ('completed', 'closed')
            ORDER BY tickets.sla_due_at ASC
            LIMIT 20
            """
        ),
        params,
    )

    category_rows = [
        ReportMetricItem(**dict(row))
        for row in category_result.mappings().all()
    ]

    return ReportSummaryRead(
        total_count=totals["total_count"],
        open_count=totals["open_count"],
        closed_count=totals["closed_count"],
        overdue_count=totals["overdue_count"],
        by_status=[ReportMetricItem(**dict(row)) for row in status_result.mappings().all()],
        by_category=category_rows,
        assignee_load=[AssigneeLoadItem(**dict(row)) for row in assignee_result.mappings().all()],
        overdue_tickets=[OverdueTicketRead(**dict(row)) for row in overdue_result.mappings().all()],
    )


@app.get("/tickets", response_model=list[TicketRead], tags=["tickets"])
async def read_tickets(
    status_code: str | None = Query(default=None, max_length=32),
    category_id: int | None = Query(default=None, gt=0),
    assignee_id: int | None = Query(default=None, gt=0),
    date_from: date | None = None,
    date_to: date | None = None,
    current_user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TicketRead]:
    clauses = []
    params: dict[str, Any] = {}

    if _has_role(current_user, "admin"):
        pass
    elif _has_role(current_user, "executor"):
        clauses.append("tickets.assignee_id = :current_user_id")
        params["current_user_id"] = current_user.id
    elif _has_role(current_user, "employee"):
        clauses.append("tickets.created_by_id = :current_user_id")
        params["current_user_id"] = current_user.id
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tickets are not available for this role")

    if status_code:
        clauses.append("ticket_statuses.code = :status_code")
        params["status_code"] = status_code
    if category_id:
        clauses.append("tickets.category_id = :category_id")
        params["category_id"] = category_id
    if assignee_id:
        clauses.append("tickets.assignee_id = :assignee_id")
        params["assignee_id"] = assignee_id
    if date_from:
        clauses.append("tickets.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("tickets.created_at < (CAST(:date_to AS date) + INTERVAL '1 day')")
        params["date_to"] = date_to

    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    result = await session.execute(text(f"{TICKET_SELECT}{where_sql} ORDER BY tickets.created_at DESC, tickets.id DESC"), params)
    return [TicketRead(**dict(row)) for row in result.mappings().all()]


@app.post("/tickets", response_model=TicketRead, status_code=status.HTTP_201_CREATED, tags=["tickets"])
async def create_ticket(
    payload: TicketCreate,
    current_user: UserRead = Depends(require_roles("employee")),
    session: AsyncSession = Depends(get_db_session),
) -> TicketRead:
    await _ensure_active_category(session, payload.category_id)
    status_id = await _get_status_id(session, "created")
    result = await session.execute(
        text(
            """
            INSERT INTO tickets (title, description, priority, category_id, status_id, created_by_id, sla_due_at)
            VALUES (
                :title,
                :description,
                :priority,
                :category_id,
                :status_id,
                :created_by_id,
                now() + (:sla_hours * INTERVAL '1 hour')
            )
            RETURNING id
            """
        ),
        {
            "title": payload.title,
            "description": payload.description,
            "priority": payload.priority,
            "category_id": payload.category_id,
            "status_id": status_id,
            "created_by_id": current_user.id,
            "sla_hours": _sla_hours(payload.priority),
        },
    )
    ticket_id = result.scalar_one()
    await _add_ticket_history(
        session,
        ticket_id=int(ticket_id),
        event_type="ticket_created",
        field_name="status",
        old_value=None,
        new_value="created",
        actor_id=current_user.id,
    )
    ticket = await _load_ticket(session, int(ticket_id))
    await _log_notifications(session, ticket=ticket, event_type="ticket_created", actor_id=current_user.id)
    await session.commit()
    logger.info(
        "ticket_created",
        extra={
            "event": "ticket_created",
            **safe_log_fields(ticket_id=int(ticket_id), actor_id=current_user.id, category_id=payload.category_id, priority=payload.priority),
        },
    )
    return await _load_ticket(session, int(ticket_id))


@app.get("/tickets/{ticket_id}", response_model=TicketRead, tags=["tickets"])
async def read_ticket(
    ticket_id: int,
    current_user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TicketRead:
    ticket = await _load_ticket(session, ticket_id)
    if not _can_read_ticket(current_user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ticket is not available")
    return ticket


@app.get("/tickets/{ticket_id}/history", response_model=list[TicketHistoryRead], tags=["tickets"])
async def read_ticket_history(
    ticket_id: int,
    current_user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TicketHistoryRead]:
    ticket = await _load_ticket(session, ticket_id)
    if not _can_read_ticket(current_user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ticket is not available")

    result = await session.execute(
        text(
            """
            SELECT
                ticket_history.id,
                ticket_history.ticket_id,
                ticket_history.event_type,
                ticket_history.field_name,
                ticket_history.old_value,
                ticket_history.new_value,
                ticket_history.actor_id,
                users.full_name AS actor_name,
                ticket_history.created_at
            FROM ticket_history
            LEFT JOIN users ON users.id = ticket_history.actor_id
            WHERE ticket_history.ticket_id = :ticket_id
            ORDER BY ticket_history.created_at DESC, ticket_history.id DESC
            """
        ),
        {"ticket_id": ticket_id},
    )
    return [TicketHistoryRead(**dict(row)) for row in result.mappings().all()]


@app.get("/tickets/{ticket_id}/comments", response_model=list[TicketCommentRead], tags=["tickets"])
async def read_ticket_comments(
    ticket_id: int,
    current_user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TicketCommentRead]:
    ticket = await _load_ticket(session, ticket_id)
    if not _can_read_ticket(current_user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ticket is not available")

    result = await session.execute(
        text(
            """
            SELECT
                ticket_comments.id,
                ticket_comments.ticket_id,
                ticket_comments.author_id,
                users.full_name AS author_name,
                ticket_comments.body,
                ticket_comments.created_at
            FROM ticket_comments
            JOIN users ON users.id = ticket_comments.author_id
            WHERE ticket_comments.ticket_id = :ticket_id
            ORDER BY ticket_comments.created_at ASC, ticket_comments.id ASC
            """
        ),
        {"ticket_id": ticket_id},
    )
    return [TicketCommentRead(**dict(row)) for row in result.mappings().all()]


@app.post("/tickets/{ticket_id}/comments", response_model=TicketCommentRead, status_code=status.HTTP_201_CREATED, tags=["tickets"])
async def create_ticket_comment(
    ticket_id: int,
    payload: TicketCommentCreate,
    current_user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TicketCommentRead:
    ticket = await _load_ticket(session, ticket_id)
    if not _can_read_ticket(current_user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ticket is not available")

    result = await session.execute(
        text(
            """
            INSERT INTO ticket_comments (ticket_id, author_id, body)
            VALUES (:ticket_id, :author_id, :body)
            RETURNING id
            """
        ),
        {"ticket_id": ticket_id, "author_id": current_user.id, "body": payload.body},
    )
    comment_id = result.scalar_one()
    await _add_ticket_history(
        session,
        ticket_id=ticket_id,
        event_type="comment_added",
        field_name="comment",
        old_value=None,
        new_value=str(comment_id),
        actor_id=current_user.id,
    )
    await _log_notifications(session, ticket=ticket, event_type="comment_added", actor_id=current_user.id)
    await session.commit()

    result = await session.execute(
        text(
            """
            SELECT
                ticket_comments.id,
                ticket_comments.ticket_id,
                ticket_comments.author_id,
                users.full_name AS author_name,
                ticket_comments.body,
                ticket_comments.created_at
            FROM ticket_comments
            JOIN users ON users.id = ticket_comments.author_id
            WHERE ticket_comments.id = :comment_id
            """
        ),
        {"comment_id": comment_id},
    )
    return TicketCommentRead(**dict(result.mappings().one()))


@app.get("/tickets/{ticket_id}/notifications", response_model=list[NotificationLogRead], tags=["tickets"])
async def read_ticket_notifications(
    ticket_id: int,
    current_user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[NotificationLogRead]:
    ticket = await _load_ticket(session, ticket_id)
    if not _can_read_ticket(current_user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ticket is not available")

    result = await session.execute(
        text(
            """
            SELECT
                notification_logs.id,
                notification_logs.ticket_id,
                notification_logs.event_type,
                notification_logs.provider,
                notification_logs.recipient_user_id,
                users.full_name AS recipient_name,
                notification_logs.status,
                notification_logs.error_message,
                notification_logs.created_at,
                notification_logs.sent_at
            FROM notification_logs
            LEFT JOIN users ON users.id = notification_logs.recipient_user_id
            WHERE notification_logs.ticket_id = :ticket_id
            ORDER BY notification_logs.created_at DESC, notification_logs.id DESC
            """
        ),
        {"ticket_id": ticket_id},
    )
    return [NotificationLogRead(**dict(row)) for row in result.mappings().all()]


@app.patch("/tickets/{ticket_id}/assign", response_model=TicketRead, tags=["tickets"])
async def assign_ticket(
    ticket_id: int,
    payload: TicketAssignRequest,
    current_user: UserRead = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> TicketRead:
    ticket = await _load_ticket(session, ticket_id)
    if ticket.status_code not in {"created", "assigned", "in_progress"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket cannot be assigned in current status")

    await _ensure_executor(session, payload.assignee_id)
    status_id = await _get_status_id(session, "assigned" if ticket.status_code == "created" else ticket.status_code)
    await session.execute(
        text(
            """
            UPDATE tickets
            SET assignee_id = :assignee_id,
                status_id = :status_id,
                assigned_at = COALESCE(assigned_at, now()),
                updated_at = now()
            WHERE id = :ticket_id
            """
        ),
        {"ticket_id": ticket_id, "assignee_id": payload.assignee_id, "status_id": status_id},
    )
    await _add_ticket_history(
        session,
        ticket_id=ticket_id,
        event_type="ticket_assigned",
        field_name="assignee_id",
        old_value=str(ticket.assignee_id) if ticket.assignee_id is not None else None,
        new_value=str(payload.assignee_id),
        actor_id=current_user.id,
    )
    if ticket.status_code == "created":
        await _add_ticket_history(
            session,
            ticket_id=ticket_id,
            event_type="status_changed",
            field_name="status",
            old_value=ticket.status_code,
            new_value="assigned",
            actor_id=current_user.id,
        )
    updated_ticket = await _load_ticket(session, ticket_id)
    await _log_notifications(session, ticket=updated_ticket, event_type="ticket_assigned", actor_id=current_user.id)
    await session.commit()
    logger.info(
        "ticket_assigned",
        extra={
            "event": "ticket_assigned",
            **safe_log_fields(ticket_id=ticket_id, actor_id=current_user.id, assignee_id=payload.assignee_id),
        },
    )
    return await _load_ticket(session, ticket_id)


@app.patch("/tickets/{ticket_id}/status", response_model=TicketRead, tags=["tickets"])
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TicketRead:
    ticket = await _load_ticket(session, ticket_id)
    target_status = payload.status_code

    if target_status == "assigned":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use ticket assignment endpoint")
    if target_status not in ALLOWED_STATUS_TRANSITIONS.get(ticket.status_code, set()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status transition is not allowed")
    if target_status in {"in_progress", "completed"} and (not _has_role(current_user, "executor") or ticket.assignee_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assigned executor can change this status")
    if target_status == "closed" and ticket.created_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only ticket requester can close completed ticket")

    status_id = await _get_status_id(session, target_status)
    timestamp_sql = ""
    if target_status == "completed":
        timestamp_sql = ", completed_at = now()"
    elif target_status == "closed":
        timestamp_sql = ", closed_at = now()"

    await session.execute(
        text(
            f"""
            UPDATE tickets
            SET status_id = :status_id,
                updated_at = now()
                {timestamp_sql}
            WHERE id = :ticket_id
            """
        ),
        {"ticket_id": ticket_id, "status_id": status_id},
    )
    await _add_ticket_history(
        session,
        ticket_id=ticket_id,
        event_type="status_changed",
        field_name="status",
        old_value=ticket.status_code,
        new_value=target_status,
        actor_id=current_user.id,
    )
    updated_ticket = await _load_ticket(session, ticket_id)
    await _log_notifications(session, ticket=updated_ticket, event_type="status_changed", actor_id=current_user.id)
    await session.commit()
    logger.info(
        "ticket_status_changed",
        extra={
            "event": "ticket_status_changed",
            **safe_log_fields(ticket_id=ticket_id, actor_id=current_user.id, old_status=ticket.status_code, new_status=target_status),
        },
    )
    return await _load_ticket(session, ticket_id)
