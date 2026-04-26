from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

from conftest import create_ticket


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_protected_endpoint_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_employee_cannot_assign_ticket(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)

    response = await client.patch(
        f"/tickets/{ticket['id']}/assign",
        headers=await auth_headers("employee"),
        json={"assignee_id": 2},
    )

    assert response.status_code == 403


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_direct_status_assignment_is_rejected(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)

    response = await client.patch(
        f"/tickets/{ticket['id']}/status",
        headers=await auth_headers("employee"),
        json={"status_code": "assigned"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Use ticket assignment endpoint"


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_unassigned_executor_cannot_read_someone_elses_ticket(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
    default_category_id: int,
) -> None:
    ticket = await create_ticket(client, auth_headers, default_category_id)

    response = await client.get(
        f"/tickets/{ticket['id']}",
        headers=await auth_headers("executor"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Ticket is not available"


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_manager_role_cannot_use_ticket_list(
    client: AsyncClient,
    auth_headers: Callable[[str], Awaitable[dict[str, str]]],
) -> None:
    response = await client.get("/tickets", headers=await auth_headers("manager"))

    assert response.status_code == 403
