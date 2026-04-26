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
from app.schemas import (
    LoginRequest,
    RoleRead,
    TicketAssignRequest,
    TicketCategoryRead,
    TicketCreate,
    TicketRead,
    TicketStatusRead,
    TicketStatusUpdateRequest,
    TokenResponse,
    UserRead,
)


settings = get_settings()

ALLOWED_STATUS_TRANSITIONS = {
    "created": {"assigned"},
    "assigned": {"in_progress"},
    "in_progress": {"completed"},
    "completed": {"closed"},
    "closed": set(),
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
    tickets.closed_at
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
            INSERT INTO tickets (title, description, priority, category_id, status_id, created_by_id)
            VALUES (:title, :description, :priority, :category_id, :status_id, :created_by_id)
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
        },
    )
    ticket_id = result.scalar_one()
    await session.commit()
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


@app.patch("/tickets/{ticket_id}/assign", response_model=TicketRead, tags=["tickets"])
async def assign_ticket(
    ticket_id: int,
    payload: TicketAssignRequest,
    _: UserRead = Depends(require_roles("admin")),
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
    await session.commit()
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
    await session.commit()
    return await _load_ticket(session, ticket_id)
