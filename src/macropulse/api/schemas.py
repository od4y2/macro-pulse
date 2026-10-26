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
# Public alias: the quality module (S07) imports the same tuple so the API
# contract stays the single source of truth for the grade vocabulary.
QUALITY_GRADES = _QUALITY_GRADES


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


class FactRefOut(BaseModel):
    """One cited observation's identity - the wire shape of FactRef.

    The persisted ``briefing_claims.evidence_refs`` are FactRef dumps
    (the S03 observation identity), not integer observation ids, so the
    claim schema mirrors the 6-field reference exactly.
    """

    indicator_id: str
    country_iso3: str
    period: str
    vintage: str
    source_system: str
    source_code: str


class BriefingClaimOut(BaseModel):
    claim_text: str
    evidence_refs: list[FactRefOut]
    validated: bool


class BriefingOut(BaseModel):
    """One persisted briefing run (GET /briefing/{run_id}).

    The prose itself is not persisted - ``briefing_runs`` records the
    generator identity, status, and adjudicated claims (the audit trail);
    the document is re-renderable from those inputs.
    """

    id: int
    created_at: datetime
    model: str
    prompt_version: str
    status: str
    claims: list[BriefingClaimOut]


class BriefingGenerateRequest(BaseModel):
    # Length-pinned so a malformed code is an automatic 422, never a
    # silent no-match; existence is checked against the Country table.
    country_iso3: str = Field(min_length=3, max_length=3)


class BriefingGenerateOut(BriefingOut):
    """POST /briefing: the generated document plus its honest provenance."""

    country_iso3: str
    prose: str
    used_llm: bool
    warning: str | None = None


class HealthOut(BaseModel):
    status: str
    data_mode: str


def validate_evidence_label(label: str) -> bool:
    """Contract guard: only the five locked S01 labels are valid."""
    return label in EVIDENCE_LABELS


def validate_quality_grade(grade: str) -> bool:
    return grade in _QUALITY_GRADES
