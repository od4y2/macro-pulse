"""Release sweep (unit S20): gate the whole catalog, derive what passes.

One release pass over the governed store answers the release question the
S09 gates were built for: which catalog series may be published, and what
does the derived layer hold for them?

- The PLAN is the scheduled-refresh plan (``plan_series``): every catalog
  indicator crossed with the countries its primary source covers.
- The GATE is the S09 publication gate, evaluated on the latest-vintage
  view with the closed reason vocabulary - a held series is reported with
  its named reasons, never silently dropped.
- The DERIVE step materializes the S09 robust standardization for every
  published series through the S08 engine (``persist_derived``), so every
  derived row carries the same lineage and version rows as the S18 demo
  path. Window is in frequency steps; the metric key names it
  (``{indicator_id}.robust_z{window}``), matching the S18 convention.

Idempotency: derived identity is (metric_key, country, period)
(``uq_metric_identity``), so a re-run can never store a second value for
the same point. A recomputed value that matches the stored one is skipped
(``derived_unchanged``). One that differs - its inputs were revised since
the last derive - REPLACES the stored row (delete + re-insert through the
same governed writer; ``metric_versions`` cascade) and is counted as
``derived_replaced``. The derived layer is a materialization of the
normalized layer; observed data is never touched by this module.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Any

from macropulse.catalog import CATALOG
from macropulse.db.models import DerivedMetric
from macropulse.metrics.engine import (
    latest_vintage_records,
    latest_vintage_series,
    observation_id_map,
    persist_derived,
)
from macropulse.metrics.gates import (
    DEFAULT_GATE_THRESHOLDS,
    GateThresholds,
    evaluate_gate,
)
from macropulse.metrics.standardize import standardize_series
from macropulse.ops.refresh import SeriesTarget, plan_series
from macropulse.quality.missingness import missingness_report

DEFAULT_RELEASE_WINDOW = 5  # frequency steps; matches the S18 demo convention


@dataclass(frozen=True)
class SeriesRelease:
    """Release outcome for one planned (indicator, country) series."""

    indicator_id: str
    country_iso3: str
    metric_key: str
    published: bool
    reasons: tuple[str, ...]
    coverage: float
    n_observed: int
    n_expected: int
    derived_new: int = 0
    derived_unchanged: int = 0
    derived_replaced: int = 0

    def line(self) -> str:
        """One report line for this series."""
        if self.published:
            derived = (
                f" derived new={self.derived_new} unchanged={self.derived_unchanged}"
                f" replaced={self.derived_replaced}"
            )
            return (
                f"PUBLISH {self.indicator_id}/{self.country_iso3}"
                f" coverage={self.coverage:.3f} observed={self.n_observed}"
                f"/{self.n_expected}{derived}"
            )
        return (
            f"HOLD    {self.indicator_id}/{self.country_iso3}"
            f" coverage={self.coverage:.3f} observed={self.n_observed}"
            f"/{self.n_expected} reasons={','.join(self.reasons)}"
        )


@dataclass(frozen=True)
class ReleaseReport:
    """The full sweep result, summarizable and renderable as text."""

    window: int
    derive: bool
    series: tuple[SeriesRelease, ...]

    def summary(self) -> dict[str, Any]:
        published = sum(1 for s in self.series if s.published)
        held_reasons = Counter(
            reason for s in self.series if not s.published for reason in s.reasons
        )
        return {
            "window": self.window,
            "derive": self.derive,
            "series_total": len(self.series),
            "published": published,
            "held": len(self.series) - published,
            "held_by_reason": dict(sorted(held_reasons.items())),
            "derived_new": sum(s.derived_new for s in self.series),
            "derived_unchanged": sum(s.derived_unchanged for s in self.series),
            "derived_replaced": sum(s.derived_replaced for s in self.series),
        }

    def to_text(self) -> str:
        """Deterministic full report (header, one line per series, summary)."""
        lines = [
            (
                f"release sweep: window={self.window} derive={self.derive}"
                f" series={len(self.series)}"
            ),
        ]
        lines.extend(s.line() for s in self.series)
        summary = self.summary()
        lines.append(
            f"summary: {summary['published']}/{summary['series_total']} published,"
            f" {summary['held']} held"
        )
        for reason, count in summary["held_by_reason"].items():
            lines.append(f"  held {reason}: {count}")
        if self.derive:
            lines.append(
                "derived: new={derived_new} unchanged={derived_unchanged}"
                " replaced={derived_replaced}".format(**summary)
            )
        return "\n".join(lines)


def _derive_counts(
    session,
    metric_key: str,
    country_iso3: str,
    standardized,
    id_map,
) -> tuple[int, int, int]:
    """Write computable standardized points, idempotently.

    Returns (new, unchanged, replaced) counts. Deletions flush before the
    inserts so a replaced point never collides with its own predecessor on
    ``uq_metric_identity`` inside one transaction.
    """
    existing = {
        row.period: row
        for row in session.query(DerivedMetric)
        .filter_by(metric_key=metric_key, country_iso3=country_iso3)
        .all()
    }
    fresh: list = []
    unchanged = 0
    stale: list = []
    for point in standardized:
        if point.value is None:
            continue  # explicit non-fabrication: no row for missing outputs
        prior = existing.get(point.period)
        if prior is None:
            fresh.append(point)
        elif float(prior.value) == point.value:
            unchanged += 1
        else:
            stale.append(prior)
            fresh.append(point)
    for prior in stale:
        session.delete(prior)  # metric_versions rows cascade
    if stale:
        session.flush()
    persist_derived(
        session, metric_key, country_iso3, fresh, "robust_z", id_map
    )
    return len(fresh) - len(stale), unchanged, len(stale)


def release_sweep(
    session,
    window: int = DEFAULT_RELEASE_WINDOW,
    derive: bool = True,
    indicator_ids=None,
    country_iso3s=None,
    thresholds: GateThresholds = DEFAULT_GATE_THRESHOLDS,
) -> ReleaseReport:
    """Gate every planned series; materialize robust_z for published ones.

    ``indicator_ids``/``country_iso3s`` restrict the plan (same semantics
    as ``plan_series``). Held series are outcomes, not errors: the report
    carries their named gate reasons.
    """
    targets: list[SeriesTarget] = plan_series(indicator_ids, country_iso3s)
    catalog_by_id = {i.indicator_id: i for i in CATALOG}
    outcomes: list[SeriesRelease] = []
    for target in targets:
        entry = catalog_by_id[target.indicator_id]
        metric_key = f"{target.indicator_id}.robust_z{window}"
        points = latest_vintage_series(session, target.indicator_id, target.country_iso3)
        records = latest_vintage_records(session, target.indicator_id, target.country_iso3)
        report = missingness_report(points, entry.frequency)
        gate = evaluate_gate(
            f"{target.indicator_id}/{target.country_iso3}", report, records, thresholds
        )
        outcome = SeriesRelease(
            indicator_id=target.indicator_id,
            country_iso3=target.country_iso3,
            metric_key=metric_key,
            published=gate.published,
            reasons=gate.reasons,
            coverage=report.coverage,
            n_observed=report.n_observed,
            n_expected=report.n_expected,
        )
        if gate.published and derive:
            standardized = standardize_series(
                points, window, entry.direction, entry.frequency
            )
            id_map = observation_id_map(session, target.indicator_id, target.country_iso3)
            new, unchanged, replaced = _derive_counts(
                session, metric_key, target.country_iso3, standardized, id_map
            )
            session.commit()
            outcome = replace(
                outcome,
                derived_new=new,
                derived_unchanged=unchanged,
                derived_replaced=replaced,
            )
        outcomes.append(outcome)
    return ReleaseReport(window=window, derive=derive, series=tuple(outcomes))


__all__ = [
    "DEFAULT_RELEASE_WINDOW",
    "ReleaseReport",
    "SeriesRelease",
    "release_sweep",
]
