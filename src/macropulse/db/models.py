"""ORM models for the MacroPulse database contract (unit S03).

Core entities per docs/Architecture.md section 3: countries, indicators,
source_catalog, release_calendar, raw_observations, normalized_observations,
derived_metrics, metric_versions, data_quality_flags, briefing_runs,
briefing_claims.

Vocabularies are imported from the locked S01 scope (macropulse.scope) and
the S02 catalog (macropulse.catalog) so the schema cannot drift from them.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from macropulse.catalog import (
    FREQUENCIES,
    SEASONAL_ADJUSTMENTS,
    SOURCE_SYSTEMS,
    VERIFICATION_STATUSES,
)
from macropulse.scope import EVIDENCE_LABELS

EVIDENCE_LABEL_ENUM = Enum(
    *sorted(EVIDENCE_LABELS), name="evidence_label", native_enum=True
)


class Base(DeclarativeBase):
    pass


class Country(Base):
    __tablename__ = "countries"

    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


class Indicator(Base):
    __tablename__ = "indicators"

    indicator_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    frequency: Mapped[str] = mapped_column(
        Enum(*FREQUENCIES, name="frequency"), nullable=False
    )
    seasonal_adjustment: Mapped[str] = mapped_column(
        Enum(*SEASONAL_ADJUSTMENTS, name="seasonal_adjustment"), nullable=False
    )
    fallback_status: Mapped[str] = mapped_column(String(32), nullable=False)
    comparability_notes: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)


class SourceCatalogEntry(Base):
    __tablename__ = "source_catalog"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    system: Mapped[str] = mapped_column(
        Enum(*SOURCE_SYSTEMS, name="source_system"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # primary | fallback
    verified: Mapped[str] = mapped_column(
        Enum(*VERIFICATION_STATUSES, name="verification_status"), nullable=False
    )
    coverage: Mapped[str] = mapped_column(Text, nullable=False)
    indicator_id: Mapped[str] = mapped_column(
        ForeignKey("indicators.indicator_id"), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("system", "code", "role", name="uq_source_system_code_role"),
    )


class ReleaseCalendarEntry(Base):
    __tablename__ = "release_calendar"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_system: Mapped[str] = mapped_column(
        Enum(*SOURCE_SYSTEMS, name="source_system"), nullable=False
    )
    country_iso3: Mapped[str] = mapped_column(
        ForeignKey("countries.iso3"), nullable=False
    )
    indicator_id: Mapped[str] = mapped_column(
        ForeignKey("indicators.indicator_id"), nullable=False
    )
    reference_period: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_release: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_release: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    __table_args__ = (
        UniqueConstraint(
            "source_system", "country_iso3", "indicator_id", "reference_period",
            name="uq_release_unique",
        ),
    )


class RawObservation(Base):
    """As-retrieved payload; never mutated, never shown as normalized data."""

    __tablename__ = "raw_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("source_catalog.id"), nullable=False
    )
    country_iso3: Mapped[str] = mapped_column(
        ForeignKey("countries.iso3"), nullable=False
    )
    indicator_id: Mapped[str] = mapped_column(
        ForeignKey("indicators.indicator_id"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric, nullable=True)  # NULL = missing
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)  # raw provider response

    source = relationship("SourceCatalogEntry")


class NormalizedObservation(Base):
    """Governed observation. Must carry every provenance field from the S01
    scope (see tests/test_db_models.py::test_normalized_provenance_fields)."""

    __tablename__ = "normalized_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    indicator_id: Mapped[str] = mapped_column(
        ForeignKey("indicators.indicator_id"), nullable=False
    )
    country_iso3: Mapped[str] = mapped_column(
        ForeignKey("countries.iso3"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric, nullable=True)  # NULL = missing, never imputed silently
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    frequency: Mapped[str] = mapped_column(
        Enum(*FREQUENCIES, name="frequency"), nullable=False
    )
    seasonal_adjustment: Mapped[str] = mapped_column(
        Enum(*SEASONAL_ADJUSTMENTS, name="seasonal_adjustment"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("source_catalog.id"), nullable=False
    )
    release_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieval_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vintage: Mapped[date] = mapped_column(Date, nullable=False)
    evidence_label: Mapped[str] = mapped_column(EVIDENCE_LABEL_ENUM, nullable=False)
    quality_grade: Mapped[str] = mapped_column(String(32), nullable=False, default="ungraded")
    missing_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            "indicator_id", "country_iso3", "period", "vintage", "source_id",
            name="uq_observation_identity",
        ),
        CheckConstraint(
            "value IS NOT NULL OR missing_reason IS NOT NULL",
            name="ck_missing_requires_reason",
        ),
    )


class DerivedMetric(Base):
    __tablename__ = "derived_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    country_iso3: Mapped[str] = mapped_column(
        ForeignKey("countries.iso3"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    formula_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False)  # input observation ids
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    __table_args__ = (
        UniqueConstraint("metric_key", "country_iso3", "period", name="uq_metric_identity"),
    )

    versions = relationship("MetricVersion", back_populates="metric", cascade="all, delete-orphan")


class MetricVersion(Base):
    __tablename__ = "metric_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric_id: Mapped[int] = mapped_column(
        ForeignKey("derived_metrics.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(String(32), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    __table_args__ = (
        UniqueConstraint("metric_id", "version", name="uq_metric_version"),
    )

    metric = relationship("DerivedMetric", back_populates="versions")


class DataQualityFlag(Base):
    __tablename__ = "data_quality_flags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    normalized_observation_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_observations.id"), nullable=False
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BriefingRun(Base):
    __tablename__ = "briefing_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    claims = relationship("BriefingClaim", back_populates="run", cascade="all, delete-orphan")


class BriefingClaim(Base):
    __tablename__ = "briefing_claims"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    briefing_run_id: Mapped[int] = mapped_column(
        ForeignKey("briefing_runs.id"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False)  # observation/metric ids
    validated: Mapped[bool] = mapped_column(nullable=False, default=False)

    run = relationship("BriefingRun", back_populates="claims")
