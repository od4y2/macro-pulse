"""Tests for S08 time-series transformations."""

from __future__ import annotations

from datetime import date

import pytest

from macropulse.metrics.transforms import (
    FORMULAS,
    DerivedPoint,
    SeriesPoint,
    annualized_pct_series,
    mom,
    pct_change_series,
    percent_change,
    pp_change_series,
    rolling_mean,
    weighted_coverage,
    yoy,
)


def pts(spec: dict[str, float | None], missing="not_available") -> list[SeriesPoint]:
    """Monthly points from {"YYYY-MM": value} (None -> explicit missing)."""
    out = []
    for key, v in spec.items():
        y, m = key.split("-")
        out.append(
            SeriesPoint(
                period=date(int(y), int(m), 1),
                value=v,
                missing_reason=missing if v is None else None,
            )
        )
    return out


def annual(values: dict[int, float | None]) -> list[SeriesPoint]:
    return [
        SeriesPoint(
            period=date(y, 1, 1), value=v,
            missing_reason=None if v is not None else "not_available",
        )
        for y, v in values.items()
    ]


# --- audit-era scalar helpers (baseline) -----------------------------------


def test_percent_change() -> None:
    assert percent_change(110, 100) == pytest.approx(10.0)


def test_percent_change_rejects_zero_base() -> None:
    with pytest.raises(ValueError):
        percent_change(1, 0)


def test_coverage() -> None:
    assert weighted_coverage([0.5, 0.2], [0.5, 0.3, 0.2]) == pytest.approx(0.7)


# --- YoY --------------------------------------------------------------------


def test_yoy_annual_series():
    series = annual({2022: 100.0, 2023: 110.0, 2024: 121.0})
    out = yoy(series)
    values = {o.period.year: o for o in out}
    assert values[2022].value is None  # no history yet
    assert values[2022].missing_reason == "insufficient_history"
    assert values[2023].value == pytest.approx(10.0)
    assert values[2024].value == pytest.approx(10.0)
    assert values[2024].input_periods == (date(2023, 1, 1), date(2024, 1, 1))


def test_yoy_monthly_series():
    series = pts({"2023-01": 100.0, "2024-01": 103.0, "2024-02": 104.0})
    out = yoy(series)
    by_period = {o.period: o for o in out}
    assert by_period[date(2024, 1, 1)].value == pytest.approx(3.0)
    assert by_period[date(2024, 2, 1)].value is None  # 2023-02 absent
    assert by_period[date(2023, 1, 1)].missing_reason == "insufficient_history"


def test_yoy_quarterly_same_quarter_prior_year():
    series = [
        SeriesPoint(date(2023, 4, 1), 100.0, None),
        SeriesPoint(date(2024, 4, 1), 102.0, None),
    ]
    out = yoy(series)
    assert out[1].value == pytest.approx(2.0)


def test_yoy_missing_lag_input_propagates():
    series = pts({"2023-01": 100.0, "2024-01": 103.0})
    out = yoy(series)
    # 2023-01 exists with a value; 2024-01 vs 2023-01 is computable.
    assert out[1].value == pytest.approx(3.0)
    # Now with the base NULL:
    series2 = pts({"2023-01": None, "2024-01": 103.0})
    out2 = yoy(series2)
    assert out2[1].value is None
    assert out2[1].missing_reason == "input_missing"


def test_yoy_current_null_propagates():
    series = pts({"2023-01": 100.0, "2024-01": None})
    out = yoy(series)
    assert out[1].value is None
    assert out[1].missing_reason == "input_missing"


def test_yoy_zero_base_is_missing_not_infinity():
    series = annual({2023: 0.0, 2024: 5.0})
    out = yoy(series)
    assert out[1].value is None
    assert out[1].missing_reason == "zero_base"


def test_yoy_negative_base_is_missing():
    series = annual({2023: -2.0, 2024: 4.0})
    out = yoy(series)
    assert out[1].value is None
    assert out[1].missing_reason == "non_positive_base"


# --- MoM --------------------------------------------------------------------


def test_mom_monthly():
    series = pts({"2024-01": 100.0, "2024-02": 101.0, "2024-03": 101.0})
    out = mom(series)
    assert out[1].value == pytest.approx(1.0)
    assert out[2].value == pytest.approx(0.0)
    assert out[0].missing_reason == "insufficient_history"


def test_mom_on_quarterly_series_has_no_valid_lag():
    # MoM assumes monthly data: quarterly periods shifted by 1 month do not
    # exist, so every output is insufficient_history - honest, not an error.
    series = [
        SeriesPoint(date(2024, 1, 1), 100.0, None),
        SeriesPoint(date(2024, 4, 1), 103.0, None),
    ]
    out = mom(series)
    assert all(o.value is None for o in out)


# --- percentage-point change -------------------------------------------------


def test_pp_change_rates():
    series = pts({"2024-01": 5.0, "2024-02": 5.4})
    out = pp_change_series(series, 1)
    assert out[1].value == pytest.approx(0.4)


def test_pp_change_works_on_negative_and_zero():
    series = pts({"2024-01": -2.0, "2024-02": 0.0, "2024-03": 3.0})
    out = pp_change_series(series, 1)
    assert out[1].value == pytest.approx(2.0)
    assert out[2].value == pytest.approx(3.0)


def test_pp_change_yoy_lag():
    series = annual({2023: 3.9, 2024: 4.3})
    out = pp_change_series(series, 12)
    assert out[1].value == pytest.approx(0.4)


