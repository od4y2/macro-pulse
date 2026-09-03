"""S16 briefing tests: validated facts JSON, claim adjudication with
rejection reasons, banned-phrase prose checks, and run persistence.

All inputs are synthetic fixtures (test payloads, never observations).
"""

from __future__ import annotations

import pytest

from macropulse.briefing import (
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROMPT_VERSION,
    BriefingFacts,
    adjudicate,
    adjudicate_all,
    build_claims,
    check_prose,
    record_briefing_run,
    render_briefing,
    render_rejection_report,
)
from macropulse.briefing.claims import CLAIM_KINDS, REJECTION_REASONS
from macropulse.briefing.facts import ExcludedObservation


def obs(**overrides: object) -> dict:
    """One observation record shaped like the service's ObservationOut."""
    base: dict[str, object] = {
        "indicator_id": "gdp_real_growth",
        "country_iso3": "BRA",
        "period": "2025-01-01",
        "value": 2.9,
        "unit": "percent_per_year",
        "frequency": "annual",
        "seasonal_adjustment": "varies",
        "source": {
            "system": "world_bank",
            "code": "NY.GDP.MKTP.KD.ZG",
            "role": "primary",
            "verified": "confirmed",
            "coverage": "test",
        },
        "release_time": "2026-01-25T13:30:00Z",
        "retrieval_time": "2026-01-25T14:00:00Z",
        "vintage": "2026-01-25",
        "evidence_label": "real",
        "quality_grade": "official",
        "missing_reason": None,
    }
    base.update(overrides)
    return base


# --- facts JSON contract ---------------------------------------------------------


def test_facts_partition_real_missing_excluded() -> None:
    facts = BriefingFacts.from_observations(
        [
            obs(),
            obs(period="2024-01-01", value=2.8),
            obs(
                period="2023-01-01", value=None, missing_reason="not_observed_at_period"
            ),
            obs(period="2022-01-01", value=1.0, evidence_label="mocked"),
        ]
    )
    assert len(facts.facts) == 2
    assert len(facts.missing) == 1
    assert facts.missing[0].missing_reason == "not_observed_at_period"
    assert len(facts.excluded) == 1
    assert facts.excluded[0].evidence_label == "mocked"


def test_facts_non_real_value_is_never_a_fact() -> None:
    # A mocked observation with a value is excluded, not stated as observed.
    facts = BriefingFacts.from_observations(
        [obs(evidence_label="synthetic", value=5.0)]
    )
    assert facts.facts == []
    assert len(facts.excluded) == 1


def test_facts_reject_duplicate_periods() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        BriefingFacts.from_observations(
            [obs(), obs(vintage="2026-02-01")]  # same period, two vintages
        )


def test_facts_reject_unknown_evidence_label() -> None:
    with pytest.raises(ValueError, match="outside the locked vocabulary"):
        BriefingFacts.from_observations([obs(evidence_label="probably-real")])


def test_facts_reject_non_iso_period() -> None:
    with pytest.raises(ValueError, match="not an ISO date"):
        BriefingFacts.from_observations([obs(period="2025-Q1")])


def test_indicator_label_falls_back_to_id() -> None:
    facts = BriefingFacts.from_observations(
        [obs()], {"gdp_real_growth": "Real GDP growth"}
    )
    assert facts.indicator_label("gdp_real_growth") == "Real GDP growth"
    assert facts.indicator_label("other") == "other"


# --- claim building ---------------------------------------------------------------


def test_build_claims_level_at_latest_period() -> None:
    facts = BriefingFacts.from_observations(
        [
            obs(period="2023-01-01", value=1.0),
            obs(period="2024-01-01", value=2.8),
            obs(),
        ]
    )
    claims = build_claims(facts)
    levels = [c for c in claims if c.kind == "level"]
    assert len(levels) == 1
    assert levels[0].period == "2025-01-01"
    assert levels[0].value == 2.9


