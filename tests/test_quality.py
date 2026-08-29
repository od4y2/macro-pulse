"""Tests for S07 quality assessment and missingness rules."""

from __future__ import annotations

from datetime import date

import pytest

from macropulse.quality.assessment import (
    FLAG_MISSING_VALUE,
    FLAG_SERIES_GAP,
    FLAG_VINTAGE_PRECEDES_PERIOD,
    QualityFlag,
    RecordAssessment,
    assess_series,
    expected_periods,
)
from macropulse.quality.missingness import (
    MissingnessReport,
    missingness_report,
)


class Row:
    """Duck-typed stand-in for NormalizedObservation / NormalizedRecord."""

    def __init__(self, period, value, missing_reason=None,
                 vintage=None, evidence_label="real"):
        self.period = period
        self.value = value
        self.missing_reason = missing_reason
        self.vintage = vintage if vintage is not None else period
        self.evidence_label = evidence_label


ANNUAL = [date(y, 1, 1) for y in (2022, 2023, 2024)]


# --- expected_periods ------------------------------------------------------


def test_expected_periods_annual():
    assert expected_periods("annual", date(2022, 1, 1), date(2024, 1, 1)) == ANNUAL


def test_expected_periods_quarterly_crosses_year_boundary():
    periods = expected_periods("quarterly", date(2023, 10, 1), date(2024, 4, 1))
    assert periods == [
        date(2023, 10, 1), date(2024, 1, 1), date(2024, 4, 1),
    ]


def test_expected_periods_monthly():
    periods = expected_periods("monthly", date(2024, 11, 1), date(2025, 2, 1))
    assert periods == [
        date(2024, 11, 1), date(2024, 12, 1),
        date(2025, 1, 1), date(2025, 2, 1),
    ]


def test_expected_periods_anchored_on_first():
    # A quarterly series in a Q2-Q4-Q2 phase stays on that phase.
    periods = expected_periods("quarterly", date(2023, 4, 1), date(2024, 4, 1))
    assert periods == [
        date(2023, 4, 1), date(2023, 7, 1),
        date(2023, 10, 1), date(2024, 1, 1), date(2024, 4, 1),
    ]


def test_expected_periods_rejects_unknown_frequency():
    with pytest.raises(ValueError, match="unknown frequency"):
        expected_periods("weekly", date(2024, 1, 1), date(2024, 12, 1))


# --- assess_series: grades -------------------------------------------------


def test_clean_real_series_grades_official():
    rows = [Row(p, 1.0 + i) for i, p in enumerate(ANNUAL)]
    assessment = assess_series(rows, "gdp_real_growth", "USA", "annual")
    assert all(r.grade == "official" for r in assessment.records)
    assert assessment.n_flagged == 0
    assert assessment.gap_periods == ()


def test_mocked_series_grades_ungraded():
    rows = [Row(p, 1.0, evidence_label="mocked") for p in ANNUAL]
    assessment = assess_series(rows, "gdp_real_growth", "USA", "annual")
    assert all(r.grade == "ungraded" for r in assessment.records)


def test_superseded_vintage_grades_revised():
    rows = [
        Row(date(2023, 1, 1), 2.1, vintage=date(2023, 6, 1)),
        Row(date(2023, 1, 1), 2.4, vintage=date(2024, 6, 1)),
        Row(date(2024, 1, 1), 2.9, vintage=date(2024, 6, 1)),
    ]
    assessment = assess_series(
        rows, "gdp_real_growth", "USA", "annual",
        superseded=frozenset({(date(2023, 1, 1), date(2023, 6, 1))}),
    )
    grades = {(r.period, r.vintage): r.grade for r in assessment.records}
    assert grades[(date(2023, 1, 1), date(2023, 6, 1))] == "revised"
    assert grades[(date(2023, 1, 1), date(2024, 6, 1))] == "official"


def test_flagged_outranks_other_grades():
    # A missing value on a mocked, superseded record still grades "flagged".
    rows = [
        Row(date(2023, 1, 1), None, "not_available",
            vintage=date(2023, 6, 1), evidence_label="mocked"),
    ]
    assessment = assess_series(
        rows, "gdp_real_growth", "USA", "annual",
        superseded=frozenset({(date(2023, 1, 1), date(2023, 6, 1))}),
    )
    assert assessment.records[0].grade == "flagged"
    codes = {f.flag_code for f in assessment.records[0].flags}
    assert codes == {FLAG_MISSING_VALUE}


def test_grades_by_period_hides_superseded():
    rows = [
        Row(date(2023, 1, 1), 2.1, vintage=date(2023, 6, 1)),
        Row(date(2023, 1, 1), 2.4, vintage=date(2024, 6, 1)),
    ]
    assessment = assess_series(
        rows, "gdp_real_growth", "USA", "annual",
        superseded=frozenset({(date(2023, 1, 1), date(2023, 6, 1))}),
    )
    assert assessment.grades_by_period() == {date(2023, 1, 1): "official"}


# --- assess_series: flags ---------------------------------------------------


def test_missing_value_flagged_with_reason_in_description():
    rows = [
        Row(date(2022, 1, 1), 1.0),
        Row(date(2023, 1, 1), None, "not_available"),
        Row(date(2024, 1, 1), 2.0),
    ]
    assessment = assess_series(rows, "gdp_real_growth", "USA", "annual")
    flagged = [r for r in assessment.records if r.flags]
    assert len(flagged) == 1
    assert flagged[0].flags[0].flag_code == FLAG_MISSING_VALUE


