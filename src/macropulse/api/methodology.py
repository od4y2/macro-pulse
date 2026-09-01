"""Methodology endpoints (unit S13): formula registry and metric definitions.

Two traceability surfaces:

- ``/methodology/formulas`` serves the implemented formula registry
  (``macropulse.metrics.transforms.FORMULAS``) - the code-level source of
  truth for every transformation, so a metric's ``formula_ref`` always
  resolves to the definition that produced it.
- ``/methodology/metrics/{metric_key}`` serves the definitions actually
  recorded in the database (``metric_versions`` rows written by
  ``persist_derived``), newest version first - the per-metric audit trail
  of what was computed and when.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from macropulse.api.deps import DbSession
from macropulse.db.models import DerivedMetric, MetricVersion
from macropulse.metrics.transforms import FORMULAS

router = APIRouter(prefix="/methodology", tags=["methodology"])


class FormulaOut(BaseModel):
    name: str
    definition: str


class MetricDefinitionOut(BaseModel):
    metric_key: str
    version: str
    definition: str
    recorded_at: datetime


@router.get("/formulas", response_model=list[FormulaOut])
def list_formulas(name: str | None = None) -> list[FormulaOut]:
    """The implemented formula registry; an unknown ``name`` yields []."""
    names = sorted(FORMULAS)
    if name is not None:
        names = [n for n in names if n == name]
    return [FormulaOut(name=n, definition=FORMULAS[n]) for n in names]


@router.get("/metrics/{metric_key}", response_model=list[MetricDefinitionOut])
def metric_definitions(
    metric_key: str,
    db: DbSession,
) -> list[MetricDefinitionOut]:
    """Recorded definitions for one metric key, newest first.

    404 when the metric key has no recorded definitions at all - an
    unknown key must not silently read as "no methodology".
    """
    rows = (
        db.query(
            DerivedMetric.metric_key,
            MetricVersion.version,
            MetricVersion.definition,
            MetricVersion.created_at,
        )
        .join(MetricVersion, MetricVersion.metric_id == DerivedMetric.id)
        .filter(DerivedMetric.metric_key == metric_key)
        .distinct()
        .order_by(MetricVersion.created_at.desc(), MetricVersion.version.desc())
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"unknown metric_key: {metric_key} (no recorded definitions)",
        )
    return [
        MetricDefinitionOut(
            metric_key=r.metric_key,
            version=r.version,
            definition=r.definition,
            recorded_at=r.created_at,
        )
        for r in rows
    ]
