from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from conftest import AsyncSessionLocal, create_ticket, executor_id


@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


@pytest.mark.api
@pytest.mark.asyncio
async def test_employee_can_create_ticket(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)

    assert ticket["status_code"] == "created"
    assert ticket["created_by_name"]
    assert ticket["assignee_id"] is None
    assert ticket["sla_due_at"]
    assert ticket["is_overdue"] is False


@pytest.mark.api
@pytest.mark.asyncio
async def test_admin_assigns_executor(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)
    assignee_id = await executor_id(client, auth_headers)

    response = await client.patch(
        f"/tickets/{ticket['id']}/assign",
        headers=await auth_headers("admin"),
        json={"assignee_id": assignee_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assignee_id"] == assignee_id
    assert body["status_code"] == "assigned"


@pytest.mark.api
@pytest.mark.asyncio
async def test_ticket_status_lifecycle(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)
    assignee_id = await executor_id(client, auth_headers)

    await client.patch(
        f"/tickets/{ticket['id']}/assign",
        headers=await auth_headers("admin"),
        json={"assignee_id": assignee_id},
    )

    in_progress = await client.patch(
        f"/tickets/{ticket['id']}/status",
        headers=await auth_headers("executor"),
        json={"status_code": "in_progress"},
    )
    completed = await client.patch(
        f"/tickets/{ticket['id']}/status",
        headers=await auth_headers("executor"),
        json={"status_code": "completed"},
    )
    closed = await client.patch(
        f"/tickets/{ticket['id']}/status",
        headers=await auth_headers("employee"),
        json={"status_code": "closed"},
    )

    assert in_progress.status_code == 200
    assert in_progress.json()["status_code"] == "in_progress"
    assert completed.status_code == 200
    assert completed.json()["status_code"] == "completed"
    assert closed.status_code == 200
    assert closed.json()["status_code"] == "closed"


@pytest.mark.api
@pytest.mark.asyncio
async def test_ticket_comments_history_and_notifications(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)

    comment_response = await client.post(
        f"/tickets/{ticket['id']}/comments",
        headers=await auth_headers("employee"),
        json={"body": "Комментарий для проверки обработки заявки."},
    )
    history_response = await client.get(
        f"/tickets/{ticket['id']}/history",
        headers=await auth_headers("employee"),
    )
    notifications_response = await client.get(
        f"/tickets/{ticket['id']}/notifications",
        headers=await auth_headers("employee"),
    )

    assert comment_response.status_code == 201
    assert comment_response.json()["body"] == "Комментарий для проверки обработки заявки."

    event_types = {item["event_type"] for item in history_response.json()}
    assert {"ticket_created", "comment_added"}.issubset(event_types)

    notification_events = {item["event_type"] for item in notifications_response.json()}
    assert {"ticket_created", "comment_added"}.issubset(notification_events)


@pytest.mark.api
@pytest.mark.asyncio
async def test_invalid_status_transition_is_rejected(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)

    response = await client.patch(
        f"/tickets/{ticket['id']}/status",
        headers=await auth_headers("employee"),
        json={"status_code": "closed"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Status transition is not allowed"


@pytest.mark.api
@pytest.mark.asyncio
async def test_manager_report_includes_sla_overdue_ticket(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE tickets SET sla_due_at = now() - INTERVAL '1 hour' WHERE id = :ticket_id"),
            {"ticket_id": ticket["id"]},
        )
        await session.commit()

    response = await client.get("/reports/summary", headers=await auth_headers("manager"))

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["open_count"] == 1
    assert body["overdue_count"] == 1
    assert body["overdue_tickets"][0]["id"] == ticket["id"]
