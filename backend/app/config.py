from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    database_url: str = "sqlite:///./relearn.db"
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: str | None = None
    neon_auth_issuer: str = ""
    neon_auth_base_url: str = ""
    neon_auth_jwks_url: str = ""
    neon_auth_audience: str = "authenticated"
    neon_auth_teacher_emails: str = ""
    neon_auth_admin_emails: str = ""
    model_config = SettingsConfigDict(env_file=(".env", ".env.local", "../.env.local"), extra="ignore")

    @property
    def frontend_origin_list(self) -> list[str]:
        value = self.frontend_origins or self.frontend_origin
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Use the psycopg v3 driver for standard PostgreSQL/Neon URLs."""
        url = make_url(self.database_url)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
        return url.render_as_string(hide_password=False)

    @property
    def configured_neon_auth_issuer(self) -> str:
        # NEON_AUTH_BASE_URL is the name Neon exposes in some integrations;
        # NEON_AUTH_ISSUER remains the explicit backend setting.
        return self.neon_auth_issuer or self.neon_auth_base_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