def test_build_claims_change_for_consecutive_periods() -> None:
    facts = BriefingFacts.from_observations(
        [obs(period="2024-01-01", value=2.8), obs()]
    )
    claims = build_claims(facts)
    changes = [c for c in claims if c.kind == "change"]
    assert len(changes) == 1
    assert changes[0].prior_period == "2024-01-01"
    assert changes[0].prior_value == 2.8
    assert "up from 2.8" in changes[0].text


def test_build_claims_no_change_across_gap() -> None:
    # 2023 -> 2025 with 2024 absent: the periods are not one step apart,
    # so no change claim is built (a "rose from" across a gap would
    # mislead about timing).
    facts = BriefingFacts.from_observations(
        [obs(period="2023-01-01", value=1.0), obs()]
    )
    assert [c for c in build_claims(facts) if c.kind == "change"] == []


def test_build_claims_change_directions() -> None:
    facts = BriefingFacts.from_observations(
        [obs(period="2024-01-01", value=3.0), obs(value=2.5)]
    )
    change = next(c for c in build_claims(facts) if c.kind == "change")
    assert "down from 3.0" in change.text

    facts = BriefingFacts.from_observations(
        [obs(period="2024-01-01", value=2.9), obs()]
    )
    change = next(c for c in build_claims(facts) if c.kind == "change")
    assert "unchanged from 2.9" in change.text


def test_build_claims_availability_for_missing() -> None:
    facts = BriefingFacts.from_observations(
        [obs(), obs(period="2024-01-01", value=None, missing_reason="series_gap")]
    )
    availability = [c for c in build_claims(facts) if c.kind == "availability"]
    assert len(availability) == 1
    assert "missing (series_gap)" in availability[0].text


def test_build_claims_quarterly_step_is_three_months() -> None:
    facts = BriefingFacts.from_observations(
        [
            obs(period="2026-01-01", value=1.0, frequency="quarterly"),
            obs(period="2026-04-01", value=1.5, frequency="quarterly"),
        ]
    )
    changes = [c for c in build_claims(facts) if c.kind == "change"]
    assert len(changes) == 1  # Jan -> Apr is exactly one quarterly step


def test_build_claims_unknown_frequency_rejected() -> None:
    facts = BriefingFacts.from_observations(
        [
            obs(period="2024-01-01", value=2.8, frequency="weekly"),
            obs(frequency="weekly"),
        ]
    )
    with pytest.raises(ValueError, match="unknown frequency"):
        build_claims(facts)


def test_claim_kinds_and_reasons_are_closed_vocabularies() -> None:
    assert CLAIM_KINDS == ("level", "change", "availability")
    assert set(REJECTION_REASONS) == {
        "fact_not_found",
        "value_mismatch",
        "evidence_not_real",
        "missing_value_claimed",
        "citation_missing",
        "citation_mismatch",
        "availability_contradicted",
        "reason_mismatch",
    }


# --- adjudication (the rejection tests) --------------------------------------------


def facts_3y() -> BriefingFacts:
    return BriefingFacts.from_observations(
        [
            obs(period="2023-01-01", value=1.0),
            obs(period="2024-01-01", value=2.8),
            obs(),
        ]
    )


def test_adjudicate_valid_claims() -> None:
    facts = facts_3y()
    for claim in build_claims(facts):
        verdict = adjudicate(claim, facts)
        assert verdict.validated
        assert verdict.reason is None


def test_adjudicate_value_mismatch() -> None:
    facts = facts_3y()
    level = next(c for c in build_claims(facts) if c.kind == "level")
    tampered = level.model_copy(update={"value": level.value + 0.5})
    assert adjudicate(tampered, facts).reason == "value_mismatch"


def test_adjudicate_fact_not_found() -> None:
    facts = facts_3y()
    level = next(c for c in build_claims(facts) if c.kind == "level")
    tampered = level.model_copy(update={"period": "2030-01-01"})
    assert adjudicate(tampered, facts).reason == "fact_not_found"


