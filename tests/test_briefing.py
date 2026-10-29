"""S16 briefing tests: validated facts JSON, claim adjudication with
rejection reasons, banned-phrase prose checks, and run persistence.

All inputs are synthetic fixtures (test payloads, never observations).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from macropulse.briefing import (
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROMPT_VERSION,
    ROUNDING_NOTE,
    BriefingFacts,
    adjudicate,
    adjudicate_all,
    availability_summary_lines,
    build_claims,
    check_frame_conflict,
    check_numeric_fidelity,
    check_prose,
    display_value,
    key_figures_table,
    numeric_tokens,
    record_briefing_run,
    render_briefing,
    render_rejection_report,
    title_line,
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
    # No entries -> no Key figures table header, no rounding note.
    assert "| Indicator |" not in doc
    assert ROUNDING_NOTE not in doc


def test_render_section_order_and_no_rst_rules() -> None:
    facts = BriefingFacts.from_observations(
        [obs(period="2024-01-01", value=2.8), obs()]
    )
    doc = render_briefing(facts, adjudicate_all(build_claims(facts), facts), "BRA")
    assert doc.startswith("# MacroPulse briefing — Brazil (BRA)")
    for earlier, later in (
        ("## Headlines", "## Key figures"),
        ("## Key figures", "## Statements"),
        ("## Statements", "## Availability"),
        ("## Availability", "## Limitations"),
    ):
        assert doc.index(earlier) < doc.index(later)
    # The rounding note sits under the Key figures table, above Statements.
    assert doc.index("## Key figures") < doc.index(ROUNDING_NOTE)
    assert doc.index(ROUNDING_NOTE) < doc.index("## Statements")
    # Markdown only - no reST-style section rules.
    assert "=====" not in doc
    assert "----------" not in doc


def test_render_full_precision_only_in_statements() -> None:
    facts = BriefingFacts.from_observations(
        [
            obs(period="2024-01-01", value=2.8123456),
            obs(value=2.9123456),
        ]
    )
    doc = render_briefing(facts, adjudicate_all(build_claims(facts), facts))
    head, statements = doc.split("## Statements")
    # The frame rounds; Statements carry the served precision verbatim.
    assert "2.9123456" not in head
    assert "**2.91**" in head
    assert "up from **2.81**" in head
    assert "2.9123456" in statements
    assert "2.8123456" in statements


def test_key_figures_row_shape() -> None:
    facts = BriefingFacts.from_observations(
        [obs(period="2024-01-01", value=2.8), obs()]
    )
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    table = "\n".join(key_figures_table(facts, validated))
    assert "| Indicator | Latest period | Value | Change | Source |" in table
    assert "| gdp_real_growth | 2025-01-01 | **2.9** percent_per_year " in table
    assert "up from **2.8** (2024-01-01)" in table
    assert "world_bank NY.GDP.MKTP.KD.ZG" in table


def test_key_figures_level_only_names_the_absent_comparison() -> None:
    facts = BriefingFacts.from_observations([obs()])
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    table = "\n".join(key_figures_table(facts, validated))
    assert "no consecutive prior period" in table
    assert "up from" not in table


def test_key_figures_multi_country_gains_economy_column() -> None:
    facts = BriefingFacts.from_observations(
        [obs(), obs(country_iso3="ZAF", value=0.7)]
    )
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    table = "\n".join(key_figures_table(facts, validated))
    assert "| Economy | Indicator |" in table
    assert "| BRA | gdp_real_growth |" in table
    assert "| ZAF | gdp_real_growth |" in table


def test_key_figures_escapes_pipes_in_indicator_names() -> None:
    facts = BriefingFacts.from_observations(
        [obs()], indicator_names={"gdp_real_growth": "GDP | growth"}
    )
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    table = "\n".join(key_figures_table(facts, validated))
    assert "GDP \\| growth [gdp_real_growth]" in table


def test_headlines_capped_at_four_bullets() -> None:
    facts = BriefingFacts.from_observations(
        [obs(indicator_id=f"ind_{i}", value=float(i)) for i in range(6)]
    )
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    doc = render_briefing(facts, adjudicate_all(build_claims(facts), facts))
    headlines = doc.split("## Headlines")[1].split("## Key figures")[0]
    assert len([ln for ln in headlines.splitlines() if ln.startswith("- **")]) == 4
    # The table below stays exhaustive.
    table = "\n".join(key_figures_table(facts, validated))
    assert len([ln for ln in table.splitlines() if ln.startswith("| ind_")]) == 6


def test_availability_compacted_to_per_indicator_counts() -> None:
    facts = BriefingFacts.from_observations(
        [
            obs(),
            obs(period="2024-01-01", value=None, missing_reason="series_gap"),
            obs(period="2023-01-01", value=None, missing_reason="series_gap"),
            obs(
                indicator_id="cpi_inflation_pct",
                period="2024-01-01",
                value=None,
                missing_reason="not_observed_at_period",
            ),
        ]
    )
    adjudicated = adjudicate_all(build_claims(facts), facts)
    validated = [c for c, a in adjudicated if a.validated]
    summary = availability_summary_lines(facts, validated)
    # 3 missing over 2 indicators -> 2 count bullets + the audit pointer.
    assert len(summary) == 3
    assert any(
        "gdp_real_growth: 2 observation(s) recorded missing "
        "(reasons: series_gap)." in line
        for line in summary
    )
    assert any(
        "cpi_inflation_pct: 1 observation(s) recorded missing "
        "(reasons: not_observed_at_period)." in line
        for line in summary
    )
    assert any("audit trail" in line for line in summary)
    doc = render_briefing(facts, adjudicated)
    # The per-observation wall is gone from the document...
    assert "No observation recorded for" not in doc
    # ...but missingness is still summarized honestly, with a pointer
    # from the Headlines block.
    assert "Recorded missing: 3 observation(s) across 2 indicator(s)" in doc
    # The scope line interpolates every count (regression: a dropped
    # f-prefix once rendered the placeholder literally).
    assert "3 recorded missing." in doc
    assert "{len(" not in doc


def test_title_line_names_countries_and_falls_back_to_the_iso3() -> None:
    empty = BriefingFacts.from_observations([])
    assert title_line(empty) == "# MacroPulse briefing"
    facts = BriefingFacts.from_observations([obs(country_iso3="XYZ")])
    # An iso3 off the panel renders as itself - never a fabricated name.
    assert title_line(facts) == "# MacroPulse briefing — XYZ"
    # An explicit iso3 wins and resolves through the panel names.
    assert title_line(facts, "DEU") == "# MacroPulse briefing — Germany (DEU)"
    multi = BriefingFacts.from_observations(
        [obs(country_iso3="BRA"), obs(country_iso3="ZAF")]
    )
    assert title_line(multi) == "# MacroPulse briefing — Brazil, South Africa"


# --- display rounding (frame presentation, never a restatement of the record) ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2.9, "2.9"),
        (2.0, "2"),
        (100.0, "100"),
        (-1.5, "-1.5"),
        (98.30, "98.3"),
        (2.123456789, "2.12"),
        (2.125, "2.13"),  # ROUND_HALF_UP, not banker's rounding ("2.12")
        (2.675, "2.68"),  # the binary-float trap round() gets wrong
        (0.004, "<0.01"),  # nonzero never flattens to a fabricated zero
        (-0.004, ">-0.01"),
        (0.0, "0"),
    ],
)
def test_display_value(value: float, expected: str) -> None:
    assert display_value(value) == expected


def test_display_value_survives_extremes() -> None:
    # Huge floats quantize without sci-notation and without crashing
    # (Decimal over repr keeps 1e30 exact as 10**30, not int(1e30)).
    assert display_value(1e30) == "1" + "0" * 30
    assert display_value(float("inf")) == "inf"  # repr, not a quantize crash


# --- frame-conflict guard (llm-v3 draft structure) --------------------------------


def test_check_frame_conflict_accepts_the_v3_shape() -> None:
    assert check_frame_conflict("## Overview\nText.\n\n## Statements\n- More.") == []
    # Heading comparison is case-insensitive.
    assert check_frame_conflict("## overview\nT\n\n## STATEMENTS\n- M") == []
    # Inline mentions of frame words are prose, not headings.
    draft = (
        "## Overview\nThe key figures and limitations below are scope.\n\n"
        "## Statements\n- Headlines are machine-composed."
    )
    assert check_frame_conflict(draft) == []


def test_check_frame_conflict_reports_missing_and_forbidden() -> None:
    assert check_frame_conflict("## Statements\n- x") == [
        "missing_heading: Overview"
    ]
    issues = check_frame_conflict(
        "## Overview\nT\n\n## Statements\n- x\n\n## Limitations\n- none"
    )
    assert "frame_heading: limitations" in issues
    assert check_frame_conflict("Plain prose, no headings at all.") == [
        "missing_heading: Overview",
        "missing_heading: Statements",
    ]


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


def test_record_briefing_run_records_fallback_status(session) -> None:
    from macropulse.db.models import BriefingRun

    run_id = record_briefing_run(
        session,
        model=DETERMINISTIC_MODEL,
        prompt_version=DETERMINISTIC_PROMPT_VERSION,
        adjudicated=[],
        status="fallback",
    )
    run = session.get(BriefingRun, run_id)
    assert run is not None
    assert run.status == "fallback"


def test_record_briefing_run_rejects_unknown_status(session) -> None:
    with pytest.raises(ValueError, match="outside"):
        record_briefing_run(
            session,
            model=DETERMINISTIC_MODEL,
            prompt_version=DETERMINISTIC_PROMPT_VERSION,
            adjudicated=[],
            status="partially-fine",
        )


# --- numeric fidelity guard --------------------------------------------------------


def _validated_3y() -> list:
    facts = facts_3y()
    adjudicated = adjudicate_all(build_claims(facts), facts)
    return [c for c, a in adjudicated if a.validated]


def test_numeric_tokens_parses_values_and_dates() -> None:
    tokens = numeric_tokens("2.9 percent_per_year in 2025-01-01 (1,234.5 units)")
    assert tokens == {Decimal("2.9"), Decimal(2025), Decimal(1), Decimal("1234.5")}


def test_check_numeric_fidelity_passes_claim_numbers() -> None:
    # Exact values, ISO dates, and decimal-equivalent restatements all
    # pass ("2.90" == the claim's 2.9). Only numbers the validated
    # claims carry are admissible - 2023 appears in the facts but in no
    # validated claim, so it stays out of admissible prose.
    prose = (
        "Real GDP growth for BRA stood at 2.90 percent_per_year in "
        "2025-01-01, up from 2.8 in 2024-01-01."
    )
    assert check_numeric_fidelity(prose, _validated_3y()) == []
    assert check_numeric_fidelity("Also noted for 2023.", _validated_3y()) == [
        "2023"
    ]


def test_check_numeric_fidelity_flags_fabricated_number() -> None:
    prose = "Real GDP growth for BRA stood at 2.9, with inflation at 3.5 percent."
    violations = check_numeric_fidelity(prose, _validated_3y())
    assert violations == ["3.5"]


def test_check_numeric_fidelity_comma_grouping_matches() -> None:
    facts = BriefingFacts.from_observations([obs(value=1234.5)])
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    assert check_numeric_fidelity("The level was 1,234.5 units.", validated) == []


def test_check_numeric_fidelity_no_claims_flags_every_number() -> None:
    assert check_numeric_fidelity("Growth was 7 percent.", []) == ["7"]


def test_check_numeric_fidelity_dedupes_repeated_fabrication() -> None:
    prose = "A 3.5 figure and again 3.5 and yet 9.9."
    assert check_numeric_fidelity(prose, _validated_3y()) == ["3.5", "9.9"]
