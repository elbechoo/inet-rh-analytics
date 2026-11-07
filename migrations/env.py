"""Alembic environment - wired to the app's env-driven DB config.

Autogenerate compares the live database against the ORM metadata in
models/models.py, so `alembic revision --autogenerate` produces migrations that
match the SQLAlchemy models. Because we import the app's engine/URL, migrations
always run against the same database the app is configured for.
"""
from logging.config import fileConfig

from alembic import context

# Import the app's Base + engine, then the models module so every table is
# registered on Base.metadata for autogenerate.
from config.database import Base, engine, CONNECTION_STRING
import models.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection."""
    context.configure(
        url=CONNECTION_STRING,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the app's configured engine."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
