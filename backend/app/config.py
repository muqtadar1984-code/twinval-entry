from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(default="postgresql+psycopg2://twinval:twinval@localhost:5432/twinval_portal")

    jwt_secret: str = Field(default="dev-secret-change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_minutes: int = Field(default=30)
    refresh_token_ttl_days: int = Field(default=14)

    initial_admin_email: str = Field(default="admin@twinval.com")
    initial_admin_password: str = Field(default="change-me-on-first-login")
    initial_admin_name: str = Field(default="TwinVal Admin")

    cors_origins: str = Field(default="http://localhost:5173")

    s3_endpoint_url: str = Field(default="")
    s3_bucket: str = Field(default="")
    s3_access_key_id: str = Field(default="")
    s3_secret_access_key: str = Field(default="")
    s3_region: str = Field(default="auto")
    s3_public_base_url: str = Field(default="")

    genesis_seed: str = Field(default="TWINVAL_GENESIS_IIUM_PILOT")

    login_rate_limit: str = Field(default="10/15minutes")

    max_photo_bytes: int = Field(default=5 * 1024 * 1024)
    allowed_photo_mime_types: str = Field(default="image/jpeg,image/png,image/webp,image/heic")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_photo_mime_types_list(self) -> List[str]:
        return [m.strip() for m in self.allowed_photo_mime_types.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
