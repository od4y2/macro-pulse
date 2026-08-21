"""Normalization pipeline (unit S06).

Pure, deterministic rules unifying fetched connector series into governed
normalized observations. Every rule is documented here and in
docs/NormalizationRules.md; there are no magic constants.

Unification rules:
- **Country**: FetchedSeries already carries ISO3; normalization rejects
  codes outside the allowed panel (the locked S01 country set).
- **Period**: taken verbatim from the connector (dates are already unified:
  annual -> year start, FRED monthly -> month start).
- **Unit**: the catalog indicator's unit is canonical. Values pass through
  UNCHANGED - normalization never converts units (index->YoY etc. is S08's
  job and must be a labelled derived metric).
- **Frequency**: inferred from the median month-gap between consecutive
  periods (1 -> monthly, 3 -> quarterly, 12 -> annual). A single point
  cannot be inferred and must be supplied explicitly.
- **Seasonal adjustment**: caller-supplied, defaulting to the catalog
  indicator's value. Sources differ (e.g. FRED CPIAUCSL is SA while the WB
  canonical is NSA), so the applied value is recorded per observation -
  never silently defaulted when it differs from the canonical.
- **Vintage**: FRED points carry their own realtime_start; WB/ILOSTAT
  points carry the retrieval date (snapshot semantics, set by connectors).
- **Release time**: FRED/WB/ILOSTAT expose no per-observation release
  timestamp in these endpoints; recorded as retrieval_time (documented
  limitation, refined in S07).
- **Missingness**: value None keeps its connector missing_reason; values
  are never imputed, interpolated, or dropped.
- **Quality**: ungraded at this stage; grading is S07's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date
from itertools import pairwise
from statistics import median

from macropulse.catalog import CATALOG, FREQUENCIES, SEASONAL_ADJUSTMENTS
from macropulse.connectors.base import FetchedPoint, FetchedSeries
from macropulse.scope import EVIDENCE_LABELS

# Median month-gap -> frequency name. Gaps are in whole months.
_FREQUENCY_BY_GAP = {1: "monthly", 3: "quarterly", 12: "annual"}


class NormalizationError(RuntimeError):
    """Raised when a series cannot be normalized under the locked rules."""


def panel_countries() -> frozenset[str]:
    """The locked S01 panel (source of truth for country validation)."""
    from macropulse.scope import COUNTRIES

    return frozenset(c.iso3 for c in COUNTRIES)


@dataclass(frozen=True)
class NormalizedRecord:
    indicator_id: str
    country_iso3: str
    period: date
    value: float | None
    missing_reason: str | None
    unit: str
    frequency: str
    seasonal_adjustment: str
    source_system: str
    source_code: str
    release_time: date
    retrieval_time: date
    vintage: date
    evidence_label: str
    quality_grade: str = "ungraded"


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def infer_frequency(points: list[FetchedPoint]) -> str:
    """Infer frequency from the median month gap of consecutive periods."""
    if len(points) < 2:
        raise NormalizationError(
            "cannot infer frequency from fewer than 2 points; pass it explicitly"
        )
    periods = sorted(p.period for p in points)
    if len(set(periods)) != len(periods):
        raise NormalizationError("duplicate periods in series")
    gaps = [_months_between(a, b) for a, b in pairwise(periods)]
    typical = median(gaps)
    if typical != int(typical) or int(typical) not in _FREQUENCY_BY_GAP:
        raise NormalizationError(
            f"cannot unify frequency: median gap {typical} months is not one of "
            f"{sorted(_FREQUENCY_BY_GAP)}"
        )
    return _FREQUENCY_BY_GAP[int(typical)]


def _catalog_indicator(indicator_id: str):
    for ind in CATALOG:
        if ind.indicator_id == indicator_id:
            return ind
    raise NormalizationError(f"indicator {indicator_id!r} is not in the catalog")


def normalize_series(
    series: FetchedSeries,
    indicator_id: str,
    seasonal_adjustment: str | None = None,
    frequency: str | None = None,
    allowed_countries: frozenset[str] | None = None,
) -> list[NormalizedRecord]:
    """Normalize one fetched series into governed records.

    ``seasonal_adjustment`` defaults to the catalog indicator's value;
    ``frequency`` is inferred from the points unless given.
    """
    allowed = allowed_countries if allowed_countries is not None else panel_countries()
    if series.country_iso3 not in allowed:
        raise NormalizationError(
            f"country {series.country_iso3!r} is outside the allowed panel"
        )
    indicator = _catalog_indicator(indicator_id)

    if seasonal_adjustment is None:
        seasonal_adjustment = indicator.seasonal_adjustment
    if seasonal_adjustment not in SEASONAL_ADJUSTMENTS:
        raise NormalizationError(
            f"invalid seasonal_adjustment {seasonal_adjustment!r}"
        )
    if frequency is None:
        frequency = infer_frequency(list(series.points))
    elif frequency not in FREQUENCIES:
        raise NormalizationError(f"invalid frequency {frequency!r}")
    if series.evidence_label not in EVIDENCE_LABELS:
        raise NormalizationError(
            f"invalid evidence label {series.evidence_label!r}"
        )

    seen: set[date] = set()
    records: list[NormalizedRecord] = []
    for point in series.points:
        if point.period in seen:
            raise NormalizationError(
                f"duplicate period {point.period} in {series.series_id}"
            )
        seen.add(point.period)
        if point.value is None and not point.missing_reason:
            raise NormalizationError(
                f"missing value at {point.period} has no missing_reason "
                "(hidden missingness is not allowed)"
            )
        if point.value is not None and point.missing_reason:
            raise NormalizationError(
                f"point at {point.period} has both a value and a missing_reason"
            )
        records.append(
            NormalizedRecord(
                indicator_id=indicator_id,
                country_iso3=series.country_iso3,
                period=point.period,
                value=point.value,
                missing_reason=point.missing_reason,
                unit=indicator.unit,  # canonical unit; no conversion
                frequency=frequency,
                seasonal_adjustment=seasonal_adjustment,
                source_system=series.system,
                source_code=series.series_id,
                release_time=series.retrieval_time.date(),  # documented proxy
                retrieval_time=series.retrieval_time.date(),
                vintage=point.vintage,
                evidence_label=series.evidence_label,
            )
        )
    return records


def persist_normalized(session, records: list[NormalizedRecord], source_id: int):
    """Write normalized records; the schema's unique constraint rejects
    duplicate (indicator, country, period, vintage, source) identities."""
    from macropulse.db.models import NormalizedObservation

    rows = [
        NormalizedObservation(
            indicator_id=r.indicator_id,
            country_iso3=r.country_iso3,
            period=r.period,
            value=r.value,
            unit=r.unit,
            frequency=r.frequency,
            seasonal_adjustment=r.seasonal_adjustment,
            source_id=source_id,
            release_time=_as_utc(r.release_time),
            retrieval_time=_as_utc(r.retrieval_time),
            vintage=r.vintage,
            evidence_label=r.evidence_label,
            quality_grade=r.quality_grade,
            missing_reason=r.missing_reason,
        )
        for r in records
    ]
    session.add_all(rows)
    session.flush()
    return rows


def _as_utc(day: date):
    from datetime import datetime

    return datetime(day.year, day.month, day.day, tzinfo=UTC)


__all__ = [
    "NormalizationError",
    "NormalizedRecord",
    "infer_frequency",
    "normalize_series",
    "panel_countries",
    "persist_normalized",
]
