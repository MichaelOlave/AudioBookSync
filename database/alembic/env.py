"""Alembic migration environment with async support."""

from logging.config import fileConfig
from pathlib import Path

import sqlalchemy as sa
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Import models for autogenerate to discover them
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.core.config import Config
from src.database.models.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata

# Other values from config can be acquired:
# my_important_option = config.get_main_option("my_important_option")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Useful for generating SQL scripts without a live database connection.
    """
    # Use async URL for offline mode
    url = Config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: sa.engine.Connection) -> None:
    """Helper to run migrations with a connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async support.

    In this scenario we create an async Engine and associate a connection
    with the context.
    """
    # Use asyncpg driver for async migrations
    url = Config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = url

    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        echo=False,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
