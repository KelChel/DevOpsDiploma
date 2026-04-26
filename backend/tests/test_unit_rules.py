import pytest
from fastapi import HTTPException

from app.auth import require_roles
from app.main import ALLOWED_STATUS_TRANSITIONS, _can_read_ticket, _notification_recipients
from app.notifications import MockNotificationProvider, build_notification_provider
from app.schemas import TicketRead, UserRead


def user(user_id: int, roles: list[str]) -> UserRead:
    return UserRead(
        id=user_id,
        username=f"user{user_id}",
        full_name=f"User {user_id}",
        is_active=True,
        roles=roles,
    )


def ticket(created_by_id: int = 1, assignee_id: int | None = 2) -> TicketRead:
    from datetime import UTC, datetime

    return TicketRead(
        id=10,
        title="Test ticket",
        description="Test ticket description",
        priority="normal",
        category_id=1,
        category_code="it",
        category_name="IT",
        status_id=1,
        status_code="assigned",
        status_name="Assigned",
        created_by_id=created_by_id,
        created_by_name="Requester",
        assignee_id=assignee_id,
        assignee_name="Executor" if assignee_id else None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_status_transitions_match_lifecycle() -> None:
    assert ALLOWED_STATUS_TRANSITIONS == {
        "created": {"assigned"},
        "assigned": {"in_progress"},
        "in_progress": {"completed"},
        "completed": {"closed"},
        "closed": set(),
    }


@pytest.mark.asyncio
async def test_require_roles_allows_matching_role() -> None:
    dependency = require_roles("admin")
    current_user = user(1, ["employee", "admin"])

    assert await dependency(current_user=current_user) == current_user


@pytest.mark.asyncio
async def test_require_roles_rejects_non_matching_role() -> None:
    dependency = require_roles("admin")

    with pytest.raises(HTTPException) as exc:
        await dependency(current_user=user(1, ["employee"]))

    assert exc.value.status_code == 403


def test_ticket_read_access_rules() -> None:
    current_ticket = ticket(created_by_id=1, assignee_id=2)

    assert _can_read_ticket(user(1, ["employee"]), current_ticket) is True
    assert _can_read_ticket(user(2, ["executor"]), current_ticket) is True
    assert _can_read_ticket(user(3, ["admin"]), current_ticket) is True
    assert _can_read_ticket(user(4, ["executor"]), current_ticket) is False


def test_notification_recipients_exclude_actor() -> None:
    current_ticket = ticket(created_by_id=1, assignee_id=2)

    assert _notification_recipients(current_ticket, "ticket_assigned", actor_id=3) == [2]
    assert _notification_recipients(current_ticket, "status_changed", actor_id=2) == [1]
    assert _notification_recipients(current_ticket, "comment_added", actor_id=1) == [2]


@pytest.mark.asyncio
async def test_mock_notification_provider_returns_sent_result() -> None:
    provider = MockNotificationProvider()

    result = await provider.send(event_type="ticket_created", ticket_id=1, recipient_user_id=2)

    assert result.status == "sent"
    assert result.sent_at is not None
    assert result.error_message is None


@pytest.mark.asyncio
async def test_unconfigured_max_provider_fails_without_secret_leak() -> None:
    provider = build_notification_provider("max", max_api_base_url="", max_bot_token="secret-token")

    result = await provider.send(event_type="ticket_created", ticket_id=1, recipient_user_id=2)

    assert result.status == "failed"
    assert result.error_message == "MAX provider is not configured"
    assert "secret-token" not in result.error_message
