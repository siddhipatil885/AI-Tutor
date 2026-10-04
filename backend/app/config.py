from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./relearn.db"
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: str | None = None
    neon_auth_issuer: str = ""
    neon_auth_jwks_url: str = ""
    neon_auth_audience: str = "authenticated"
    neon_auth_teacher_emails: str = ""
    neon_auth_admin_emails: str = ""
    model_config = SettingsConfigDict(env_file=(".env", ".env.local", "../.env.local"), extra="ignore")

    @property
    def frontend_origin_list(self) -> list[str]:
        value = self.frontend_origins or self.frontend_origin
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
