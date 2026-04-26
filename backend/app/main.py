from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authenticate_user, get_current_user, issue_user_token, require_roles
from app.config import get_settings
from app.db import engine, get_db_session
from app.schemas import LoginRequest, RoleRead, TokenResponse, UserRead


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


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
