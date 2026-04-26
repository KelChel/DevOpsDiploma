from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.schemas import UserRead
from app.security import create_access_token, decode_access_token, verify_password


bearer_scheme = HTTPBearer(auto_error=False)


async def _load_user(session: AsyncSession, username: str) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT
                users.id,
                users.username,
                users.full_name,
                users.position,
                users.password_hash,
                users.is_active,
                COALESCE(array_agg(roles.code ORDER BY roles.code) FILTER (WHERE roles.code IS NOT NULL), '{}') AS roles
            FROM users
            LEFT JOIN user_roles ON user_roles.user_id = users.id
            LEFT JOIN roles ON roles.id = user_roles.role_id
            WHERE users.username = :username
            GROUP BY users.id
            """
        ),
        {"username": username},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def authenticate_user(session: AsyncSession, username: str, password: str) -> UserRead | None:
    user = await _load_user(session, username)
    if not user or not user["is_active"]:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return UserRead(
        id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        position=user["position"],
        is_active=user["is_active"],
        roles=list(user["roles"]),
    )


def issue_user_token(user: UserRead) -> str:
    return create_access_token(subject=user.username, user_id=user.id, roles=user.roles)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRead:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    username = payload.get("sub")
    if not isinstance(username, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    user = await _load_user(session, username)
    if not user or not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")

    return UserRead(
        id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        position=user["position"],
        is_active=user["is_active"],
        roles=list(user["roles"]),
    )


def require_roles(*allowed_roles: str):
    async def dependency(current_user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
        if not set(current_user.roles).intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return dependency
