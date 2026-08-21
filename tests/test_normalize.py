"""Tests for the S06 normalization pipeline."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from macropulse.catalog import CATALOG
from macropulse.connectors.base import FetchedPoint, FetchedSeries
from macropulse.pipeline.normalize import (
    NormalizationError,
    infer_frequency,
    normalize_series,
    persist_normalized,
)

RETRIEVAL = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def make_series(
    points,
    system="world_bank",
    series_id="NY.GDP.MKTP.KD.ZG",
    country_iso3="USA",
    evidence_label="real",
):
    return FetchedSeries(
        system=system,
        series_id=series_id,
        country_iso3=country_iso3,
        evidence_label=evidence_label,
        retrieval_time=RETRIEVAL,
        points=tuple(points),
        raw_payload="[]",
    )


def annual_points(values_by_year):
    return [
        FetchedPoint(
            period=date(y, 1, 1),
            value=v,
            missing_reason=None if v is not None else "not_available",
            vintage=RETRIEVAL.date(),
        )
        for y, v in values_by_year.items()
    ]


def catalog_indicator(indicator_id):
    return next(i for i in CATALOG if i.indicator_id == indicator_id)


# --- frequency inference -------------------------------------------------


def test_infer_frequency_annual():
    pts = annual_points({2020: 1.0, 2021: 2.0, 2022: 3.0})
    assert infer_frequency(pts) == "annual"


def test_infer_frequency_quarterly():
    pts = [
        FetchedPoint(date(2024, m, 1), 1.0, None, date(2024, 6, 1))
        for m in (1, 4, 7, 10)
    ]
    assert infer_frequency(pts) == "quarterly"


def test_infer_frequency_monthly():
    pts = [
        FetchedPoint(date(2024, m, 1), 1.0, None, date(2024, 6, 1))
        for m in (1, 2, 3, 4)
    ]
    assert infer_frequency(pts) == "monthly"


def test_infer_frequency_tolerates_one_gap():
    # One missing quarter in an otherwise quarterly series: the MEDIAN gap
    # is still 3, so the series is quarterly. The gap itself is preserved
    # as missingness by the connector, not repaired here.
    pts = [
        FetchedPoint(date(2024, m, 1), 1.0, None, date(2024, 6, 1))
        for m in (1, 4, 10)
    ] + [FetchedPoint(date(2025, 1, 1), 2.0, None, date(2025, 3, 1))]
    assert infer_frequency(pts) == "quarterly"


def test_infer_frequency_rejects_single_point():
    with pytest.raises(NormalizationError, match="fewer than 2 points"):
        infer_frequency(annual_points({2024: 1.0}))


def test_infer_frequency_rejects_inconsistent():
    pts = [
        FetchedPoint(date(2024, 1, 1), 1.0, None, date(2024, 6, 1)),
        FetchedPoint(date(2024, 2, 1), 2.0, None, date(2024, 6, 1)),
        FetchedPoint(date(2024, 8, 1), 3.0, None, date(2024, 6, 1)),
    ]
    with pytest.raises(NormalizationError, match="median gap"):
        infer_frequency(pts)


def test_infer_frequency_rejects_duplicates():
    pts = annual_points({2024: 1.0}) + annual_points({2024: 2.0})
    with pytest.raises(NormalizationError, match="duplicate periods"):
        infer_frequency(pts)


# --- normalize_series -----------------------------------------------------


def test_normalize_happy_path():
    series = make_series(annual_points({2022: 2.1, 2023: 2.4, 2024: 2.9}))
    records = normalize_series(series, "gdp_real_growth")

    assert len(records) == 3
    ind = catalog_indicator("gdp_real_growth")
    for r, expected_value in zip(records, (2.1, 2.4, 2.9)):
        assert r.indicator_id == "gdp_real_growth"
        assert r.country_iso3 == "USA"
        assert r.unit == ind.unit  # canonical unit, unchanged value
        assert r.frequency == "annual"
        assert r.seasonal_adjustment == ind.seasonal_adjustment
        assert r.value == expected_value
        assert r.missing_reason is None
        assert r.evidence_label == "real"
        assert r.quality_grade == "ungraded"
        assert r.vintage == RETRIEVAL.date()  # snapshot semantics
        assert r.release_time == RETRIEVAL.date()  # documented proxy


def test_normalize_passes_missing_through_with_reason():
    series = make_series(
        annual_points({2022: 2.1, 2023: None, 2024: 2.9})
    )
    records = normalize_series(series, "gdp_real_growth")
    assert records[1].value is None
    assert records[1].missing_reason == "not_available"


def test_normalize_missing_without_reason_rejected():
    series = make_series(
        [
            FetchedPoint(date(2022, 1, 1), 1.0, None, date(2026, 8, 19)),
            FetchedPoint(date(2023, 1, 1), None, None, date(2026, 8, 19)),
            FetchedPoint(date(2024, 1, 1), 2.0, None, date(2026, 8, 19)),
        ]
    )
    with pytest.raises(NormalizationError, match="no missing_reason"):
        normalize_series(series, "gdp_real_growth")


def test_normalize_value_with_reason_rejected():
    series = make_series(
        [
            FetchedPoint(date(2022, 1, 1), 1.0, "stale", date(2026, 8, 19)),
            FetchedPoint(date(2023, 1, 1), 2.0, None, date(2026, 8, 19)),
        ]
    )
    with pytest.raises(NormalizationError, match="both a value and a missing_reason"):
        normalize_series(series, "gdp_real_growth")


def test_normalize_rejects_country_outside_panel():
    series = make_series(
        annual_points({2022: 1.0, 2023: 1.1}), country_iso3="FRA"
    )
    with pytest.raises(NormalizationError, match="outside the allowed panel"):
        normalize_series(series, "gdp_real_growth")


def test_normalize_accepts_other_panel_country():
    series = make_series(
        annual_points({2022: 1.0, 2023: 1.1}), country_iso3="ZAF"
    )
    records = normalize_series(series, "gdp_real_growth")
    assert all(r.country_iso3 == "ZAF" for r in records)


def test_normalize_rejects_unknown_indicator():
    series = make_series(annual_points({2022: 1.0, 2023: 1.1}))
    with pytest.raises(NormalizationError, match="not in the catalog"):
        normalize_series(series, "no_such_indicator")


def test_normalize_explicit_seasonal_adjustment_overrides_default():
    ind = catalog_indicator("gdp_real_growth")
    series = make_series(annual_points({2022: 1.0, 2023: 1.1}))
    records = normalize_series(
        series, "gdp_real_growth", seasonal_adjustment="seasonally_adjusted"
    )
    assert records[0].seasonal_adjustment == "seasonally_adjusted"
    assert ind.seasonal_adjustment != "seasonally_adjusted"


def test_normalize_rejects_invalid_seasonal_adjustment():
    series = make_series(annual_points({2022: 1.0, 2023: 1.1}))
    with pytest.raises(NormalizationError, match="invalid seasonal_adjustment"):
        normalize_series(series, "gdp_real_growth", seasonal_adjustment="smoothed")


def test_normalize_explicit_frequency_overrides_inference():
    # Quarterly GDP series normalized as annual would be wrong; an explicit
    # frequency overrides inference but must still be a legal value.
    pts = [
        FetchedPoint(date(2024, m, 1), 1.0, None, date(2024, 6, 1))
        for m in (1, 4, 7, 10)
    ]
    series = make_series(pts, system="fred", series_id="A191RL1Q225SBEA")
    records = normalize_series(series, "gdp_real_growth", frequency="quarterly")
    assert all(r.frequency == "quarterly" for r in records)


def test_normalize_rejects_invalid_frequency():
    series = make_series(annual_points({2022: 1.0, 2023: 1.1}))
    with pytest.raises(NormalizationError, match="invalid frequency"):
        normalize_series(series, "gdp_real_growth", frequency="weekly")


def test_normalize_rejects_invalid_evidence_label():
    series = make_series(
        annual_points({2022: 1.0, 2023: 1.1}), evidence_label="probably"
    )
    with pytest.raises(NormalizationError, match="invalid evidence label"):
        normalize_series(series, "gdp_real_growth")


def test_normalize_fred_point_vintage_preserved():
    # FRED points carry per-point vintages (realtime_start); normalization
    # must NOT flatten them to the retrieval date.
    series = make_series(
        [
            FetchedPoint(date(2023, 1, 1), 5.2, None, date(2023, 4, 2)),
            FetchedPoint(date(2024, 1, 1), 4.8, None, date(2024, 4, 3)),
        ],
        system="fred",
        series_id="UNRATE",
    )
    records = normalize_series(series, "unemployment_rate", frequency="annual")
    assert [r.vintage for r in records] == [date(2023, 4, 2), date(2024, 4, 3)]


def test_normalize_source_fields_recorded():
    series = make_series(
        annual_points({2022: 1.0, 2023: 1.1}),
        system="fred",
        series_id="CPIAUCSL",
    )
    records = normalize_series(series, "cpi_inflation")
    assert records[0].source_system == "fred"
    assert records[0].source_code == "CPIAUCSL"


# --- database integration -------------------------------------------------


@pytest.fixture()
def seeded(session):
    """Seed the minimal FK parents: one country, one indicator, one source."""
    from macropulse.db.models import Country, Indicator, SourceCatalogEntry

    ind = catalog_indicator("gdp_real_growth")
    session.add(
        Country(iso3="USA", name="United States", rationale="test")
    )
    session.add(
        Indicator(
            indicator_id=ind.indicator_id,
            name=ind.name,
            module=ind.module,
            unit=ind.unit,
            frequency=ind.frequency,
            seasonal_adjustment=ind.seasonal_adjustment,
            fallback_status=ind.fallback_status,
            comparability_notes=ind.comparability_notes,
            limitations=ind.limitations,
        )
    )
    session.flush()
    source = SourceCatalogEntry(
        system="world_bank",
        code="NY.GDP.MKTP.KD.ZG",
        role="primary",
        verified="confirmed",
        coverage="test",
        indicator_id=ind.indicator_id,
    )
    session.add(source)
    session.commit()
    return source


def test_persist_normalized_roundtrip(session, seeded):
    from macropulse.db.models import NormalizedObservation

    series = make_series(
        annual_points({2022: 2.1, 2023: None, 2024: 2.9}),
        system="world_bank",
        series_id="NY.GDP.MKTP.KD.ZG",
        country_iso3="USA",
    )
    records = normalize_series(series, "gdp_real_growth")

    rows = persist_normalized(session, records, seeded.id)
    session.commit()

    assert len(rows) == 3
    stored = (
        session.query(NormalizedObservation)
        .filter_by(indicator_id="gdp_real_growth", country_iso3="USA")
        .order_by(NormalizedObservation.period)
        .all()
    )
    assert [r.period for r in stored] == [
        date(2022, 1, 1), date(2023, 1, 1), date(2024, 1, 1)
    ]
    assert float(stored[0].value) == pytest.approx(2.1)
    assert stored[1].value is None
    assert stored[1].missing_reason == "not_available"
    assert stored[0].frequency == "annual"
    assert stored[0].quality_grade == "ungraded"
    assert stored[0].source_id == seeded.id


def test_persist_normalized_rejects_duplicate_identity(session, seeded):
    series = make_series(annual_points({2022: 2.1, 2023: 2.4}))
    records = normalize_series(series, "gdp_real_growth")
    persist_normalized(session, records, seeded.id)
    session.commit()

    # Same (indicator, country, period, vintage, source) identity again.
    with pytest.raises(Exception, match="uq_observation_identity|duplicate key"):
        persist_normalized(session, records, seeded.id)
        session.commit()
    session.rollback()
