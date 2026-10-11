"""Alembic environment: runs migrations against the app's database."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.schema import CreateSchema
from sqlmodel import SQLModel

from src.backend.app.core.config import settings
from src.backend.app.core.db import db_connect_args
from src.backend.app.core.model_registry import load_models

# * Import every models.py so its tables register on SQLModel.metadata;
# * autogenerate only sees tables that are imported before it runs.
load_models()

# * This is the Alembic Config object, which provides
# * access to the values within the .ini file in use.
config = context.config

# * Interpret the config file for Python logging.
# * This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# * Escape "%" so configparser interpolation does not choke on URL-encoded passwords.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# * Add your model's MetaData object here
# * for 'autogenerate' support
# * from myapp import mymodel
# * target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# * Other values from the config, defined by the needs of env.py,
# * can be acquired:
# * my_important_option = config.get_main_option("my_important_option")
# * ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure the context with a live connection and run migrations.

    Creates ``POSTGRES_SCHEMA`` first if it is missing: the connection's
    ``search_path`` points at it, and PostgreSQL refuses to create tables when
    no schema on the path exists.

    Args:
        connection (Connection): Synchronous connection to migrate through.
    """
    if settings.POSTGRES_SCHEMA:
        connection.execute(CreateSchema(settings.POSTGRES_SCHEMA, if_not_exists=True))
        connection.commit()

    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations on one of its connections.

    The connection uses the same ``search_path`` as the app, so tables and the
    ``alembic_version`` table land in ``POSTGRES_SCHEMA``.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=db_connect_args(settings.POSTGRES_SCHEMA),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
