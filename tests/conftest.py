"""Shared pytest fixtures: a dedicated test database on the local Postgres."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from macropulse.db.base import database_url
from macropulse.db.models import Base

TEST_DB_URL = os.environ.get(
    "MACROPULSE_TEST_DB_URL",
    database_url().rsplit("/", 1)[0] + "/macropulse_test",
)


def db_available() -> bool:
    try:
        engine = create_engine(TEST_DB_URL.rsplit("/", 1)[0] + "/postgres", future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except (OSError, SQLAlchemyError):
        return False


@pytest.fixture()
def session():
    """A session bound to a freshly recreated macropulse_test database.

    Skips the test when PostgreSQL is unreachable so unit tests stay
    runnable without Docker.
    """
    if not db_available():
        pytest.skip("PostgreSQL not reachable")

    admin = create_engine(TEST_DB_URL.rsplit("/", 1)[0] + "/postgres", future=True)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("DROP DATABASE IF EXISTS macropulse_test"))
        conn.execute(text("CREATE DATABASE macropulse_test"))
    admin.dispose()

    engine = create_engine(TEST_DB_URL, future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()
