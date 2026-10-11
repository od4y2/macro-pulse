"""Data query endpoints (unit S13): typed, paginated, filterable.

Serves the normalized database through the S03-pinned response schemas
(``macropulse.api.schemas``). Every observation carries its full provenance
contract (source, release and retrieval times, vintage, evidence label,
quality grade, missing reason); missing values are returned as ``null``
with a named ``missing_reason`` and are never imputed.

Pagination contract for every list endpoint: ``limit`` (default 50, max
500) and ``offset`` rows into the deterministically ordered result, with
the unpaginated count of the filtered set in the ``X-Total-Count``
response header.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response
from sqlalchemy import ColumnElement, and_, func
from sqlalchemy.orm import selectinload

from macropulse.api.deps import DbSession
from macropulse.api.schemas import (
    QUALITY_GRADES,
    CountryOut,
    EvidenceLabel,
    IndicatorOut,
    MetricOut,
    ObservationOut,
    SourceOut,
)
from macropulse.db.models import (
    Country,
    DerivedMetric,
    Indicator,
    MetricVersion,
    NormalizedObservation,
    SourceCatalogEntry,
)
from macropulse.scope import MODULES

router = APIRouter(tags=["data"])

# Pagination bounds: small enough to keep responses inspectable, large
# enough that the panel (10 economies x annual series) fits one page.
DEFAULT_LIMIT = 50
MAX_LIMIT = 500

# Pagination markers (Annotated so the Query call stays out of defaults;
# the default value itself is given explicitly in each signature).
PageLimit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
PageOffset = Annotated[int, Query(ge=0)]

# Closed vocabularies re-used from the locked scope/catalog so invalid
# filter values fail with 422 instead of silently matching nothing.
ModuleFilter = Literal[MODULES]
QualityGradeFilter = Literal[QUALITY_GRADES]


def _observation_out(
    obs: NormalizedObservation, src: SourceCatalogEntry
) -> ObservationOut:
    """Assemble the pinned observation shape; None value stays None."""
    return ObservationOut(
        indicator_id=obs.indicator_id,
        country_iso3=obs.country_iso3,
        period=obs.period,
        value=None if obs.value is None else float(obs.value),
        unit=obs.unit,
        frequency=obs.frequency,
        seasonal_adjustment=obs.seasonal_adjustment,
        source=SourceOut(
            system=src.system,
            code=src.code,
            role=src.role,
            verified=src.verified,
            coverage=src.coverage,
        ),
        release_time=obs.release_time,
        retrieval_time=obs.retrieval_time,
        vintage=obs.vintage,
        evidence_label=obs.evidence_label,
        quality_grade=obs.quality_grade,
        missing_reason=obs.missing_reason,
    )


def _latest_version(versions: list[MetricVersion]) -> MetricVersion | None:
    """Newest recorded definition: creation time first, version as tiebreak."""
    if not versions:
        return None
    return max(versions, key=lambda v: (v.created_at, v.version))


@router.get("/countries", response_model=list[CountryOut])
def list_countries(
    db: DbSession,
    response: Response,
    limit: PageLimit = DEFAULT_LIMIT,
    offset: PageOffset = 0,
) -> list[CountryOut]:
    query = db.query(Country)
    response.headers["X-Total-Count"] = str(query.count())
    rows = query.order_by(Country.iso3).limit(limit).offset(offset).all()
    return [CountryOut(iso3=c.iso3, name=c.name, rationale=c.rationale) for c in rows]


@router.get("/indicators", response_model=list[IndicatorOut])
def list_indicators(
    db: DbSession,
    response: Response,
    module: ModuleFilter | None = None,
    limit: PageLimit = DEFAULT_LIMIT,
    offset: PageOffset = 0,
) -> list[IndicatorOut]:
    query = db.query(Indicator)
    if module is not None:
        query = query.filter(Indicator.module == module)
    response.headers["X-Total-Count"] = str(query.count())
    rows = query.order_by(Indicator.indicator_id).limit(limit).offset(offset).all()
    return [
        IndicatorOut(
            indicator_id=i.indicator_id,
            name=i.name,
            module=i.module,
            unit=i.unit,
            frequency=i.frequency,
            seasonal_adjustment=i.seasonal_adjustment,
            fallback_status=i.fallback_status,
        )
        for i in rows
    ]


@router.get("/observations", response_model=list[ObservationOut])
def list_observations(
    db: DbSession,
    response: Response,
    indicator_id: str | None = None,
    country_iso3: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    vintage: date | None = None,
    evidence_label: EvidenceLabel | None = None,
    quality_grade: QualityGradeFilter | None = None,
    missing: bool | None = None,
    latest_vintage: bool = False,
    limit: PageLimit = DEFAULT_LIMIT,
    offset: PageOffset = 0,
) -> list[ObservationOut]:
    """Filter the normalized observation store.

    ``latest_vintage=True`` keeps, per (indicator, country, period, source)
    group, only the newest vintage among the rows matching the other
    filters - so evidence-label or quality filters restrict which vintages
    compete rather than being applied after the fact. ``missing=True``
    selects rows whose value is NULL (each carries a missing_reason);
    ``missing=False`` selects rows with a value.
    """
    filters: list[ColumnElement[bool]] = []
    if indicator_id is not None:
        filters.append(NormalizedObservation.indicator_id == indicator_id)
    if country_iso3 is not None:
        filters.append(NormalizedObservation.country_iso3 == country_iso3)
    if period_start is not None:
        filters.append(NormalizedObservation.period >= period_start)
    if period_end is not None:
        filters.append(NormalizedObservation.period <= period_end)
    if vintage is not None:
        filters.append(NormalizedObservation.vintage == vintage)
    if evidence_label is not None:
        filters.append(NormalizedObservation.evidence_label == evidence_label)
    if quality_grade is not None:
        filters.append(NormalizedObservation.quality_grade == quality_grade)
    if missing is True:
        filters.append(NormalizedObservation.value.is_(None))
    elif missing is False:
        filters.append(NormalizedObservation.value.isnot(None))

    query = db.query(NormalizedObservation, SourceCatalogEntry).join(
        SourceCatalogEntry, NormalizedObservation.source_id == SourceCatalogEntry.id
    )
    for f in filters:
        query = query.filter(f)

    if latest_vintage:
        sub = db.query(
            NormalizedObservation.indicator_id.label("indicator_id"),
            NormalizedObservation.country_iso3.label("country_iso3"),
            NormalizedObservation.period.label("period"),
            NormalizedObservation.source_id.label("source_id"),
            func.max(NormalizedObservation.vintage).label("max_vintage"),
        )
        for f in filters:
            sub = sub.filter(f)
        latest_sq = sub.group_by(
            NormalizedObservation.indicator_id,
            NormalizedObservation.country_iso3,
            NormalizedObservation.period,
            NormalizedObservation.source_id,
        ).subquery()
        query = query.join(
            latest_sq,
            and_(
                NormalizedObservation.indicator_id == latest_sq.c.indicator_id,
                NormalizedObservation.country_iso3 == latest_sq.c.country_iso3,
                NormalizedObservation.period == latest_sq.c.period,
                NormalizedObservation.source_id == latest_sq.c.source_id,
                NormalizedObservation.vintage == latest_sq.c.max_vintage,
            ),
        )

    response.headers["X-Total-Count"] = str(query.count())
    rows = (
        query.order_by(
            NormalizedObservation.indicator_id,
            NormalizedObservation.country_iso3,
            NormalizedObservation.period,
            NormalizedObservation.vintage,
            NormalizedObservation.id,
        )
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [_observation_out(obs, src) for obs, src in rows]


@router.get("/metrics", response_model=list[MetricOut])
def list_metrics(
    db: DbSession,
    response: Response,
    metric_key: str | None = None,
    country_iso3: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    limit: PageLimit = DEFAULT_LIMIT,
    offset: PageOffset = 0,
) -> list[MetricOut]:
    """List derived metrics with their latest recorded version.

    A derived metric with no recorded version row is skipped rather than
    served with an invented version string. Sanctioned write paths
    (``macropulse.metrics.engine.persist_derived``) always record one, so
    this only guards against out-of-contract rows.
    """
    query = db.query(DerivedMetric)
    if metric_key is not None:
        query = query.filter(DerivedMetric.metric_key == metric_key)
    if country_iso3 is not None:
        query = query.filter(DerivedMetric.country_iso3 == country_iso3)
    if period_start is not None:
        query = query.filter(DerivedMetric.period >= period_start)
    if period_end is not None:
        query = query.filter(DerivedMetric.period <= period_end)
    response.headers["X-Total-Count"] = str(query.count())
    rows = (
        query.options(selectinload(DerivedMetric.versions))
        .order_by(
            DerivedMetric.metric_key,
            DerivedMetric.country_iso3,
            DerivedMetric.period,
        )
        .limit(limit)
        .offset(offset)
        .all()
    )
    out: list[MetricOut] = []
    for m in rows:
        version = _latest_version(m.versions)
        if version is None:
            continue
        out.append(
            MetricOut(
                metric_key=m.metric_key,
                country_iso3=m.country_iso3,
                period=m.period,
                value=float(m.value),
                formula_ref=m.formula_ref,
                version=version.version,
            )
        )
    return out