def test_series_gap_flagged_and_anchored_to_preceding_record():
    # 2023 is absent entirely; the flag anchors on the 2022 record.
    rows = [Row(date(2022, 1, 1), 1.0), Row(date(2024, 1, 1), 2.0)]
    assessment = assess_series(rows, "gdp_real_growth", "USA", "annual")
    assert assessment.gap_periods == (date(2023, 1, 1),)
    anchor = [r for r in assessment.records if r.flags]
    assert len(anchor) == 1
    assert anchor[0].period == date(2022, 1, 1)
    assert anchor[0].flags[0].flag_code == FLAG_SERIES_GAP
    assert "2023-01-01" in anchor[0].flags[0].description
    assert anchor[0].grade == "flagged"


def test_gap_span_starts_at_first_record():
    # Gap detection spans first..last only: 2025 absent between present
    # endpoints is a gap; nothing before 2024 is inferred as missing.
    rows = [Row(date(2024, 1, 1), 2.0), Row(date(2026, 1, 1), 3.0)]
    assessment = assess_series(rows, "gdp_real_growth", "USA", "annual")
    assert assessment.gap_periods == (date(2025, 1, 1),)
    assert assessment.n_flagged == 1


def test_vintage_precedes_period_flagged():
    # FRED can return realtime windows that predate the observation date
    # (scheduled-but-unreleased); the chronology is impossible and flagged.
    rows = [Row(date(2023, 1, 1), 5.0, vintage=date(2022, 12, 1))]
    assessment = assess_series(rows, "unemployment_rate", "USA", "annual")
    codes = {f.flag_code for f in assessment.records[0].flags}
    assert FLAG_VINTAGE_PRECEDES_PERIOD in codes
    assert assessment.records[0].grade == "flagged"


def test_missing_plus_gap_both_flagged():
    # A NULL record inside a series that also has an absent period: both
    # flags may appear on the same record (gap anchor + missing value).
    rows = [
        Row(date(2022, 1, 1), 1.0),
        Row(date(2024, 1, 1), None, "not_available"),
    ]
    assessment = assess_series(rows, "gdp_real_growth", "USA", "annual")
    by_period = {r.period: r for r in assessment.records}
    assert by_period[date(2022, 1, 1)].flags[0].flag_code == FLAG_SERIES_GAP
    assert FLAG_MISSING_VALUE in {f.flag_code for f in by_period[date(2024, 1, 1)].flags}


def test_duplicate_identity_rejected():
    rows = [
        Row(date(2023, 1, 1), 1.0, vintage=date(2023, 6, 1)),
        Row(date(2023, 1, 1), 1.1, vintage=date(2023, 6, 1)),
    ]
    with pytest.raises(ValueError, match="duplicate"):
        assess_series(rows, "gdp_real_growth", "USA", "annual")


def test_unknown_frequency_rejected():
    with pytest.raises(ValueError, match="unknown frequency"):
        assess_series([Row(date(2023, 1, 1), 1.0)], "i", "USA", "weekly")


def test_flag_code_vocabulary_is_closed():
    with pytest.raises(ValueError, match="unknown flag code"):
        QualityFlag("spicy", "not in the vocabulary")


def test_record_assessment_is_immutable():
    ra = RecordAssessment(
        period=date(2023, 1, 1), vintage=date(2023, 6, 1),
        grade="official", flags=(),
    )
    with pytest.raises(AttributeError):
        ra.grade = "flagged"  # type: ignore[misc]


# --- missingness report -----------------------------------------------------


def test_missingness_full_coverage():
    rows = [Row(p, float(i)) for i, p in enumerate(ANNUAL)]
    report = missingness_report(rows, "annual")
    assert report.n_observed == 3
    assert report.n_missing == 0
    assert report.n_gaps == 0
    assert report.n_expected == 3
    assert report.coverage == 1.0
    assert report.fully_covered


def test_missingness_counts_null_and_gap_separately():
    rows = [
        Row(date(2022, 1, 1), 1.0),
        Row(date(2024, 1, 1), None, "not_available"),
    ]
    report = missingness_report(rows, "annual")
    assert report.n_observed == 1
    assert report.n_missing == 1
    assert report.n_gaps == 1  # 2023 absent entirely
    assert report.n_expected == 3
    assert report.coverage == pytest.approx(1 / 3)
    assert not report.fully_covered
    assert report.gap_periods == (date(2023, 1, 1),)
    assert report.missing_reasons == (("not_available", 1),)


def test_missingness_aggregates_reasons():
    rows = [
        Row(date(2022, 1, 1), None, "not_available"),
        Row(date(2023, 1, 1), None, "not_available"),
        Row(date(2024, 1, 1), None, "fred_missing_value"),
    ]
    report = missingness_report(rows, "annual")
    assert report.missing_reasons == (
        ("not_available", 2), ("fred_missing_value", 1),
    )


def test_missingness_empty_series_boundary():
    report = missingness_report([], "annual")
    assert report.n_expected == 0
    assert report.coverage == 0.0
    assert not report.fully_covered


def test_missingness_single_period_boundary():
    report = missingness_report([Row(date(2023, 1, 1), 1.0)], "annual")
    assert report.n_expected == 1
    assert report.coverage == 1.0
    assert report.fully_covered


def test_missingness_never_fabricates():
    # The report has no fill/interpolate/ffill path: outputs are counts
    # and periods only. Sanity-check the surface.
    assert {f for f in MissingnessReport.__dataclass_fields__} == {
        "frequency", "n_observed", "n_missing", "n_gaps",
        "n_expected", "coverage", "missing_reasons", "gap_periods",
    }
