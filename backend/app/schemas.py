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
