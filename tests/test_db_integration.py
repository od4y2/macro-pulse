"""Integration tests against the live PostgreSQL instance (unit S03).

These run only when the docker-compose database is reachable. They use a
dedicated test database so the dev database is never mutated.
"""

from __future__ import annotations

import datetime as dt
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from macropulse.db.base import database_url
from macropulse.db.models import (
    Base,
    Country,
    Indicator,
    NormalizedObservation,
    SourceCatalogEntry,
)

TEST_DB_URL = os.environ.get(
    "MACROPULSE_TEST_DB_URL",
    database_url().rsplit("/", 1)[0] + "/macropulse_test",
)


def _db_available(url: str) -> bool:
    try:
        engine = create_engine(url.rsplit("/", 1)[0] + "/postgres", future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except (OSError, SQLAlchemyError):
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(TEST_DB_URL), reason="PostgreSQL not reachable"
)


@pytest.fixture()
def session():
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


def _seed_reference_data(s):
    s.add(Country(iso3="USA", name="United States", rationale="benchmark"))
    s.add(
        Indicator(
            indicator_id="unemployment_rate", name="Unemployment rate",
            module="traditional-indicators", unit="percent", frequency="annual",
            seasonal_adjustment="varies", fallback_status="primary-and-fallback",
            comparability_notes="n/a", limitations="n/a",
        )
    )
    s.add(
        SourceCatalogEntry(
            system="world_bank", code="SL.UEM.TOTL.ZS", role="primary",
            verified="confirmed", coverage="all panel", indicator_id="unemployment_rate",
        )
    )
    s.commit()
    return s.query(SourceCatalogEntry).one()


def _observation(source_id: int, **overrides) -> NormalizedObservation:
    base = {
        "indicator_id": "unemployment_rate", "country_iso3": "USA",
        "period": dt.date(2024, 1, 1), "value": 4.1, "unit": "percent",
        "frequency": "annual", "seasonal_adjustment": "varies",
        "source_id": source_id,
        "release_time": dt.datetime(2025, 1, 15, tzinfo=dt.UTC),
        "retrieval_time": dt.datetime(2025, 2, 1, tzinfo=dt.UTC),
        "vintage": dt.date(2025, 2, 1), "evidence_label": "real",
        "quality_grade": "official",
    }
    base.update(overrides)
    return NormalizedObservation(**base)


def test_observation_roundtrip_preserves_provenance(session) -> None:
    source = _seed_reference_data(session)
    session.add(_observation(source.id))
    session.commit()

    row = session.query(NormalizedObservation).one()
    assert float(row.value) == pytest.approx(4.1)
    assert row.evidence_label == "real"
    assert row.quality_grade == "official"
    assert row.release_time == dt.datetime(2025, 1, 15, tzinfo=dt.UTC)
    assert row.vintage == dt.date(2025, 2, 1)


def test_missing_value_without_reason_rejected(session) -> None:
    source = _seed_reference_data(session)
    session.add(_observation(source.id, value=None, missing_reason=None))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_missing_value_with_reason_accepted(session) -> None:
    source = _seed_reference_data(session)
    session.add(_observation(source.id, value=None, missing_reason="not yet released"))
    session.commit()

    row = session.query(NormalizedObservation).one()
    assert row.value is None
    assert row.missing_reason == "not yet released"


def test_invalid_evidence_label_rejected(session) -> None:
    source = _seed_reference_data(session)
    session.add(_observation(source.id, evidence_label="guessed"))
    # PG native enums reject unknown labels at the driver level (DataError)
    with pytest.raises((IntegrityError, DataError)):
        session.commit()
    session.rollback()


def test_duplicate_observation_identity_rejected(session) -> None:
    source = _seed_reference_data(session)
    session.add(_observation(source.id))
    session.commit()
    session.add(_observation(source.id))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
