"""
Database initialization script.

Creates every table declared in app.database.models via SQLAlchemy's
create_all(), then stamps Alembic at head so the migration history agrees with
what is actually in the database.

Usage (from the backend/ directory):
    python init_db.py

WHY THE STAMP MATTERS
---------------------
create_all() builds *all* tables, including the ones owned by Alembic
revisions (ai_stock_reports, email_preferences, insider_transactions, ...).
Without a stamp, the database looks empty to Alembic, so a subsequent
`alembic upgrade head` replays every revision from base and dies on the first
CREATE TABLE with "relation already exists". Stamping records that head is
already present, making that upgrade a clean no-op.

Both of these therefore work on a fresh database:
    alembic upgrade head                 # migrations only
    python init_db.py && alembic upgrade head

`alembic upgrade head` on its own is the preferred path, and the one the
deploy pipeline uses (see Dockerfile.migrate). Prefer it in any environment
that matters: it applies the exact DDL the revisions describe, whereas
create_all() reflects models.py and can differ in small ways (server-side
column defaults, for instance, which models.py expresses as Python-side
defaults). This script is for quick local/dev setup.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.database.connection import engine, Base
from app.database import models  # noqa: F401  (registers every table on Base)

BACKEND_ROOT = Path(__file__).resolve().parent


def _alembic_config() -> Config:
    """Alembic config with absolute paths, so this works from any cwd."""
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    # No sqlalchemy.url here on purpose: alembic/env.py sets it from
    # app.config.settings.DATABASE_URL, the same source `engine` above uses.
    return cfg


def init_database():
    """Create all database tables, then stamp Alembic at head."""
    print("Initializing database...")

    # Drop all tables (WARNING: Only use in development!)
    # Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    print("Tables created:")
    for table_name in sorted(Base.metadata.tables):
        print(f"   - {table_name}")

    print("\nStamping Alembic at head...")
    command.stamp(_alembic_config(), "head")

    print("\nDatabase initialized successfully.")
    print("`alembic upgrade head` is now a no-op against this database.")


if __name__ == "__main__":
    init_database()