def test_adjudicate_evidence_not_real() -> None:
    facts = BriefingFacts.from_observations([obs(evidence_label="mocked")])
    claims = BriefingFacts.from_observations([obs()])
    level = next(c for c in build_claims(claims) if c.kind == "level")
    # claim referencing an observation the facts hold only as excluded
    assert adjudicate(level, facts).reason == "evidence_not_real"


def test_adjudicate_missing_value_claimed() -> None:
    facts = BriefingFacts.from_observations(
        [obs(period="2024-01-01", value=None, missing_reason="series_gap")]
    )
    populated = BriefingFacts.from_observations([obs(period="2024-01-01")])
    level = next(c for c in build_claims(populated) if c.kind == "level")
    assert adjudicate(level, facts).reason == "missing_value_claimed"


def test_adjudicate_citation_missing() -> None:
    facts = facts_3y()
    level = next(c for c in build_claims(facts) if c.kind == "level")
    uncited = level.model_copy(update={"refs": []})
    assert adjudicate(uncited, facts).reason == "citation_missing"


def test_adjudicate_citation_mismatch() -> None:
    facts = facts_3y()
    level = next(c for c in build_claims(facts) if c.kind == "level")
    wrong_source = level.model_copy(
        update={
            "refs": [level.refs[0].model_copy(update={"source_code": "WRONG.CODE"})]
        }
    )
    assert adjudicate(wrong_source, facts).reason == "citation_mismatch"


def test_adjudicate_availability_contradicted() -> None:
    # Claiming an observation is missing when the facts hold its value.
    facts = facts_3y()
    availability = build_claims(
        BriefingFacts.from_observations(
            [obs(period="2025-01-01", value=None, missing_reason="series_gap")]
        )
    )[0]
    assert adjudicate(availability, facts).reason == "availability_contradicted"


def test_adjudicate_reason_mismatch() -> None:
    facts = BriefingFacts.from_observations(
        [obs(period="2024-01-01", value=None, missing_reason="series_gap")]
    )
    availability = build_claims(facts)[0]
    wrong_reason = availability.model_copy(update={"missing_reason": "other_reason"})
    assert adjudicate(wrong_reason, facts).reason == "reason_mismatch"


def test_adjudicate_all_preserves_pairs() -> None:
    facts = facts_3y()
    adjudicated = adjudicate_all(build_claims(facts), facts)
    assert len(adjudicated) == len(build_claims(facts))
    assert all(a.validated for _, a in adjudicated)


# --- prose ------------------------------------------------------------------------


def test_rendered_briefing_passes_banned_phrase_check() -> None:
    # The template output itself must survive the rejection layer.
    facts = BriefingFacts.from_observations(
        [
            obs(period="2024-01-01", value=2.8),
            obs(),
            obs(country_iso3="ZAF", period="2024-01-01", value=0.7),
            obs(country_iso3="ZAF"),
            obs(
                country_iso3="USA",
                period="2023-01-01",
                value=None,
                missing_reason="not_observed_at_period",
            ),
        ]
    )
    adjudicated = adjudicate_all(build_claims(facts), facts)
    assert check_prose(render_briefing(facts, adjudicated)) == []


def test_check_prose_rejects_each_banned_class() -> None:
    samples = {
        "causal_phrase": "Growth rose because reforms passed.",
        "advice_phrase": "Investors should invest in bonds now.",
        "forecast_phrase": "GDP will fall next year.",
        "merit_ranking_phrase": "Germany has the best economy.",
    }
    for reason, sentence in samples.items():
        assert check_prose(sentence) == [reason]


def test_check_prose_passes_plain_factual_text() -> None:
    assert check_prose("Real GDP growth was 2.9 in 2025, up from 2.8 in 2024.") == []


def test_render_includes_citations_and_full_precision() -> None:
    facts = BriefingFacts.from_observations([obs(value=2.123456789)])
    doc = render_briefing(facts, adjudicate_all(build_claims(facts), facts))
    assert "world_bank NY.GDP.MKTP.KD.ZG" in doc
    assert "vintage: 2026-01-25" in doc
    assert "evidence: real" in doc
    assert "quality: official" in doc
    assert "2.123456789" in doc  # full precision, no rounding


