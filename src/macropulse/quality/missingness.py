"""Non-fabricating missing-data rules (unit S07).

A missingness report DESCRIBES what is absent; it never fills, interpolates,
carries forward, or otherwise fabricates values. Every number below is
directly countable from the series:

- ``n_observed``  records with a non-NULL value
- ``n_missing``   records present in the series with NULL value (each
                  carries a ``missing_reason`` - enforced upstream)
- ``n_gaps``      periods the frequency requires that have NO record at all
- ``coverage``    ``n_observed / n_expected`` where ``n_expected`` counts
                  every period the frequency requires over the series' own
                  span (anchored on its first period)

Boundary semantics: an empty series has ``n_expected == 0`` and coverage
``0.0`` (not a division-by-zero, and not a silent 1.0). A series with one
period is fully covered by definition (``n_expected == 1``).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from macropulse.quality.assessment import expected_periods


@dataclass(frozen=True)
class MissingnessReport:
    frequency: str
    n_observed: int
    n_missing: int
    n_gaps: int
    n_expected: int
    coverage: float
    missing_reasons: tuple[tuple[str, int], ...]
    gap_periods: tuple

    @property
    def fully_covered(self) -> bool:
        return self.n_observed == self.n_expected and self.n_expected > 0


def missingness_report(records, frequency: str) -> MissingnessReport:
    """Build the missingness report for one normalized series.

    ``records``: sequence exposing ``period``, ``value``, ``missing_reason``
    (NormalizedRecord or NormalizedObservation rows).
    """
    if not records:
        return MissingnessReport(
            frequency=frequency,
            n_observed=0,
            n_missing=0,
            n_gaps=0,
            n_expected=0,
            coverage=0.0,
            missing_reasons=(),
            gap_periods=(),
        )

    n_observed = sum(1 for r in records if r.value is not None)
    n_missing = sum(1 for r in records if r.value is None)

    reasons = Counter(
        r.missing_reason for r in records if r.value is None and r.missing_reason
    )

    periods = sorted({r.period for r in records})
    expected = expected_periods(frequency, periods[0], periods[-1])
    gap_periods = tuple(p for p in expected if p not in set(periods))

    n_expected = len(expected)
    coverage = n_observed / n_expected if n_expected else 0.0

    return MissingnessReport(
        frequency=frequency,
        n_observed=n_observed,
        n_missing=n_missing,
        n_gaps=len(gap_periods),
        n_expected=n_expected,
        coverage=coverage,
        missing_reasons=tuple(reasons.most_common()),
        gap_periods=gap_periods,
    )


__all__ = ["MissingnessReport", "missingness_report"]
