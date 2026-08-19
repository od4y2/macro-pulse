"""Tests for the locked research scope (unit S01).

Covers normal, boundary, missing, and invalid cases as required by the
engineering contract.
"""

import pytest

from macropulse import scope
from macropulse.scope import Country, ResearchQuestion, validate_scope

EXPECTED_ISO3 = {"USA", "CHN", "JPN", "DEU", "GBR", "IND", "BRA", "KOR", "ZAF", "MEX"}


# --- Normal cases -----------------------------------------------------------

def test_scope_validates_cleanly() -> None:
    assert validate_scope() == []


def test_country_panel_matches_locked_set() -> None:
    assert {c.iso3 for c in scope.COUNTRIES} == EXPECTED_ISO3


def test_research_questions_locked() -> None:
    assert [q.rq_id for q in scope.RESEARCH_QUESTIONS] == ["RQ1", "RQ2", "RQ3", "RQ4"]
    assert {q.unit for q in scope.RESEARCH_QUESTIONS} == {"S10", "S11", "S12", "S07"}


def test_evidence_labels_match_governance() -> None:
    assert scope.EVIDENCE_LABELS == {"real", "synthetic", "mocked", "cached", "external"}


def test_non_claims_boundary_present() -> None:
    joined = " ".join(scope.NON_CLAIMS).lower()
    assert "investment advice" in joined
    assert "causal" in joined


# --- Boundary cases ----------------------------------------------------------

def test_country_panel_size_is_exactly_ten() -> None:
    assert len(scope.COUNTRIES) == 10


def test_provenance_fields_match_architecture_contract() -> None:
    assert set(scope.PROVENANCE_FIELDS) == {
        "period", "release_time", "retrieval_time", "vintage", "unit",
        "frequency", "seasonal_adjustment", "source", "quality_grade",
    }


# --- Missing cases -----------------------------------------------------------

def test_empty_country_panel_rejected() -> None:
    original = scope.COUNTRIES
    try:
        scope.COUNTRIES = ()
        problems = validate_scope()
        assert any("10 economies" in p for p in problems)
    finally:
        scope.COUNTRIES = original


def test_country_missing_rationale_rejected() -> None:
    original = scope.COUNTRIES
    try:
        scope.COUNTRIES = original[:9] + (Country("MEX", "Mexico", ""),)
        assert any("missing name or rationale" in p for p in validate_scope())
    finally:
        scope.COUNTRIES = original


# --- Invalid cases -----------------------------------------------------------

def test_duplicate_iso3_rejected() -> None:
    original = scope.COUNTRIES
    try:
        scope.COUNTRIES = original[:9] + (Country("USA", "Clone", "duplicate"),)
        assert any("duplicate ISO3" in p for p in validate_scope())
    finally:
        scope.COUNTRIES = original


@pytest.mark.parametrize("bad", ["us", "USA1", "Usa", "USAX"])
def test_malformed_iso3_rejected(bad: str) -> None:
    original = scope.COUNTRIES
    try:
        scope.COUNTRIES = original[:9] + (Country(bad, "Bad", "invalid"),)
        assert any("invalid ISO3" in p for p in validate_scope())
    finally:
        scope.COUNTRIES = original


def test_question_without_question_mark_rejected() -> None:
    original = scope.RESEARCH_QUESTIONS
    try:
        scope.RESEARCH_QUESTIONS = original[:3] + (
            ResearchQuestion("RQ4", "not a question", "vintage-transparency", "S07"),
        )
        assert any("not phrased as a question" in p for p in validate_scope())
    finally:
        scope.RESEARCH_QUESTIONS = original


def test_question_referencing_unknown_module_rejected() -> None:
    original = scope.RESEARCH_QUESTIONS
    try:
        scope.RESEARCH_QUESTIONS = original[:3] + (
            ResearchQuestion("RQ4", "unknown lens?", "does-not-exist", "S07"),
        )
        assert any("unknown module" in p for p in validate_scope())
    finally:
        scope.RESEARCH_QUESTIONS = original
