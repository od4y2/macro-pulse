"""Integration tests against the live PostgreSQL instance (unit S03).

Uses the shared `session` fixture (tests/conftest.py), which skips
automatically when Postgres is unreachable.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy.exc import DataError, IntegrityError

from macropulse.db.models import (
    Country,
    Indicator,
    NormalizedObservation,
    SourceCatalogEntry,
)


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
