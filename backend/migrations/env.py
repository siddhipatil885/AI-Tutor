"""Alembic environment for Re:Learn application tables only.

Neon Auth owns its own tables and is intentionally not imported or modified.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Model metadata imports initialize the application's session module. During a
# migration the direct URL is authoritative, so give that import a safe value
# without ever allowing the pooled URL to drive Alembic.
if os.getenv("DATABASE_URL_UNPOOLED"):
    os.environ.setdefault("DATABASE_URL", os.environ["DATABASE_URL_UNPOOLED"])

from app.db.session import Base
import app.models  # noqa: F401 - registers SQLAlchemy models with Base metadata.


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def migration_url() -> str:
    url = os.getenv("DATABASE_URL_UNPOOLED")
    if not url:
        raise RuntimeError("DATABASE_URL_UNPOOLED is required for migrations; do not run Alembic through Neon pooling.")
    if not url.startswith("postgresql"):
        raise RuntimeError("Stage 4 migrations require a PostgreSQL direct connection URL.")
    if "-pooler" in url:
        raise RuntimeError("DATABASE_URL_UNPOOLED must be a direct Neon host, not a -pooler host.")
    return url


def run_migrations_offline() -> None:
    context.configure(url=migration_url(), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = migration_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
