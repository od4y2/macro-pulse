"""Publication gates (unit S09).

Deterministic rules deciding whether a series may be PUBLISHED (shown as
data in the dashboard/briefing layers). A gate never silently drops
anything: every failed check contributes an explicit reason code, and a
passing series has an empty reason list. Full documentation:
docs/StandardizationRules.md.

Design choice: gates check the underlying CONDITIONS (coverage, counts,
evidence, chronology), not the S07 grade labels. Grades summarize the
same conditions after the fact; gating on conditions keeps one source of
truth - a series does not fail twice for the same problem, and the gate
reason always names the verifiable fact.

Reason codes (closed set):
- ``coverage_below_minimum``   observed/expected < thresholds.min_coverage
- ``too_few_observations``     n_observed < thresholds.min_observed
- ``not_real_evidence``        a latest-vintage record is not labelled real
- ``impossible_chronology``    a latest-vintage vintage precedes its period

Default thresholds and their rationale (documented, not magic):
- ``min_coverage`` 0.5 - majority of expected periods observed; a series
  observed less than half its span describes the span poorly.
- ``min_observed`` 3 - the same minimum where a median is an observed
  value (matches MIN_WINDOW_OCCUPANCY in standardize.py).
- ``require_real`` True - mocked/synthetic/cached series are never
  published as observed data (S01 evidence governance).
"""

from __future__ import annotations

from dataclasses import dataclass

from macropulse.quality.missingness import MissingnessReport

GATE_REASONS = (
    "coverage_below_minimum",
    "too_few_observations",
    "not_real_evidence",
    "impossible_chronology",
)


@dataclass(frozen=True)
class GateThresholds:
    min_coverage: float = 0.5
    min_observed: int = 3
    require_real: bool = True


# Frozen singleton: the documented default thresholds (B008-safe default).
DEFAULT_GATE_THRESHOLDS = GateThresholds()


@dataclass(frozen=True)
class GateCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class GateResult:
    """Gate outcome for one (metric, country) series."""

    metric: str
    published: bool
    reasons: tuple[str, ...]
    checks: tuple[GateCheck, ...]


def evaluate_gate(
    metric: str,
    report: MissingnessReport,
    latest_records,
    thresholds: GateThresholds = DEFAULT_GATE_THRESHOLDS,
) -> GateResult:
    """Evaluate publication rules for one series.

    ``latest_records``: latest-vintage records (rows or records exposing
    ``evidence_label``, ``vintage``, ``period``); the current view only,
    as loaded by ``engine.latest_vintage_records``.
    """
    checks: list[GateCheck] = []

    coverage_ok = report.coverage >= thresholds.min_coverage
    checks.append(
        GateCheck(
            "coverage",
            coverage_ok,
            f"coverage={report.coverage:.3f} (min {thresholds.min_coverage})",
        )
    )

    observed_ok = report.n_observed >= thresholds.min_observed
    checks.append(
        GateCheck(
            "observations",
            observed_ok,
            f"n_observed={report.n_observed} (min {thresholds.min_observed})",
        )
    )

    if thresholds.require_real:
        non_real = [
            r for r in latest_records if r.evidence_label != "real"
        ]
        real_ok = not non_real
        checks.append(
            GateCheck(
                "evidence",
                real_ok,
                (
                    "all latest-vintage records are real"
                    if real_ok
                    else f"{len(non_real)} latest-vintage record(s) not labelled real"
                ),
            )
        )
    else:
        real_ok = True

    bad_chronology = [r for r in latest_records if r.vintage < r.period]
    chronology_ok = not bad_chronology
    checks.append(
        GateCheck(
            "chronology",
            chronology_ok,
            (
                "all vintages follow their periods"
                if chronology_ok
                else f"{len(bad_chronology)} record(s) with vintage before period"
            ),
        )
    )

    reasons: list[str] = []
    if not coverage_ok:
        reasons.append("coverage_below_minimum")
    if not observed_ok:
        reasons.append("too_few_observations")
    if not real_ok:
        reasons.append("not_real_evidence")
    if not chronology_ok:
        reasons.append("impossible_chronology")

    return GateResult(
        metric=metric,
        published=not reasons,
        reasons=tuple(reasons),
        checks=tuple(checks),
    )


__all__ = [
    "GATE_REASONS",
    "GateCheck",
    "GateResult",
    "GateThresholds",
    "evaluate_gate",
]
