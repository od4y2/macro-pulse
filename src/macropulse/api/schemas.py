"""Pydantic schemas locking the MacroPulse query-service API contract (unit S03).

These schemas define the response shapes the S13 FastAPI service must
implement. Defining them now (before any endpoint code) pins the contract
between the database layer and the service layer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from macropulse.scope import EVIDENCE_LABELS

EvidenceLabel = Literal["real", "synthetic", "mocked", "cached", "external"]

_QUALITY_GRADES = ("ungraded", "official", "preliminary", "revised", "estimated", "flagged")


class CountryOut(BaseModel):
    iso3: str = Field(min_length=3, max_length=3)
    name: str
    rationale: str


class IndicatorOut(BaseModel):
    indicator_id: str
    name: str
    module: str
    unit: str
    frequency: str
    seasonal_adjustment: str
    fallback_status: str


class SourceOut(BaseModel):
    system: str
    code: str
    role: str
    verified: str
    coverage: str


class ObservationOut(BaseModel):
    """Every field of the provenance contract travels with the value."""

    indicator_id: str
    country_iso3: str
    period: date
    value: float | None  # None means missing - never silently imputed
    unit: str
    frequency: str
    seasonal_adjustment: str
    source: SourceOut
    release_time: datetime
    retrieval_time: datetime
    vintage: date
    evidence_label: EvidenceLabel
    quality_grade: str
    missing_reason: str | None = None

    model_config = {"extra": "forbid"}


class MetricOut(BaseModel):
    metric_key: str
    country_iso3: str
    period: date
    value: float
    formula_ref: str
    version: str


class BriefingClaimOut(BaseModel):
    claim_text: str
    evidence_refs: list[int]
    validated: bool


class BriefingOut(BaseModel):
    created_at: datetime
    model: str
    prompt_version: str
    status: str
    claims: list[BriefingClaimOut]


class HealthOut(BaseModel):
    status: str
    data_mode: str


def validate_evidence_label(label: str) -> bool:
    """Contract guard: only the five locked S01 labels are valid."""
    return label in EVIDENCE_LABELS


def validate_quality_grade(grade: str) -> bool:
    return grade in _QUALITY_GRADES
