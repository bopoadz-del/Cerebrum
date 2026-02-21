"""
Alembic Migration Environment

Configures the migration environment for database schema management.
"""
import os
import sys
from logging.config import fileConfig

# Add the parent directory to Python path so 'app' can be imported
# This is needed when running in Docker at /app
sys.path.insert(0, '/app')

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy import engine_from_config
from alembic import context

from app.core.config import settings
from app.db.base_class import Base

# this is the Alembic Config object
config = context.config

# Force Alembic to use DATABASE_URL (Render) so migrations and app hit the same DB
import os
_db_url = os.getenv("DATABASE_URL")
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)  # Force Alembic target DB
# Force Alembic to use DATABASE_URL


# Force Alembic to run against the same DB as the application (Render uses DATABASE_URL)
import os
_db_url = os.getenv("DATABASE_URL")
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)


# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
# Import all models here so they are registered with Base.metadata
from app.models.user import User  # noqa
from app.models.audit import AuditLog  # noqa

target_metadata = Base.metadata

# Get database URL from settings
def get_url():
    # Use the async driver URL so Alembic can run via asyncpg in production
    return settings.async_database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations with a session-scoped advisory lock."""
    lock_id = int(os.getenv('MIGRATION_LOCK_ID', '987654321'))
    try:
        # Hold the lock for the lifetime of this Alembic connection (prevents race on multi-instance deploy)
        \1
          # ALEMBIC_DEBUG_DB_IDENTITY
          try:
              db = connection.execute(text("select current_database()")).scalar()
              usr = connection.execute(text("select current_user")).scalar()
              ip  = connection.execute(text("select inet_server_addr()")).scalar()
              sp  = connection.execute(text("show search_path")).scalar()
              n_public = connection.execute(text("""
                  select count(*) from information_schema.tables
                  where table_schema='public' and table_type='BASE TABLE'
              """)).scalar()
              print(f"[ALEMBIC_DEBUG] db={db} user={usr} server={ip} search_path={sp} public_tables_before={n_public}")
          except Exception as e:
              print(f"[ALEMBIC_DEBUG] failed to read identity: {e}")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()
    finally:
        try:
            connection.execute(text('SELECT pg_advisory_unlock(:id)'), {'id': lock_id})
        except Exception:
            pass

def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a SYNC engine (psycopg2)."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = os.getenv("DATABASE_URL") or get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
