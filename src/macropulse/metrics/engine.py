"""Derived-metric engine (unit S08).

Glue between the normalized store and the derived store:
- ``latest_vintage_series`` reads one (indicator, country) series at its
  LATEST vintage per period (S07 superseded semantics) as transform input;
- ``persist_derived`` writes computed values to ``derived_metrics`` with
  full lineage (input observation ids in the ``inputs`` JSON) and records
  the formula definition in ``metric_versions``.

Metric key convention: ``{indicator_id}.{formula_name}`` e.g.
``cpi_inflation.yoy``. Identity is (metric_key, country, period) per the
S03 contract; a derived value is written only when computable (the
schema's NOT NULL value). Missing outputs stay in the returned list with
their reasons - the derived layer never fabricates a row for them, and
whether a value should exist is derivable from source coverage.
"""

from __future__ import annotations

from datetime import date

from macropulse.db.models import DerivedMetric, MetricVersion, NormalizedObservation
from macropulse.metrics.transforms import FORMULAS, DerivedPoint, SeriesPoint


class DeriveError(RuntimeError):
    """Raised when derived persistence violates the rules."""


def latest_vintage_series(
    session, indicator_id: str, country_iso3: str
) -> list[SeriesPoint]:
    """Latest-vintage points for one (indicator, country), period order.

    Reads all vintages and keeps, per period, the newest one (revision
    transparency: superseded vintages stay in the store; transforms
    consume the current view). NULL values pass through with their
    missing_reason so transforms surface them honestly.
    """
    rows = (
        session.query(NormalizedObservation)
        .filter_by(indicator_id=indicator_id, country_iso3=country_iso3)
        .order_by(NormalizedObservation.period, NormalizedObservation.vintage)
        .all()
    )
    latest: dict[date, NormalizedObservation] = {}
    for row in rows:  # ordered oldest -> newest; last write wins
        latest[row.period] = row
    return [
        SeriesPoint(
            period=row.period,
            value=float(row.value) if row.value is not None else None,
            missing_reason=row.missing_reason,
        )
        for row in sorted(latest.values(), key=lambda r: r.period)
    ]


def observation_id_map(
    session, indicator_id: str, country_iso3: str
) -> dict[date, int]:
    """Latest-vintage observation id per period (for lineage recording)."""
    rows = (
        session.query(NormalizedObservation)
        .filter_by(indicator_id=indicator_id, country_iso3=country_iso3)
        .order_by(NormalizedObservation.period, NormalizedObservation.vintage)
        .all()
    )
    latest: dict[date, int] = {}
    for row in rows:
        latest[row.period] = row.id
    return latest


def persist_derived(
    session,
    metric_key: str,
    country_iso3: str,
    derived: list[DerivedPoint],
    formula_name: str,
    id_map: dict[date, int],
    version: str = "v1",
) -> list[DerivedMetric]:
    """Write computable derived points to ``derived_metrics``.

    ``id_map`` maps input periods to normalized observation ids (lineage).
    Only points with a value are written; missing points are skipped by
    design (the schema forbids NULL derived values and we never fabricate
    one). Each written row also gets a ``metric_versions`` row carrying
    the formula definition text (idempotent per (metric, version)).
    """
    if formula_name not in FORMULAS:
        raise DeriveError(
            f"unknown formula {formula_name!r}; definitions live in FORMULAS"
        )

    written: list[DerivedMetric] = []
    for point in derived:
        if point.value is None:
            continue  # explicit non-fabrication: no row for missing outputs
        input_ids = sorted(
            id_map[p] for p in point.input_periods if p in id_map
        )
        row = DerivedMetric(
            metric_key=metric_key,
            country_iso3=country_iso3,
            period=point.period,
            value=point.value,
            formula_ref=formula_name,
            inputs={"observation_ids": input_ids},
        )
        session.add(row)
        session.flush()  # materialize row.id for the version link
        session.add(
            MetricVersion(
                metric_id=row.id,
                version=version,
                definition=FORMULAS[formula_name],
            )
        )
        written.append(row)
    session.flush()
    return written


__all__ = [
    "DeriveError",
    "latest_vintage_series",
    "observation_id_map",
    "persist_derived",
]
