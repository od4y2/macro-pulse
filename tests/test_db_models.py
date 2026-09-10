"""Unit tests for the database contract (unit S03).

These tests validate the ORM contract without requiring a live database:
table presence, provenance fields, vocabularies, and constraint wiring.
"""

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint

from macropulse.db.models import Base, NormalizedObservation
from macropulse.scope import EVIDENCE_LABELS, PROVENANCE_FIELDS

# --- Normal cases -----------------------------------------------------------


def test_all_core_entities_present() -> None:
    expected = {
        "countries",
        "indicators",
        "source_catalog",
        "release_calendar",
        "raw_observations",
        "normalized_observations",
        "derived_metrics",
        "metric_versions",
        "data_quality_flags",
        "briefing_runs",
        "briefing_claims",
        # 12th table, added by S17 (scheduled refresh run audit);
        # migration c9af6b543047, docs/DatabaseContract.md updated with it.
        "refresh_runs",
    }
    assert set(Base.metadata.tables) == expected


def test_normalized_provenance_fields() -> None:
    column_names = {c.name for c in NormalizedObservation.__table__.columns}
    # the scope's "source" provenance field is stored as the source_id FK
    field_to_column = {"source": "source_id"}
    for field in PROVENANCE_FIELDS:
        column = field_to_column.get(field, field)
        assert column in column_names, f"missing provenance field: {field}"


def test_evidence_label_enum_matches_scope() -> None:
    enum_col = NormalizedObservation.__table__.columns["evidence_label"]
    values = set(enum_col.type.enums)
    assert values == set(EVIDENCE_LABELS)


def test_observation_identity_unique() -> None:
    constraint_names = {
        c.name
        for c in NormalizedObservation.__table__.constraints
        if isinstance(c, UniqueConstraint)
    }
    assert "uq_observation_identity" in constraint_names


# --- Boundary cases ----------------------------------------------------------


def test_missing_value_requires_reason_constraint() -> None:
    checks = [
        c
        for c in NormalizedObservation.__table__.constraints
        if isinstance(c, CheckConstraint)
    ]
    assert any("missing_requires_reason" in (c.name or "") for c in checks)


def test_raw_observations_keep_full_payload() -> None:
    from macropulse.db.models import RawObservation

    cols = {c.name for c in RawObservation.__table__.columns}
    assert {"source_id", "period", "value", "retrieved_at", "payload"} <= cols


# --- Missing cases -----------------------------------------------------------


def test_no_table_without_primary_key() -> None:
    for table in Base.metadata.tables.values():
        assert table.primary_key.columns, f"{table.name} lacks a primary key"


def test_vintage_field_not_dropped() -> None:
    cols = {c.name for c in NormalizedObservation.__table__.columns}
    assert "vintage" in cols  # RQ4 depends on vintage being a first-class column


# --- Invalid cases -----------------------------------------------------------


def test_bad_evidence_label_rejected_by_enum() -> None:
    enum_col = NormalizedObservation.__table__.columns["evidence_label"]
    assert "guessed" not in enum_col.type.enums
    assert "" not in enum_col.type.enums


@pytest.mark.parametrize("bad", ["real", "synthetic", "cached", "not-a-label"])
def test_api_contract_label_guard(bad: str) -> None:
    from macropulse.api.schemas import validate_evidence_label

    if bad in EVIDENCE_LABELS:
        assert validate_evidence_label(bad) is True
    else:
        assert validate_evidence_label(bad) is False
