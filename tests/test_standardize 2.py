"""Tests for S09 robust standardization and panel coverage."""

from __future__ import annotations

from datetime import date

import pytest

from macropulse.metrics.standardize import (
    MIN_WINDOW_OCCUPANCY,
    StandardizedPoint,
    panel_coverage,
    standardize_series,
)
from macropulse.metrics.transforms import SeriesPoint


def annual(values: dict[int, float | None]) -> list[SeriesPoint]:
    return [
        SeriesPoint(
            period=date(y, 1, 1), value=v,
            missing_reason=None if v is not None else "not_available",
        )
        for y, v in values.items()
    ]


def monthly(spec: dict[str, float | None]) -> list[SeriesPoint]:
    out = []
    for key, v in spec.items():
        y, m = key.split("-")
        out.append(
            SeriesPoint(
                period=date(int(y), int(m), 1), value=v,
                missing_reason=None if v is not None else "not_available",
            )
        )
    return out


# --- robust center/scale -----------------------------------------------------


def test_median_center_and_mad_scale():
    # 2024's trailing window is [1, 2, 3, 4, 100]: median 3, MAD 1 (the 100
    # outlier moves the mean to 22 and std to ~43.7 but leaves the robust
    # scale untouched - the deviation stays 97, not ~1.8).
    series = annual({2020: 1.0, 2021: 2.0, 2022: 3.0, 2023: 4.0, 2024: 100.0})
    out = standardize_series(series, 5, "higher_is_better", "annual")
    by_year = {o.period.year: o for o in out}
    assert by_year[2024].deviation == pytest.approx(97.0)
    assert by_year[2024].window_occupancy == 5
    # 2023's window [1, 2, 3, 4]: median 2.5, MAD 1.0 -> deviation 1.5.
    assert by_year[2023].deviation == pytest.approx(1.5)
    # 2021/2020 have fewer than 3 window members.
    assert by_year[2021].missing_reason == "insufficient_history"


def test_direction_lower_is_better_flips_sign():
    series = annual({2020: 5.0, 2021: 6.0, 2022: 7.0, 2023: 8.0, 2024: 9.0})
    out = standardize_series(series, 5, "lower_is_better", "annual")
    by_year = {o.period.year: o for o in out}
    # 2024 is above its own window median: deviation positive, value negative.
    assert by_year[2024].deviation > 0
    assert by_year[2024].value == pytest.approx(-by_year[2024].deviation)


def test_direction_neutral_passes_through():
    series = annual({2020: 5.0, 2021: 6.0, 2022: 7.0, 2023: 8.0, 2024: 9.0})
    out = standardize_series(series, 5, "neutral", "annual")
    by_year = {o.period.year: o for o in out}
    assert by_year[2024].value == pytest.approx(by_year[2024].deviation)


def test_direction_adjusted_value_is_favorable_positive():
    # lower_is_better: a BELOW-median unemployment reading is favorable.
    series = annual({2020: 9.0, 2021: 8.0, 2022: 7.0, 2023: 6.0, 2024: 4.0})
    out = standardize_series(series, 5, "lower_is_better", "annual")
    by_year = {o.period.year: o for o in out}
    assert by_year[2024].deviation < 0
    assert by_year[2024].value > 0


# --- fixed window semantics ---------------------------------------------------


def test_window_is_trailing_and_fixed_size():
    # Each point is scaled by the trailing 3 periods ending at it; the
    # earliest points lack history.
    series = annual({2020: 1.0, 2021: 2.0, 2022: 3.0, 2023: 6.0})
    out = standardize_series(series, 3, "higher_is_better", "annual")
    by_year = {o.period.year: o for o in out}
    assert by_year[2020].value is None
    assert by_year[2020].missing_reason == "insufficient_history"
    assert by_year[2021].value is None  # only 2 window members
    # 2022: window [1,2,3], median 2, MAD 1 -> deviation +1
    assert by_year[2022].deviation == pytest.approx(1.0)
    assert by_year[2022].window_occupancy == 3
    # 2023: window [2,3,6], median 3, MAD 1 -> deviation +3
    assert by_year[2023].deviation == pytest.approx(3.0)


def test_window_skips_absent_members_and_records_occupancy():
    # 2022 missing entirely: the 2024 window is [2022?, 2023, 2024] with
    # occupancy 2 -> below MIN_WINDOW_OCCUPANCY -> missing.
    series = annual({2020: 1.0, 2021: 2.0, 2023: 4.0, 2024: 6.0})
    out = standardize_series(series, 3, "higher_is_better", "annual")
    by_year = {o.period.year: o for o in out}
    assert by_year[2024].value is None
    assert by_year[2024].missing_reason == "insufficient_history"
    assert by_year[2024].window_occupancy == 2


