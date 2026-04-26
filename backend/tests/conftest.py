from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
import asyncio
import os
import sys

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("NOTIFICATION_PROVIDER", "mock")

from app.db import AsyncSessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


DEMO_PASSWORD = "password"


def pytest_configure(config):
    config.addinivalue_line("markers", "api: API tests through the FastAPI ASGI app")
    config.addinivalue_line("markers", "integration: tests that require PostgreSQL and migrations")
    config.addinivalue_line("markers", "security: access-control and data-isolation tests")
    config.addinivalue_line("markers", "smoke: minimal availability checks")


def _run_migrations() -> None:
    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(REPO_ROOT / "database" / "migrations"))
    command.upgrade(alembic_config, "head")


async def _clean_ticket_data() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    notification_logs,
                    ticket_comments,
                    ticket_history,
                    tickets
                RESTART IDENTITY CASCADE
                """
            )
        )
        await session.commit()
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    _run_migrations()
    asyncio.run(_clean_ticket_data())
    yield
    asyncio.run(_clean_ticket_data())


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncGenerator[None, None]:
    await _clean_ticket_data()
    yield
    await _clean_ticket_data()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> Callable[[str], Awaitable[dict[str, str]]]:
    async def _auth_headers(username: str) -> dict[str, str]:
        response = await client.post(
            "/auth/login",
            json={"username": username, "password": DEMO_PASSWORD},
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest_asyncio.fixture
async def default_category_id(client: AsyncClient, auth_headers: Callable[[str], Awaitable[dict[str, str]]]) -> int:
    response = await client.get("/ticket-categories", headers=await auth_headers("employee"))
    response.raise_for_status()
    return response.json()[0]["id"]


async def create_ticket(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    category_id: int,
) -> dict:
    response = await client.post(
        "/tickets",
        headers=await auth_headers("employee"),
        json={
            "title": "Не работает доступ к внутреннему сервису",
            "description": "Проверочное обращение без медицинских данных пациентов.",
            "category_id": category_id,
            "priority": "normal",
        },
    )
    response.raise_for_status()
    return response.json()


async def executor_id(client: AsyncClient, auth_headers: Callable[[str], Awaitable[dict[str, str]]]) -> int:
    response = await client.get("/admin/users", headers=await auth_headers("admin"))
    response.raise_for_status()
    users = response.json()
    return next(user["id"] for user in users if "executor" in user["roles"])
