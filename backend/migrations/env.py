"""
Alembic env.py — async migration runner for the ANT backend.

Strategy:
- Import the project's SQLAlchemy DeclarativeBase from `core.database`
  (where the 13 model classes live) so autogenerate sees the real schema.
- Read the effective database URL from the same env vars that
  `core.database` reads, falling back to the default SQLite path.
- Keep the original `Base.metadata.create_all` path as a safety net for
  installs that pre-date this migration tooling.

See: docs/AUDIT_2026-06-05_Project_Audit.md (Fix #23)
"""
import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ─── Path setup ────────────────────────────────────────────────────────
# env.py is at backend/migrations/env.py. Add backend/ to sys.path so we
# can import `core.database` without an editable install.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ─── Alembic Config object ─────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging.
# Pass `disable_existing_loggers=False` explicitly because Python's
# `logging.config.fileConfig` ignores the `disable_existing_loggers`
# setting in the ini file — it only honors the function's kwarg
# (default `True`). Without this, any pre-existing logger (e.g. the
# project's `main` logger, created via `getLogger("main")` at module
# import in core/main.py:79) gets silently disabled on every migration
# run, breaking pytest tests that follow in the same process.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# ─── Import the project's metadata ─────────────────────────────────────
# core.database defines `Base` (DeclarativeBase subclass) plus all 13
# ORM model classes. Importing the module registers every table on
# Base.metadata so autogenerate can diff them against the live DB.
from core.database import Base  # noqa: E402

target_metadata = Base.metadata

# ─── Resolve the database URL ──────────────────────────────────────────
# Read the same env vars `core.database` reads, but do it HERE (not via
# the cached `core.database.DATABASE_URL`) so this script can be pointed
# at a different DB by setting env vars before invoking alembic.
#
# Order of precedence matches `core.database`:
#   1. DATABASE_URL (if it contains a real driver prefix)
#   2. CLOUD_MODE + DATABASE_URL → use it
#   3. FORCE_SQLITE / "sqlite" in DATABASE_URL → DEFAULT_SQLITE_URL
#   4. USE_SQLITE → DEFAULT_SQLITE_URL
#   5. Fallback → DEFAULT_SQLITE_URL
from core import database as _db_mod

def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    use_sqlite = os.getenv("USE_SQLITE", "").lower() == "true"
    force_sqlite = os.getenv("FORCE_SQLITE", "true").lower() == "true"
    cloud_mode = os.getenv("CLOUD_MODE", "false").lower() == "true"

    if cloud_mode and url and "postgresql" in url:
        return url
    if "sqlite" in url.lower():
        return url
    if force_sqlite or use_sqlite or not url:
        return _db_mod.DEFAULT_SQLITE_URL
    return url


# Override the alembic.ini placeholder with the resolved URL. The async
# driver prefix (sqlite+aiosqlite / postgresql+asyncpg) is what alembic
# needs to build the async engine.
config.set_main_option("sqlalchemy.url", _resolve_database_url())

# ─── Offline (no DB connection) ────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Emits SQL to stdout instead of executing against a live DB. Useful
    for review or for producing a script to run elsewhere.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=("sqlite" in url.lower()),
    )

    with context.begin_transaction():
        context.run_migrations()


# ─── Online (real DB connection) ───────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    url = config.get_main_option("sqlalchemy.url") or ""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=("sqlite" in url.lower()),
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run the migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (real connection)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
