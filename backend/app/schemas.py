from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str
    position: str | None = None
    is_active: bool
    roles: list[str]


class RoleRead(BaseModel):
    code: str
    name: str
    description: str


TicketPriority = Literal["low", "normal", "high", "critical"]


class TicketCategoryRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    is_active: bool


class TicketStatusRead(BaseModel):
    id: int
    code: str
    name: str
    sort_order: int


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=4000)
    category_id: int = Field(gt=0)
    priority: TicketPriority = "normal"


class TicketAssignRequest(BaseModel):
    assignee_id: int = Field(gt=0)


class TicketStatusUpdateRequest(BaseModel):
    status_code: str = Field(min_length=1, max_length=32)


class TicketRead(BaseModel):
    id: int
    title: str
    description: str
    priority: TicketPriority
    category_id: int
    category_code: str
    category_name: str
    status_id: int
    status_code: str
    status_name: str
    created_by_id: int
    created_by_name: str
    assignee_id: int | None = None
    assignee_name: str | None = None
    created_at: datetime
    updated_at: datetime
    assigned_at: datetime | None = None
    completed_at: datetime | None = None
    closed_at: datetime | None = None