def test_current_value_null_is_input_missing():
    series = annual({2021: 2.0, 2022: 3.0, 2023: 4.0, 2024: None})
    out = standardize_series(series, 3, "higher_is_better", "annual")
    by_year = {o.period.year: o for o in out}
    assert by_year[2024].value is None
    assert by_year[2024].missing_reason == "input_missing"


def test_zero_mad_is_zero_scale_missing():
    # Four of five window members identical: MAD = 0, no dispersion.
    series = annual({2020: 5.0, 2021: 5.0, 2022: 5.0, 2023: 5.0, 2024: 6.0})
    out = standardize_series(series, 5, "higher_is_better", "annual")
    by_year = {o.period.year: o for o in out}
    assert by_year[2024].value is None
    assert by_year[2024].missing_reason == "zero_scale"


def test_monthly_frequency_window_steps():
    series = monthly({"2024-01": 1.0, "2024-02": 2.0, "2024-03": 3.0, "2024-04": 9.0})
    out = standardize_series(series, 3, "higher_is_better", "monthly")
    by_period = {o.period: o for o in out}
    # April's window [Feb, Mar, Apr] = [2, 3, 9]: median 3, MAD 1 -> +6.
    assert by_period[date(2024, 4, 1)].deviation == pytest.approx(6.0)
    # January lacks history.
    assert by_period[date(2024, 1, 1)].missing_reason == "insufficient_history"


def test_input_periods_lineage_chronological():
    series = annual({2021: 1.0, 2022: 2.0, 2023: 3.0})
    out = standardize_series(series, 3, "higher_is_better", "annual")
    assert out[2].input_periods == (
        date(2021, 1, 1), date(2022, 1, 1), date(2023, 1, 1),
    )


# --- validation ---------------------------------------------------------------


def test_invalid_direction_rejected():
    with pytest.raises(ValueError, match="direction"):
        standardize_series(annual({2021: 1.0}), 3, "faster", "annual")


def test_invalid_window_rejected():
    with pytest.raises(ValueError, match="window"):
        standardize_series(annual({2021: 1.0}), 0, "neutral", "annual")


def test_invalid_frequency_rejected():
    with pytest.raises(ValueError, match="frequency"):
        standardize_series(annual({2021: 1.0}), 3, "neutral", "weekly")


def test_duplicate_periods_rejected():
    series = annual({2021: 1.0}) + annual({2021: 2.0})
    with pytest.raises(ValueError, match="duplicate period"):
        standardize_series(series, 3, "neutral", "annual")


def test_empty_series_returns_empty():
    assert standardize_series([], 3, "neutral", "annual") == []


def test_standardized_point_invariants():
    with pytest.raises(ValueError, match="missing_reason"):
        StandardizedPoint(date(2024, 1, 1), None, None, (), None, 0)
    with pytest.raises(ValueError, match="both"):
        StandardizedPoint(date(2024, 1, 1), 1.0, "stale", (), 1.0, 3)


def test_min_occupancy_constant_is_documented_value():
    # 3 = smallest sample where the median is an observed value.
    assert MIN_WINDOW_OCCUPANCY == 3


# --- panel coverage ------------------------------------------------------------


class Report:
    def __init__(self, n_observed, n_expected):
        self.n_observed = n_observed
        self.n_expected = n_expected


def test_panel_coverage_ratio_of_sums():
    reports = {"USA": Report(8, 10), "ZAF": Report(2, 10)}
    pc = panel_coverage(reports)
    assert pc.n_observed == 10
    assert pc.n_expected == 20
    assert pc.coverage == pytest.approx(0.5)
    assert pc.per_country == (("USA", 0.8), ("ZAF", 0.2))


def test_panel_coverage_weights_large_series_correctly():
    # Ratio of sums: a 40-period series missing 10 counts more than a
    # 2-period series missing 1 (mean-of-ratios would weight them equally).
    reports = {"USA": Report(30, 40), "ZAF": Report(1, 2)}
    pc = panel_coverage(reports)
    assert pc.coverage == pytest.approx(31 / 42)
    assert pc.per_country[1] == ("ZAF", 0.5)


def test_panel_coverage_empty():
    pc = panel_coverage({})
    assert pc.n_expected == 0
    assert pc.coverage == 0.0
    assert not pc.fully_covered


def test_panel_coverage_fully_covered():
    pc = panel_coverage({"USA": Report(10, 10)})
    assert pc.fully_covered
    assert pc.coverage == 1.0


def test_panel_coverage_is_frozen():
    pc = panel_coverage({"USA": Report(1, 1)})
    with pytest.raises(AttributeError):
        pc.coverage = 0.0  # type: ignore[misc]
