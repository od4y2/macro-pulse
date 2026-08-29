"""DB integration tests for the S08 derived-metric engine."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from macropulse.connectors.base import FetchedPoint, FetchedSeries
from macropulse.db.models import DerivedMetric, MetricVersion, NormalizedObservation
from macropulse.metrics.engine import (
    DeriveError,
    latest_vintage_series,
    observation_id_map,
    persist_derived,
)
from macropulse.metrics.transforms import yoy
from macropulse.pipeline.normalize import normalize_series, persist_normalized

RETRIEVAL = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


def make_series(points, system="world_bank", series_id="NY.GDP.MKTP.KD.ZG"):
    return FetchedSeries(
        system=system,
        series_id=series_id,
        country_iso3="USA",
        evidence_label="real",
        retrieval_time=RETRIEVAL,
        points=tuple(points),
        raw_payload="[]",
    )


def store(session, seeded, points):
    series = make_series(points)
    records = normalize_series(series, "gdp_real_growth", frequency="annual")
    return persist_normalized(session, records, seeded.id)


def test_latest_vintage_series_prefers_newest_vintage(session, seeded):
    # Two vintages of 2023-01; the later one wins. 2024 has one vintage.
    points = (
        FetchedPoint(date(2023, 1, 1), 2.1, None, date(2023, 6, 1)),
        FetchedPoint(date(2023, 1, 1), 2.4, None, date(2024, 6, 1)),
        FetchedPoint(date(2024, 1, 1), 2.9, None, date(2024, 6, 1)),
    )
    store(session, seeded, points)

    loaded = latest_vintage_series(session, "gdp_real_growth", "USA")
    assert [(p.period, p.value) for p in loaded] == [
        (date(2023, 1, 1), 2.4),
        (date(2024, 1, 1), 2.9),
    ]


def test_latest_vintage_series_passes_missingness_through(session, seeded):
    points = (
        FetchedPoint(date(2023, 1, 1), None, "not_available", date(2023, 6, 1)),
        FetchedPoint(date(2024, 1, 1), 2.9, None, date(2024, 6, 1)),
    )
    store(session, seeded, points)
    loaded = latest_vintage_series(session, "gdp_real_growth", "USA")
    assert loaded[0].value is None
    assert loaded[0].missing_reason == "not_available"


def test_latest_vintage_series_unknown_series(session, seeded):
    assert latest_vintage_series(session, "gdp_real_growth", "USA") == []


def test_observation_id_map_matches_latest_vintage(session, seeded):
    points = (
        FetchedPoint(date(2023, 1, 1), 2.1, None, date(2023, 6, 1)),
        FetchedPoint(date(2023, 1, 1), 2.4, None, date(2024, 6, 1)),
    )
    store(session, seeded, points)
    id_map = observation_id_map(session, "gdp_real_growth", "USA")
    assert set(id_map) == {date(2023, 1, 1)}
    newer = (
        session.query(NormalizedObservation)
        .filter_by(period=date(2023, 1, 1), vintage=date(2024, 6, 1))
        .one()
    )
    assert id_map[date(2023, 1, 1)] == newer.id


def test_persist_derived_vertical_slice(session, seeded):
    # Full slice: normalized store -> latest vintage -> yoy -> derived rows.
    points = (
        FetchedPoint(date(2022, 1, 1), 100.0, None, date(2022, 6, 1)),
        FetchedPoint(date(2023, 1, 1), 110.0, None, date(2023, 6, 1)),
        FetchedPoint(date(2024, 1, 1), 121.0, None, date(2024, 6, 1)),
    )
    store(session, seeded, points)

    loaded = latest_vintage_series(session, "gdp_real_growth", "USA")
    derived = yoy(loaded)
    id_map = observation_id_map(session, "gdp_real_growth", "USA")

    written = persist_derived(
        session, "gdp_real_growth.yoy", "USA", derived, "yoy", id_map
    )
    session.commit()

    # Missing first point is not written (schema forbids NULL; no fabrication).
    assert [w.period for w in written] == [date(2023, 1, 1), date(2024, 1, 1)]

    rows = session.query(DerivedMetric).order_by(DerivedMetric.period).all()
    assert len(rows) == 2
    assert rows[0].metric_key == "gdp_real_growth.yoy"
    assert rows[0].country_iso3 == "USA"
    assert float(rows[0].value) == pytest.approx(10.0)
    assert float(rows[1].value) == pytest.approx(10.0)
    assert rows[0].formula_ref == "yoy"

    # Lineage: input observation ids of the 2023 value are 2022+2023 rows.
    input_ids = rows[0].inputs["observation_ids"]
    assert input_ids == sorted(
        [id_map[date(2022, 1, 1)], id_map[date(2023, 1, 1)]]
    )

    # Version row carries the registry definition text.
    versions = session.query(MetricVersion).all()
    assert len(versions) == 2
    assert versions[0].version == "v1"
    assert "Year-over-year" in versions[0].definition


def test_persist_derived_skips_missing_outputs(session, seeded):
    # 2023 NULL: its yoy output is missing AND the 2024 output that depends
    # on it is missing too - zero derived rows for a fully broken chain.
    points = (
        FetchedPoint(date(2023, 1, 1), None, "not_available", date(2023, 6, 1)),
        FetchedPoint(date(2024, 1, 1), 2.9, None, date(2024, 6, 1)),
    )
    store(session, seeded, points)
    loaded = latest_vintage_series(session, "gdp_real_growth", "USA")
    derived = yoy(loaded)
    id_map = observation_id_map(session, "gdp_real_growth", "USA")

    written = persist_derived(
        session, "gdp_real_growth.yoy", "USA", derived, "yoy", id_map
    )
    assert written == []
    assert session.query(DerivedMetric).count() == 0


def test_persist_derived_rejects_unknown_formula(session, seeded):
    with pytest.raises(DeriveError, match="unknown formula"):
        persist_derived(
            session, "x", "USA",
            [], "quantum_smooth", {},
        )


def test_persist_derived_duplicate_identity_rejected(session, seeded):
    points = (
        FetchedPoint(date(2022, 1, 1), 100.0, None, date(2022, 6, 1)),
        FetchedPoint(date(2023, 1, 1), 110.0, None, date(2023, 6, 1)),
    )
    store(session, seeded, points)
    loaded = latest_vintage_series(session, "gdp_real_growth", "USA")
    derived = yoy(loaded)
    id_map = observation_id_map(session, "gdp_real_growth", "USA")

    persist_derived(session, "gdp_real_growth.yoy", "USA", derived, "yoy", id_map)
    session.commit()
    with pytest.raises(Exception, match="uq_metric_identity|duplicate key"):
        persist_derived(
            session, "gdp_real_growth.yoy", "USA", derived, "yoy", id_map
        )
        session.commit()
    session.rollback()


def test_persist_derived_idempotent_versions(session, seeded):
    # Same metric identity cannot be re-written, but different periods
    # under the same key each get their own version row.
    points = (
        FetchedPoint(date(2022, 1, 1), 100.0, None, date(2022, 6, 1)),
        FetchedPoint(date(2023, 1, 1), 110.0, None, date(2023, 6, 1)),
        FetchedPoint(date(2024, 1, 1), 121.0, None, date(2024, 6, 1)),
    )
    store(session, seeded, points)
    loaded = latest_vintage_series(session, "gdp_real_growth", "USA")
    derived = yoy(loaded)
    id_map = observation_id_map(session, "gdp_real_growth", "USA")
    persist_derived(session, "gdp_real_growth.yoy", "USA", derived, "yoy", id_map)
    session.commit()
    assert session.query(MetricVersion).count() == 2
    assert session.query(DerivedMetric).count() == 2
