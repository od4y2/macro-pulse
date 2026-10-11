"""Time-series transformations (units S08, extending the audit-era starter).

Series-level transforms that turn one normalized series into a derived
one: year-over-year and month-over-month percent change, percentage-point
change, annualized rates, and rolling trends. Full rule documentation:
docs/TransformationRules.md.

Governance rules (non-negotiable):

1. **No imputation.** A transform output is computed ONLY from inputs that
   exist. When an input is absent or NULL the output is missing with an
   explicit reason - values are never interpolated, carried forward, or
   filled.
2. **Closed missing-reason vocabulary** (traceability):
   - ``insufficient_history``  the lag/window input period is absent
   - ``input_missing``         the input period exists but its value is NULL
   - ``zero_base``             percent change against a base of 0
   - ``non_positive_base``     percent change against a negative base
   - ``incomplete_window``     rolling window missing at least one member
3. **Traceable formulas.** Every formula is documented in
   ``FORMULAS`` with its definition text; ``formula_ref`` strings recorded
   in the derived store resolve to these definitions. No magic constants:
   the only numbers are 12 (months per year, definitional), 100 (percent
   scale), and 1 (the base step).
4. **Lineage.** ``DerivedPoint.input_periods`` records exactly which
   source periods produced (or failed to produce) each output.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

# Months per period for each frequency (same definitional steps as S07
# gap enumeration; kept local so the metrics layer has no quality import).
FREQUENCY_STEP_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}

MONTHS_PER_YEAR = 12
PERCENT_SCALE = 100.0


def percent_change(current: float, previous: float) -> float:
    """Scalar percent change (audit-era helper, kept for compatibility)."""
    if previous == 0:
        raise ValueError("previous value must be non-zero")
    return 100.0 * (current / previous - 1.0)


def weighted_coverage(available_weights: list[float], all_weights: list[float]) -> float:
    """Scalar weighted coverage (audit-era helper, kept for compatibility)."""
    total = sum(all_weights)
    if total <= 0:
        raise ValueError("total weight must be positive")
    return sum(available_weights) / total


@dataclass(frozen=True)
class SeriesPoint:
    """One input point: period, value (None = missing), reason if missing."""

    period: date
    value: float | None
    missing_reason: str | None

    def __post_init__(self) -> None:
        if self.value is None and not self.missing_reason:
            raise ValueError(
                f"missing value at {self.period} needs a missing_reason"
            )
        if self.value is not None and self.missing_reason:
            raise ValueError(
                f"point at {self.period} has both a value and a missing_reason"
            )


@dataclass(frozen=True)
class DerivedPoint:
    """One output point with lineage (input periods) and explicit missingness."""

    period: date
    value: float | None
    missing_reason: str | None
    input_periods: tuple[date, ...]


# Formula registry: name -> human-readable definition, recorded verbatim in
# metric_versions.definition when results are persisted.
FORMULAS: dict[str, str] = {
    "pct_change": (
        "Percent change over a lag of L months: 100 * (v_t / v_{t-L} - 1). "
        "Requires a positive non-zero base; missing inputs stay missing."
    ),
    "yoy": (
        "Year-over-year percent change: 100 * (v_t / v_{t-12m} - 1), i.e. "
        "pct_change with L = 12 months. Same period one year earlier."
    ),
    "mom": (
        "Month-over-month percent change: 100 * (v_t / v_{t-1m} - 1), i.e. "
        "pct_change with L = 1 month. Monthly series only."
    ),
    "pp_change": (
        "Percentage-point change over a lag of L months: v_t - v_{t-L}. "
        "For rate-type series where percent-of-percent is meaningless. "
        "Defined for any sign of input."
    ),
    "annualized_pct": (
        "Annualized percent rate from a period-over-period percent change r "
        "(lag L months): (1 + r/100)^(12/L) - 1, expressed in percent. "
        "Requires 12 % L == 0 (whole compounding periods per year)."
    ),
    "rolling_mean": (
        "Trailing arithmetic mean over the last W consecutive periods "
        "(frequency step): sum(v) / W. Every window member must exist with "
        "a non-NULL value; partial windows are missing, never half-computed."
    ),
    "robust_z": (
        "Robust fixed-window standardization (S09): "
        "(v_t - median(window)) / MAD(window) over the trailing N "
        "consecutive periods (frequency step), direction-adjusted so "
        "positive = favorable; window occupancy >= 3 non-missing members. "
        "Zero MAD is missing (zero_scale), never fabricated."
    ),
    "youth_headline_gap": (
        "Youth unemployment minus headline unemployment, in percentage "
        "points (RQ1 divergence measure, S10 labor lens). Positive = youth "
        "fare worse than the headline. Only computed when both inputs "
        "exist; never imputed."
    ),
}


def _shift_months(period: date, months: int) -> date:
    """Shift a period by whole months, clamping the day into the target
    month (periods are month-anchored in practice; this stays safe for any
    day)."""
    total = period.year * MONTHS_PER_YEAR + (period.month - 1) + months
    year, month_index = divmod(total, MONTHS_PER_YEAR)
    month = month_index + 1
    day = min(period.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _validate_points(points: list[SeriesPoint]) -> None:
    seen: set[date] = set()
    for p in points:
        if p.period in seen:
            raise ValueError(f"duplicate period {p.period}")
        seen.add(p.period)


def pct_change_series(
    points: list[SeriesPoint], lag_months: int
) -> list[DerivedPoint]:
    """Percent change of each point vs. the point ``lag_months`` earlier.

    Output period set = input period set (in input order). ``lag_months``
    must be positive. Missing reasons: ``insufficient_history``,
    ``input_missing``, ``zero_base``, ``non_positive_base``.
    """
    if lag_months <= 0:
        raise ValueError("lag_months must be positive")
    _validate_points(points)

    by_period = {p.period: p for p in points}
    out: list[DerivedPoint] = []
    for p in points:
        base_period = _shift_months(p.period, -lag_months)
        base = by_period.get(base_period)
        if base is None:
            out.append(
                DerivedPoint(p.period, None, "insufficient_history", (base_period,))
            )
        elif base.value is None:
            out.append(
                DerivedPoint(p.period, None, "input_missing", (base_period,))
            )
        elif p.value is None:
            out.append(DerivedPoint(p.period, None, "input_missing", (p.period,)))
        elif base.value == 0:
            out.append(DerivedPoint(p.period, None, "zero_base", (base_period,)))
        elif base.value < 0:
            out.append(
                DerivedPoint(p.period, None, "non_positive_base", (base_period,))
            )
        else:
            value = PERCENT_SCALE * (p.value / base.value - 1.0)
            out.append(
                DerivedPoint(p.period, value, None, (base_period, p.period))
            )
    return out


def yoy(points: list[SeriesPoint]) -> list[DerivedPoint]:
    """Year-over-year percent change (lag = 12 months)."""
    return pct_change_series(points, MONTHS_PER_YEAR)


def mom(points: list[SeriesPoint]) -> list[DerivedPoint]:
    """Month-over-month percent change (lag = 1 month; monthly series)."""
    return pct_change_series(points, 1)


def pp_change_series(
    points: list[SeriesPoint], lag_months: int
) -> list[DerivedPoint]:
    """Percentage-point change: v_t - v_{t-L}. Defined for any input sign;
    only absent/NULL inputs can make an output missing."""
    if lag_months <= 0:
        raise ValueError("lag_months must be positive")
    _validate_points(points)

    by_period = {p.period: p for p in points}
    out: list[DerivedPoint] = []
    for p in points:
        base_period = _shift_months(p.period, -lag_months)
        base = by_period.get(base_period)
        if base is None:
            out.append(
                DerivedPoint(p.period, None, "insufficient_history", (base_period,))
            )
        elif base.value is None:
            out.append(
                DerivedPoint(p.period, None, "input_missing", (base_period,))
            )
        elif p.value is None:
            out.append(DerivedPoint(p.period, None, "input_missing", (p.period,)))
        else:
            out.append(
                DerivedPoint(p.period, p.value - base.value, None, (base_period, p.period))
            )
    return out


def annualized_pct_series(
    points: list[SeriesPoint], lag_months: int
) -> list[DerivedPoint]:
    """Annualized percent rate: compounds the period-over-period percent
    change over a year. Requires ``MONTHS_PER_YEAR % lag_months == 0`` (an
    integer number of compounding periods per year).

    Composed from ``pct_change_series``; missing inputs propagate with the
    same reasons, plus this transform's own history requirement (both the
    current and the lag input must exist).
    """
    if lag_months <= 0:
        raise ValueError("lag_months must be positive")
    if MONTHS_PER_YEAR % lag_months != 0:
        raise ValueError(
            f"lag_months must divide {MONTHS_PER_YEAR} (whole compounding "
            f"periods per year); got {lag_months}"
        )
    steps_per_year = MONTHS_PER_YEAR // lag_months

    # Period-over-period percent changes; each is one compounding step.
    steps = pct_change_series(points, lag_months)
    out: list[DerivedPoint] = []
    for step in steps:
        if step.value is None:
            out.append(
                DerivedPoint(
                    step.period, None, step.missing_reason, step.input_periods
                )
            )
        else:
            growth = 1.0 + step.value / PERCENT_SCALE
            annual = (growth**steps_per_year - 1.0) * PERCENT_SCALE
            out.append(
                DerivedPoint(step.period, annual, None, step.input_periods)
            )
    return out


def rolling_mean(
    points: list[SeriesPoint], window: int, frequency: str
) -> list[DerivedPoint]:
    """Trailing arithmetic mean over the last ``window`` CONSECUTIVE periods
    (consecutive by the frequency step - a window that spans a gap is
    incomplete, not silently widened).

    Output period set = input period set; every period whose trailing
    window is complete and fully non-NULL gets a value.
    """
    if frequency not in FREQUENCY_STEP_MONTHS:
        raise ValueError(
            f"frequency must be one of {sorted(FREQUENCY_STEP_MONTHS)}"
        )
    if window < 1:
        raise ValueError("window must be >= 1")
    _validate_points(points)

    step = FREQUENCY_STEP_MONTHS[frequency]
    by_period = {p.period: p for p in points}
    out: list[DerivedPoint] = []
    for p in points:
        members = [
            _shift_months(p.period, -step * k)
            for k in range(window - 1, -1, -1)  # chronological order
        ]
        member_points = [by_period.get(m) for m in members]
        if any(m is None for m in member_points):
            out.append(
                DerivedPoint(p.period, None, "incomplete_window", tuple(members))
            )
            continue
        values = [m.value for m in member_points]  # type: ignore[union-attr]
        if any(v is None for v in values):
            out.append(
                DerivedPoint(p.period, None, "incomplete_window", tuple(members))
            )
            continue
        mean = sum(values) / window  # type: ignore[arg-type]
        out.append(DerivedPoint(p.period, mean, None, tuple(members)))
    return out


__all__ = [
    "FORMULAS",
    "FREQUENCY_STEP_MONTHS",
    "DerivedPoint",
    "SeriesPoint",
    "annualized_pct_series",
    "mom",
    "pct_change_series",
    "percent_change",
    "pp_change_series",
    "rolling_mean",
    "weighted_coverage",
    "yoy",
]
