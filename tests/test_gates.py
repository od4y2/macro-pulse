"""Tests for S09 publication gates (incl. a DB vertical slice)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from macropulse.connectors.base import FetchedPoint, FetchedSeries
from macropulse.metrics.engine import (
    latest_vintage_records,
    latest_vintage_series,
    observation_id_map,
    persist_derived,
)
from macropulse.metrics.gates import (
    GATE_REASONS,
    GateThresholds,
    evaluate_gate,
)
from macropulse.metrics.standardize import standardize_series
from macropulse.pipeline.normalize import normalize_series, persist_normalized
from macropulse.quality.missingness import missingness_report

RETRIEVAL = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


class LatestRow:
    """Duck-typed latest-vintage record for pure gate tests."""

    def __init__(self, period, evidence_label="real", vintage=None):
        self.period = period
        self.vintage = vintage if vintage is not None else period
        self.evidence_label = evidence_label


def report_for(points_spec: dict[int, float | None], frequency="annual"):
    from macropulse.metrics.transforms import SeriesPoint

    pts = [
        SeriesPoint(
            period=date(y, 1, 1), value=v,
            missing_reason=None if v is not None else "not_available",
        )
        for y, v in points_spec.items()
    ]
    return missingness_report(pts, frequency)


# --- gate semantics (pure) ---------------------------------------------------


def test_clean_series_passes_all_checks():
    report = report_for({2020: 1.0, 2021: 2.0, 2022: 3.0, 2023: 4.0, 2024: 5.0})
    records = [LatestRow(date(y, 1, 1)) for y in range(2020, 2025)]
    result = evaluate_gate("gdp_real_growth/USA", report, records)
    assert result.published
    assert result.reasons == ()
    assert all(c.passed for c in result.checks)


def test_coverage_below_minimum_fails_with_reason():
    # 2 observed of 6 expected periods.
    report = report_for({2020: 1.0, 2025: 2.0})
    records = [LatestRow(date(2020, 1, 1)), LatestRow(date(2025, 1, 1))]
    result = evaluate_gate("gdp_real_growth/USA", report, records)
    assert not result.published
    assert "coverage_below_minimum" in result.reasons
    coverage_check = next(c for c in result.checks if c.name == "coverage")
    assert not coverage_check.passed
    assert "coverage=0.333" in coverage_check.detail


def test_too_few_observations_fails():
    report = report_for({2022: 1.0, 2023: 2.0})
    records = [LatestRow(date(2022, 1, 1)), LatestRow(date(2023, 1, 1))]
    result = evaluate_gate("x/USA", report, records)
    assert "too_few_observations" in result.reasons
    assert not result.published


def test_not_real_evidence_fails():
    report = report_for({2020: 1.0, 2021: 2.0, 2022: 3.0})
    records = [LatestRow(date(2020, 1, 1)), LatestRow(date(2021, 1, 1), evidence_label="mocked")]
    result = evaluate_gate("x/USA", report, records)
    assert "not_real_evidence" in result.reasons
    evidence_check = next(c for c in result.checks if c.name == "evidence")
    assert "1 latest-vintage record(s) not labelled real" in evidence_check.detail


def test_require_real_disabled_allows_mocked():
    report = report_for({2020: 1.0, 2021: 2.0, 2022: 3.0})
    records = [LatestRow(date(2020, 1, 1)), LatestRow(date(2021, 1, 1), "mocked")]
    thresholds = GateThresholds(require_real=False)
    result = evaluate_gate("x/USA", report, records, thresholds)
    assert result.published


def test_impossible_chronology_fails():
    report = report_for({2020: 1.0, 2021: 2.0, 2022: 3.0})
    records = [
        LatestRow(date(2020, 1, 1)),
        # Vintage (release) predates its own observation period.
        LatestRow(date(2021, 1, 1), vintage=date(2020, 6, 1)),
        LatestRow(date(2022, 1, 1)),
    ]
    result = evaluate_gate("x/USA", report, records)
    assert "impossible_chronology" in result.reasons
    assert not result.published


def test_multiple_failures_list_every_reason():
    # Fails coverage AND evidence AND chronology at once - nothing silent.
    report = report_for({2020: None, 2025: 2.0})
    records = [
        LatestRow(date(2020, 1, 1), evidence_label="mocked"),
        LatestRow(date(2025, 1, 1), vintage=date(2024, 1, 1)),
    ]
    result = evaluate_gate("x/USA", report, records)
    assert set(result.reasons) >= {
        "coverage_below_minimum", "not_real_evidence", "impossible_chronology",
    }


def test_reason_vocabulary_is_closed():
    assert set(GATE_REASONS) == {
        "coverage_below_minimum",
        "too_few_observations",
        "not_real_evidence",
        "impossible_chronology",
    }


def test_custom_thresholds():
    report = report_for({2022: 1.0, 2023: 2.0, 2024: 3.0})  # coverage 1.0
    records = [LatestRow(date(y, 1, 1)) for y in (2022, 2023, 2024)]
    strict = GateThresholds(min_coverage=0.99, min_observed=5)
    result = evaluate_gate("x/USA", report, records, strict)
    assert "too_few_observations" in result.reasons
    assert "coverage_below_minimum" not in result.reasons


def test_gate_result_is_frozen():
    report = report_for({2022: 1.0})
    result = evaluate_gate("x/USA", report, [LatestRow(date(2022, 1, 1))])
    with pytest.raises(AttributeError):
        result.published = True  # type: ignore[misc]


# --- DB vertical slice: store -> load -> gate -> standardize -> persist --------


def store_points(session, seeded, points, evidence_label="real"):
    series = FetchedSeries(
        system="world_bank",
        series_id="NY.GDP.MKTP.KD.ZG",
        country_iso3="USA",
        evidence_label=evidence_label,
        retrieval_time=RETRIEVAL,
        points=tuple(points),
        raw_payload="[]",
    )
    records = normalize_series(series, "gdp_real_growth", frequency="annual")
    return persist_normalized(session, records, seeded.id)


GOOD_POINTS = tuple(
    FetchedPoint(date(y, 1, 1), float(v), None, RETRIEVAL.date())
    for y, v in zip(range(2018, 2025), (1, 2, 3, 4, 5, 6, 7))
)


def test_full_slice_passing_series(session, seeded):
    store_points(session, seeded, GOOD_POINTS)

    records = latest_vintage_records(session, "gdp_real_growth", "USA")
    points = latest_vintage_series(session, "gdp_real_growth", "USA")
    report = missingness_report(points, "annual")

    result = evaluate_gate("gdp_real_growth/USA", report, records)
    assert result.published

    standardized = standardize_series(
        points, 5, "higher_is_better", "annual"
    )
    id_map = observation_id_map(session, "gdp_real_growth", "USA")
    written = persist_derived(
        session, "gdp_real_growth.robust_z5", "USA", standardized, "robust_z", id_map
    )
    session.commit()

    # 2018/2019 lack window history; 2020-2024 are written.
    assert [w.period for w in written] == [
        date(y, 1, 1) for y in range(2020, 2025)
    ]
    from macropulse.db.models import DerivedMetric

    rows = session.query(DerivedMetric).order_by(DerivedMetric.period).all()
    # 2024's window [3,4,5,6,7]: median 5, MAD 1 -> deviation +2.
    assert float(rows[-1].value) == pytest.approx(2.0)
    assert rows[-1].metric_key == "gdp_real_growth.robust_z5"
    assert rows[-1].inputs["observation_ids"] == sorted(
        id_map[date(y, 1, 1)] for y in range(2020, 2025)
    )


def test_full_slice_failing_series_writes_nothing(session, seeded):
    # Sparse + non-real: the gate fails and nothing is persisted.
    sparse = tuple(
        FetchedPoint(date(y, 1, 1), float(v), None, RETRIEVAL.date())
        for y, v in ((2018, 1.0), (2024, 7.0))
    )
    store_points(session, seeded, sparse, evidence_label="mocked")

    records = latest_vintage_records(session, "gdp_real_growth", "USA")
    points = latest_vintage_series(session, "gdp_real_growth", "USA")
    report = missingness_report(points, "annual")
    result = evaluate_gate("gdp_real_growth/USA", report, records)

    assert not result.published
    assert "coverage_below_minimum" in result.reasons
    assert "not_real_evidence" in result.reasons

    from macropulse.db.models import DerivedMetric

    assert session.query(DerivedMetric).count() == 0


def test_latest_vintage_records_excludes_superseded(session, seeded):
    # The 2020 period under two vintages: only the newer is in the view.
    points = (
        FetchedPoint(date(2020, 1, 1), 1.0, None, date(2020, 6, 1)),
        FetchedPoint(date(2020, 1, 1), 2.0, None, date(2021, 6, 1)),
        FetchedPoint(date(2021, 1, 1), 3.0, None, date(2021, 6, 1)),
    )
    store_points(session, seeded, points)
    records = latest_vintage_records(session, "gdp_real_growth", "USA")
    assert [(r.period, r.vintage) for r in records] == [
        (date(2020, 1, 1), date(2021, 6, 1)),
        (date(2021, 1, 1), date(2021, 6, 1)),
    ]


def test_latest_vintage_records_empty_for_unknown_series(session, seeded):
    assert latest_vintage_records(session, "gdp_real_growth", "USA") == []