def test_pp_change_missing_input_propagates():
    series = pts({"2024-01": None, "2024-02": 5.4})
    out = pp_change_series(series, 1)
    assert out[1].value is None
    assert out[1].missing_reason == "input_missing"


# --- annualization ------------------------------------------------------------


def test_annualized_monthly_one_percent():
    series = pts({"2024-01": 100.0, "2024-02": 101.0})
    out = annualized_pct_series(series, 1)
    assert out[1].value == pytest.approx((1.01**12 - 1) * 100.0)


def test_annualized_quarterly_one_percent():
    series = [
        SeriesPoint(date(2024, 1, 1), 100.0, None),
        SeriesPoint(date(2024, 4, 1), 101.0, None),
    ]
    out = annualized_pct_series(series, 3)
    assert out[1].value == pytest.approx((1.01**4 - 1) * 100.0)


def test_annualized_annual_lag_is_identity():
    series = annual({2023: 100.0, 2024: 105.0})
    out = annualized_pct_series(series, 12)
    assert out[1].value == pytest.approx(5.0)


def test_annualized_rejects_non_divisor_lag():
    series = pts({"2024-01": 100.0, "2024-02": 101.0})
    with pytest.raises(ValueError, match="whole compounding"):
        annualized_pct_series(series, 5)


def test_annualized_missing_propagates():
    series = pts({"2024-01": 100.0, "2024-02": None})
    out = annualized_pct_series(series, 1)
    assert out[1].value is None
    assert out[1].missing_reason == "input_missing"


# --- rolling mean -------------------------------------------------------------


def test_rolling_mean_complete_window():
    series = pts({"2024-01": 1.0, "2024-02": 2.0, "2024-03": 6.0})
    out = rolling_mean(series, 3, "monthly")
    by_period = {o.period: o for o in out}
    assert by_period[date(2024, 1, 1)].value is None  # window incomplete
    assert by_period[date(2024, 1, 1)].missing_reason == "incomplete_window"
    assert by_period[date(2024, 2, 1)].value is None
    assert by_period[date(2024, 3, 1)].value == pytest.approx(3.0)
    assert by_period[date(2024, 3, 1)].input_periods == (
        date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1),
    )


def test_rolling_mean_window_with_null_is_incomplete():
    series = pts({"2024-01": 1.0, "2024-02": None, "2024-03": 6.0})
    out = rolling_mean(series, 3, "monthly")
    by_period = {o.period: o for o in out}
    assert by_period[date(2024, 3, 1)].value is None
    assert by_period[date(2024, 3, 1)].missing_reason == "incomplete_window"


def test_rolling_mean_window_spanning_gap_is_incomplete():
    # 2024-02 is absent entirely; the trailing window of 2024-03 spans the
    # gap and is incomplete - the mean is never silently computed over the
    # two remaining points.
    series = pts({"2024-01": 1.0, "2024-03": 6.0})
    out = rolling_mean(series, 3, "monthly")
    by_period = {o.period: o for o in out}
    assert by_period[date(2024, 3, 1)].value is None
    assert by_period[date(2024, 3, 1)].missing_reason == "incomplete_window"


def test_rolling_mean_quarterly_frequency():
    series = [
        SeriesPoint(date(2024, 1, 1), 2.0, None),
        SeriesPoint(date(2024, 4, 1), 4.0, None),
        SeriesPoint(date(2024, 7, 1), 9.0, None),
    ]
    out = rolling_mean(series, 3, "quarterly")
    by_period = {o.period: o for o in out}
    assert by_period[date(2024, 7, 1)].value == pytest.approx(5.0)


def test_rolling_mean_window_one_is_identity():
    series = pts({"2024-01": 7.0})
    out = rolling_mean(series, 1, "monthly")
    assert out[0].value == pytest.approx(7.0)


def test_rolling_mean_rejects_invalid_frequency_and_window():
    series = pts({"2024-01": 1.0})
    with pytest.raises(ValueError, match="frequency"):
        rolling_mean(series, 3, "weekly")
    with pytest.raises(ValueError, match="window"):
        rolling_mean(series, 0, "monthly")


# --- input validation ---------------------------------------------------------


def test_pct_change_rejects_nonpositive_lag():
    with pytest.raises(ValueError, match="lag_months"):
        pct_change_series(pts({"2024-01": 1.0}), 0)


def test_duplicate_periods_rejected():
    series = pts({"2024-01": 1.0}) + pts({"2024-01": 2.0})
    with pytest.raises(ValueError, match="duplicate period"):
        yoy(series)


def test_empty_series_returns_empty():
    assert yoy([]) == []
    assert pp_change_series([], 1) == []
    assert rolling_mean([], 3, "monthly") == []


def test_series_point_requires_reason_for_missing():
    with pytest.raises(ValueError, match="missing_reason"):
        SeriesPoint(date(2024, 1, 1), None, None)


def test_series_point_rejects_value_with_reason():
    with pytest.raises(ValueError, match="both"):
        SeriesPoint(date(2024, 1, 1), 1.0, "stale")


def test_formula_registry_covers_all_transforms():
    # Every transform family has a traceable definition text.
    for name in ("pct_change", "yoy", "mom", "pp_change", "annualized_pct", "rolling_mean"):
        assert name in FORMULAS
        assert len(FORMULAS[name]) > 40


def test_derived_point_is_immutable():
    dp = DerivedPoint(date(2024, 1, 1), 1.0, None, ())
    with pytest.raises(AttributeError):
        dp.value = 2.0  # type: ignore[misc]
