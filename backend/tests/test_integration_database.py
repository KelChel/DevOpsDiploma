import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from conftest import BACKEND_DIR, REPO_ROOT
from app.db import AsyncSessionLocal


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrations_are_applied_to_head() -> None:
    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(REPO_ROOT / "database" / "migrations"))
    script = ScriptDirectory.from_config(alembic_config)

    async with AsyncSessionLocal() as session:
        current_revision = await session.scalar(text("SELECT version_num FROM alembic_version"))

    assert current_revision == script.get_current_head()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_seed_dictionaries_and_users_exist() -> None:
    async with AsyncSessionLocal() as session:
        roles_count = await session.scalar(text("SELECT count(*) FROM roles"))
        users_count = await session.scalar(text("SELECT count(*) FROM users"))
        categories_count = await session.scalar(text("SELECT count(*) FROM ticket_categories WHERE is_active IS TRUE"))
        statuses_count = await session.scalar(text("SELECT count(*) FROM ticket_statuses"))

    assert roles_count >= 4
    assert users_count >= 4
    assert categories_count >= 4
    assert statuses_count == 5
