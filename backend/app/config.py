from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="devops-ticket-system", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    backend_cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="BACKEND_CORS_ORIGINS",
    )
    database_url: str = Field(
        default="postgresql+asyncpg://ticket_system:change_me_for_local_only@postgres:5432/ticket_system",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="replace_with_local_development_secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
