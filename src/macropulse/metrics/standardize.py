"""Robust fixed-window standardization and coverage (unit S09).

Turns one country's series into signed, direction-adjusted scores
comparable across countries, plus panel-level coverage aggregation.
Full rule documentation: docs/StandardizationRules.md.

Governance rules:

1. **Robust statistics.** Center = window median, scale = window MAD
   (median absolute deviation). Outliers influence a median/MAD scale
   far less than a mean/std scale, so one extreme observation (a crisis
   spike, a rebasing jump) cannot dominate the scaling of the whole
   window. No normal-consistency constant is applied: the score is a
   scale-free deviation, and comparability - not normality - is the goal.
2. **Fixed window.** The median/MAD come from the trailing ``window``
   periods ending at each point (consecutive by the frequency step).
   The window SIZE is fixed, so every country's score is scaled by the
   same amount of history and the definition never depends on data that
   arrives later.
3. **Partial occupancy is honest.** Window members absent from the
   series are skipped, but the output records ``window_occupancy`` - how
   many non-missing values actually informed the scale. Fewer than
   ``MIN_WINDOW_OCCUPANCY`` members -> the score is missing with
   ``insufficient_history`` (never a thinner estimate silently).
4. **Zero MAD is undefined, not zero.** If more than half the window is
   the same value there is no dispersion to scale by; the score is
   missing with ``zero_scale`` rather than a fabricated 0 or infinity.
5. **Direction adjustment is presentation, not judgment.** For
   ``lower_is_better`` indicators the score is sign-flipped so positive
   consistently reads as "above the country's own window median"
   (deviation) and the ``value`` field reads favorable-positive. Neutral
   indicators pass through unadjusted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median

from macropulse.catalog import DIRECTIONS, FREQUENCIES
from macropulse.metrics.transforms import (
    FREQUENCY_STEP_MONTHS,
    SeriesPoint,
    _shift_months,
)

# Smallest window occupancy where the median is an observed data point
# rather than an interpolation of two (median of 3 = one of the values;
# MAD of 3 likewise). Below this, a "robust" estimate is not meaningful.
MIN_WINDOW_OCCUPANCY = 3


@dataclass(frozen=True)
class StandardizedPoint:
    """One standardized output with lineage and scale diagnostics.

    ``value``     direction-adjusted score (positive = favorable);
                  None with a reason when not computable
    ``deviation`` raw (value - median) / MAD before direction adjustment
    ``window_occupancy``  non-missing members that informed the scale
    """

    period: date
    value: float | None
    missing_reason: str | None
    input_periods: tuple[date, ...]
    deviation: float | None
    window_occupancy: int

    def __post_init__(self) -> None:
        if self.value is None and not self.missing_reason:
            raise ValueError(
                f"missing value at {self.period} needs a missing_reason"
            )
        if self.value is not None and self.missing_reason:
            raise ValueError(
                f"point at {self.period} has both a value and a missing_reason"
            )


def _validate_inputs(points: list[SeriesPoint], window: int, direction: str) -> None:
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    if window < 1:
        raise ValueError("window must be >= 1")
    seen: set[date] = set()
    for p in points:
        if p.period in seen:
            raise ValueError(f"duplicate period {p.period}")
        seen.add(p.period)


def standardize_series(
    points: list[SeriesPoint],
    window: int,
    direction: str,
    frequency: str,
    min_occupancy: int = MIN_WINDOW_OCCUPANCY,
) -> list[StandardizedPoint]:
    """Robust fixed-window standardization of one series.

    Output period set = input period set (input order). Missing reasons:
    ``insufficient_history`` (window occupancy below ``min_occupancy``),
    ``input_missing`` (current value NULL), ``zero_scale`` (MAD == 0).
    """
    if frequency not in FREQUENCIES:
        raise ValueError(f"frequency must be one of {FREQUENCIES}")
    _validate_inputs(points, window, direction)

    step = FREQUENCY_STEP_MONTHS[frequency]
    by_period = {p.period: p for p in points}
    out: list[StandardizedPoint] = []
    for p in points:
        members = [
            _shift_months(p.period, -step * k)
            for k in range(window - 1, -1, -1)  # chronological order
        ]
        present = [by_period[m] for m in members if m in by_period]
        values = [m.value for m in present if m.value is not None]
        occupancy = len(values)

        if p.value is None:
            out.append(
                StandardizedPoint(
                    p.period, None, "input_missing", tuple(members), None, occupancy
                )
            )
        elif occupancy < min_occupancy:
            out.append(
                StandardizedPoint(
                    p.period, None, "insufficient_history", tuple(members), None, occupancy
                )
            )
        else:
            med = median(values)
            mad = median([abs(v - med) for v in values])
            if mad == 0:
                out.append(
                    StandardizedPoint(
                        p.period, None, "zero_scale", tuple(members), None, occupancy
                    )
                )
            else:
                deviation = (p.value - med) / mad
                value = -deviation if direction == "lower_is_better" else deviation
                out.append(
                    StandardizedPoint(
                        p.period, value, None, tuple(members), deviation, occupancy
                    )
                )
    return out


# --- panel coverage ---------------------------------------------------------


@dataclass(frozen=True)
class PanelCoverage:
    """Coverage aggregated over countries (ratio of sums).

    ``coverage = total observed / total expected`` across all countries -
    the share of the panel's expected periods that carry a value. The
    mean-of-per-country-ratios alternative weights small series equally
    with large ones and is deliberately NOT used; per-country detail is
    preserved in ``per_country`` for transparency.
    """

    n_observed: int
    n_expected: int
    coverage: float
    per_country: tuple[tuple[str, float], ...]

    @property
    def fully_covered(self) -> bool:
        return self.n_observed == self.n_expected and self.n_expected > 0


def panel_coverage(reports: dict[str, object]) -> PanelCoverage:
    """Aggregate per-country missingness reports into panel coverage.

    ``reports``: country -> any object with ``n_observed``/``n_expected``
    (a ``MissingnessReport`` from S07 satisfies this).
    """
    n_observed = sum(r.n_observed for r in reports.values())  # type: ignore[attr-defined]
    n_expected = sum(r.n_expected for r in reports.values())  # type: ignore[attr-defined]
    coverage = n_observed / n_expected if n_expected else 0.0
    per_country = tuple(
        (country, r.n_observed / r.n_expected if r.n_expected else 0.0)  # type: ignore[attr-defined]
        for country, r in sorted(reports.items())
    )
    return PanelCoverage(
        n_observed=n_observed,
        n_expected=n_expected,
        coverage=coverage,
        per_country=per_country,
    )


__all__ = [
    "MIN_WINDOW_OCCUPANCY",
    "PanelCoverage",
    "StandardizedPoint",
    "panel_coverage",
    "standardize_series",
]
