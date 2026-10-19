"""Database engine and session management (unit S03).

The connection string comes from the ``DATABASE_URL`` environment variable
(local default: the docker-compose PostgreSQL instance). Cloud deployments
(e.g., Vercel with managed Postgres) supply their own URL with pooled
connection parameters; nothing here may assume local-only semantics.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://macropulse:macropulse@localhost:5432/macropulse"
)


def database_url() -> str:
    return os.environ.get("NEON_DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(url: str | None = None) -> Engine:
    """Create an engine; pooling is left to defaults so managed providers
    can inject their own pooler via the URL parameters."""
    return create_engine(url or database_url(), future=True)


def make_session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