def test_render_excludes_rejected_claims_from_statements() -> None:
    facts = facts_3y()
    claims = build_claims(facts)
    level = next(c for c in claims if c.kind == "level")
    tampered = level.model_copy(update={"value": level.value + 0.5})
    adjudicated = adjudicate_all(
        [c for c in claims if c is not level] + [tampered], facts
    )
    doc = render_briefing(facts, adjudicated)
    assert "1 candidate claim(s) rejected" in doc
    assert level.text not in doc  # rejected claim text never renders as a statement
    report = render_rejection_report(adjudicated)
    assert "REJECTED (value_mismatch)" in report


def test_render_names_excluded_observations() -> None:
    facts = BriefingFacts.from_observations(
        [obs(), obs(period="2024-01-01", value=1.0, evidence_label="mocked")]
    )
    doc = render_briefing(facts, adjudicate_all(build_claims(facts), facts))
    assert "1 observation(s) excluded" in doc
    assert "mocked" in doc
    assert "not stated as observed" in doc


def test_render_empty_facts() -> None:
    facts = BriefingFacts.from_observations([])
    doc = render_briefing(facts, [])
    assert "0 economies, 0 indicator(s)" in doc
    assert "No validated value statements." in doc
    assert "No missing observations in the served set." in doc


def test_excluded_observation_shape() -> None:
    # The excluded record carries its identity so refs to it resolve
    # (and get the truthful evidence_not_real verdict, not a citation error).
    facts = BriefingFacts.from_observations([obs(evidence_label="mocked")])
    excluded: ExcludedObservation = facts.excluded[0]
    assert excluded.vintage == "2026-01-25"
    assert excluded.source_system == "world_bank"


# --- persistence -----------------------------------------------------------------


def test_record_briefing_run_persists_claims_and_flags(session) -> None:
    from macropulse.db.models import BriefingClaim, BriefingRun

    facts = facts_3y()
    claims = build_claims(facts)
    level = next(c for c in claims if c.kind == "level")
    tampered = level.model_copy(update={"value": level.value + 0.5})
    adjudicated = adjudicate_all(
        [c for c in claims if c is not level] + [tampered], facts
    )

    run_id = record_briefing_run(
        session,
        model=DETERMINISTIC_MODEL,
        prompt_version=DETERMINISTIC_PROMPT_VERSION,
        adjudicated=adjudicated,
    )

    run = session.get(BriefingRun, run_id)
    assert run is not None
    assert run.model == "deterministic-template"
    assert run.prompt_version == "s16-v1"
    assert run.status == "completed"

    rows = (
        session.query(BriefingClaim)
        .filter(BriefingClaim.briefing_run_id == run_id)
        .all()
    )
    assert len(rows) == len(adjudicated)
    assert {r.validated for r in rows} == {True, False}
    rejected = next(r for r in rows if not r.validated)
    assert "REJECTED" not in rejected.claim_text  # text stored as generated
    assert rejected.evidence_refs  # every claim row carries its citation JSON
    assert set(rejected.evidence_refs[0]) == {
        "indicator_id",
        "country_iso3",
        "period",
        "vintage",
        "source_system",
        "source_code",
    }


def test_record_briefing_run_empty_claims(session) -> None:
    from macropulse.db.models import BriefingClaim

    run_id = record_briefing_run(
        session, model="deterministic-template", prompt_version="s16-v1", adjudicated=[]
    )
    assert (
        session.query(BriefingClaim)
        .filter(BriefingClaim.briefing_run_id == run_id)
        .count()
        == 0
    )


def test_record_briefing_run_rejects_overlong_identity(session) -> None:
    with pytest.raises(ValueError, match="128-char"):
        record_briefing_run(
            session, model="x" * 129, prompt_version="s16-v1", adjudicated=[]
        )
    with pytest.raises(ValueError, match="32-char"):
        record_briefing_run(
            session, model="ok", prompt_version="x" * 33, adjudicated=[]
        )
