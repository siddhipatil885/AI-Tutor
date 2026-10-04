from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./relearn.db"
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]
    neon_auth_issuer: str = ""
    neon_auth_jwks_url: str = ""
    neon_auth_audience: str = "authenticated"
    neon_auth_teacher_emails: str = ""
    neon_auth_admin_emails: str = ""
    model_config = SettingsConfigDict(env_file=(".env", ".env.local", "../.env.local"), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
