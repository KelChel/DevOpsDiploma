from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class NotificationResult:
    status: str
    sent_at: datetime | None = None
    error_message: str | None = None


class NotificationProvider(Protocol):
    name: str

    async def send(self, *, event_type: str, ticket_id: int, recipient_user_id: int | None) -> NotificationResult:
        ...


class MockNotificationProvider:
    name = "mock"

    async def send(self, *, event_type: str, ticket_id: int, recipient_user_id: int | None) -> NotificationResult:
        return NotificationResult(status="sent", sent_at=datetime.now(timezone.utc))


class MaxNotificationProvider:
    name = "max"

    def __init__(self, api_base_url: str, bot_token: str) -> None:
        self.api_base_url = api_base_url
        self.bot_token = bot_token

    async def send(self, *, event_type: str, ticket_id: int, recipient_user_id: int | None) -> NotificationResult:
        if not self.api_base_url or not self.bot_token:
            return NotificationResult(status="failed", error_message="MAX provider is not configured")

        return NotificationResult(status="queued")


def build_notification_provider(provider: str, *, max_api_base_url: str, max_bot_token: str) -> NotificationProvider:
    if provider.lower() == "max":
        return MaxNotificationProvider(api_base_url=max_api_base_url, bot_token=max_bot_token)
    return MockNotificationProvider()
