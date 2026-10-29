"""Atomic claims and their adjudication for the briefing (unit S16).

Every statement a briefing makes is a ``Claim`` - a structured assertion
carrying the observation(s) it cites (``refs``). Claims are BUILT from
validated facts by deterministic templates, then ADJUDICATED against the
same facts: a claim passes only when every value it states matches the
validated JSON exactly and its citations resolve to observations in it.
Anything else is rejected with a reason from a closed vocabulary - prose
never carries an unadjudicated statement.

This is the enforcement layer for the S01 non-claim "AI-generated prose
derives only from validated structured inputs": whether text comes from
these templates or from an LLM attached later, it survives only as
claims that adjudicate clean (plus the banned-phrase check in
``prose.py``). The machine computes; the prose reports - the AI boundary
in docs/Architecture.md section 5.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from macropulse.briefing.facts import (
    BriefingFact,
    BriefingFacts,
    MissingObservation,
)
from macropulse.metrics.transforms import FREQUENCY_STEP_MONTHS

CLAIM_KINDS = ("level", "change", "availability")

# Closed vocabulary: every reason a claim can be rejected.
REJECTION_REASONS = (
    "fact_not_found",
    "value_mismatch",
    "evidence_not_real",
    "missing_value_claimed",
    "citation_missing",
    "citation_mismatch",
    "availability_contradicted",
    "reason_mismatch",
)


class FactRef(BaseModel):
    """Identity of one cited observation (the S03 observation identity)."""

    indicator_id: str
    country_iso3: str
    period: str
    vintage: str
    source_system: str
    source_code: str


class Adjudication(BaseModel):
    """The verdict on one claim; ``reason`` is set iff not validated."""

    validated: bool
    reason: str | None = None


class LevelClaim(BaseModel):
    """A value statement about one (indicator, country, period)."""

    kind: Literal["level"] = "level"
    text: str
    refs: list[FactRef]
    indicator_id: str
    country_iso3: str
    period: str
    value: float


class ChangeClaim(BaseModel):
    """A period-over-period comparison citing both endpoint facts."""

    kind: Literal["change"] = "change"
    text: str
    refs: list[FactRef]  # [prior, current]
    indicator_id: str
    country_iso3: str
    prior_period: str
    prior_value: float
    period: str
    value: float


class AvailabilityClaim(BaseModel):
    """A statement that an observation is missing (missingness named)."""

    kind: Literal["availability"] = "availability"
    text: str
    refs: list[FactRef]
    indicator_id: str
    country_iso3: str
    period: str
    missing_reason: str | None


Claim = LevelClaim | ChangeClaim | AvailabilityClaim


def _ref(fact: BriefingFact) -> FactRef:
    return FactRef(
        indicator_id=fact.indicator_id,
        country_iso3=fact.country_iso3,
        period=fact.period,
        vintage=fact.vintage,
        source_system=fact.source_system,
        source_code=fact.source_code,
    )


def _ref_from_missing(obs: MissingObservation) -> FactRef:
    return FactRef(
        indicator_id=obs.indicator_id,
        country_iso3=obs.country_iso3,
        period=obs.period,
        vintage=obs.vintage,
        source_system=obs.source_system,
        source_code=obs.source_code,
    )


def _months_between(prior: str, current: str) -> int:
    a, b = date.fromisoformat(prior), date.fromisoformat(current)
    return (b.year - a.year) * 12 + (b.month - a.month)


def consecutive_periods(prior: str, current: str, frequency: str) -> bool:
    """True when the two periods are exactly one frequency step apart.

    Change claims are only built for consecutive observed periods: a
    "rose from" sentence across a gap would mislead about timing.
    Public because the presentation layer (views.assembly
    ``briefing_highlights``) must honor the same rule - a tile delta
    across a gap would mislead exactly like a claim would.
    """
    if frequency not in FREQUENCY_STEP_MONTHS:
        raise ValueError(
            f"unknown frequency {frequency!r}; expected one of "
            f"{sorted(FREQUENCY_STEP_MONTHS)}"
        )
    a, b = date.fromisoformat(prior), date.fromisoformat(current)
    return (
        _months_between(prior, current) == FREQUENCY_STEP_MONTHS[frequency]
        and a.day == b.day
    )


def _level_text(facts: BriefingFacts, fact: BriefingFact) -> str:
    name = facts.indicator_label(fact.indicator_id)
    return (
        f"{name} [{fact.indicator_id}] for {fact.country_iso3} in "
        f"{fact.period}: {fact.value!r} {fact.unit} "
        f"(source: {fact.source_system} {fact.source_code}; "
        f"vintage: {fact.vintage}; evidence: {fact.evidence_label}; "
        f"quality: {fact.quality_grade})"
    )


def _change_text(
    facts: BriefingFacts, prior: BriefingFact, current: BriefingFact
) -> str:
    name = facts.indicator_label(current.indicator_id)
    direction = (
        "up from"
        if current.value > prior.value
        else "down from"
        if current.value < prior.value
        else "unchanged from"
    )
    return (
        f"{name} [{current.indicator_id}] for {current.country_iso3}: "
        f"{current.value!r} {current.unit} in {current.period}, "
        f"{direction} {prior.value!r} in {prior.period} "
        f"(source: {current.source_system} {current.source_code}; "
        f"vintage: {current.vintage}; evidence: {current.evidence_label}; "
        f"quality: {current.quality_grade})"
    )


def _availability_text(facts: BriefingFacts, obs: MissingObservation) -> str:
    name = facts.indicator_label(obs.indicator_id)
    reason = obs.missing_reason if obs.missing_reason else "no reason recorded"
    return (
        f"No observation recorded for {name} [{obs.indicator_id}] "
        f"({obs.country_iso3}, {obs.period}): missing ({reason})."
    )


def build_claims(facts: BriefingFacts) -> list[Claim]:
    """Deterministic claims from validated facts (latest period per series).

    One level claim per (country, indicator) at its latest observed
    period; one change claim when the two latest observed periods are
    consecutive (one frequency step apart - no comparison across gaps);
    one availability claim per recorded missing observation.
    """
    groups: dict[tuple[str, str], list[BriefingFact]] = {}
    for fact in facts.facts:
        groups.setdefault((fact.country_iso3, fact.indicator_id), []).append(fact)

    claims: list[Claim] = []
    for (country, indicator), series in sorted(groups.items()):
        series.sort(key=lambda f: f.period)
        current = series[-1]
        claims.append(
            LevelClaim(
                text=_level_text(facts, current),
                refs=[_ref(current)],
                indicator_id=indicator,
                country_iso3=country,
                period=current.period,
                value=current.value,
            )
        )
        if len(series) >= 2:
            prior = series[-2]
            if consecutive_periods(prior.period, current.period, current.frequency):
                claims.append(
                    ChangeClaim(
                        text=_change_text(facts, prior, current),
                        refs=[_ref(prior), _ref(current)],
                        indicator_id=indicator,
                        country_iso3=country,
                        prior_period=prior.period,
                        prior_value=prior.value,
                        period=current.period,
                        value=current.value,
                    )
                )
    for obs in sorted(
        facts.missing, key=lambda m: (m.country_iso3, m.indicator_id, m.period)
    ):
        claims.append(
            AvailabilityClaim(
                text=_availability_text(facts, obs),
                refs=[_ref_from_missing(obs)],
                indicator_id=obs.indicator_id,
                country_iso3=obs.country_iso3,
                period=obs.period,
                missing_reason=obs.missing_reason,
            )
        )
    return claims


class _Indexes:
    """Lookup helpers over a BriefingFacts payload."""

    def __init__(self, facts: BriefingFacts) -> None:
        self.fact_by_key = {
            (f.indicator_id, f.country_iso3, f.period): f for f in facts.facts
        }
        self.missing_by_key = {
            (m.indicator_id, m.country_iso3, m.period): m for m in facts.missing
        }
        self.excluded_by_key = {
            (e.indicator_id, e.country_iso3, e.period): e for e in facts.excluded
        }
        self.identities = (
            {
                (
                    f.indicator_id,
                    f.country_iso3,
                    f.period,
                    f.vintage,
                    f.source_system,
                    f.source_code,
                )
                for f in facts.facts
            }
            | {
                (
                    m.indicator_id,
                    m.country_iso3,
                    m.period,
                    m.vintage,
                    m.source_system,
                    m.source_code,
                )
                for m in facts.missing
            }
            | {
                (
                    e.indicator_id,
                    e.country_iso3,
                    e.period,
                    e.vintage,
                    e.source_system,
                    e.source_code,
                )
                for e in facts.excluded
            }
        )

    def ref_resolves(self, ref: FactRef) -> bool:
        return (
            ref.indicator_id,
            ref.country_iso3,
            ref.period,
            ref.vintage,
            ref.source_system,
            ref.source_code,
        ) in self.identities

    def ref_matches(self, ref: FactRef, obs: BriefingFact | MissingObservation) -> bool:
        return (
            ref.indicator_id == obs.indicator_id
            and ref.country_iso3 == obs.country_iso3
            and ref.period == obs.period
            and ref.vintage == obs.vintage
            and ref.source_system == obs.source_system
            and ref.source_code == obs.source_code
        )


def _adjudicate_level(claim: LevelClaim, indexes: _Indexes) -> Adjudication:
    key = (claim.indicator_id, claim.country_iso3, claim.period)
    fact = indexes.fact_by_key.get(key)
    if fact is None:
        if key in indexes.excluded_by_key:
            return Adjudication(validated=False, reason="evidence_not_real")
        if key in indexes.missing_by_key:
            return Adjudication(validated=False, reason="missing_value_claimed")
        return Adjudication(validated=False, reason="fact_not_found")
    if claim.value != fact.value:
        return Adjudication(validated=False, reason="value_mismatch")
    if not any(indexes.ref_matches(r, fact) for r in claim.refs):
        return Adjudication(validated=False, reason="citation_mismatch")
    return Adjudication(validated=True)


def adjudicate(claim: Claim, facts: BriefingFacts) -> Adjudication:
    """Validate one claim against the facts, with a closed reason set."""
    if not claim.refs:
        return Adjudication(validated=False, reason="citation_missing")
    indexes = _Indexes(facts)
    if not all(indexes.ref_resolves(r) for r in claim.refs):
        return Adjudication(validated=False, reason="citation_mismatch")

    if isinstance(claim, LevelClaim):
        return _adjudicate_level(claim, indexes)
    if isinstance(claim, ChangeClaim):
        current = _adjudicate_level(
            LevelClaim(
                text=claim.text,
                refs=[claim.refs[-1]],
                indicator_id=claim.indicator_id,
                country_iso3=claim.country_iso3,
                period=claim.period,
                value=claim.value,
            ),
            indexes,
        )
        if not current.validated:
            return current
        prior = _adjudicate_level(
            LevelClaim(
                text=claim.text,
                refs=[claim.refs[0]],
                indicator_id=claim.indicator_id,
                country_iso3=claim.country_iso3,
                period=claim.prior_period,
                value=claim.prior_value,
            ),
            indexes,
        )
        return prior

    # AvailabilityClaim: the period must be missing, with a matching reason.
    key = (claim.indicator_id, claim.country_iso3, claim.period)
    obs = indexes.missing_by_key.get(key)
    if obs is None:
        if key in indexes.fact_by_key:
            return Adjudication(validated=False, reason="availability_contradicted")
        if key in indexes.excluded_by_key:
            return Adjudication(validated=False, reason="evidence_not_real")
        return Adjudication(validated=False, reason="fact_not_found")
    if claim.missing_reason != obs.missing_reason:
        return Adjudication(validated=False, reason="reason_mismatch")
    if not any(indexes.ref_matches(r, obs) for r in claim.refs):
        return Adjudication(validated=False, reason="citation_mismatch")
    return Adjudication(validated=True)


def adjudicate_all(
    claims: list[Claim], facts: BriefingFacts
) -> list[tuple[Claim, Adjudication]]:
    """Adjudicate every claim; order preserved, pair per claim."""
    return [(claim, adjudicate(claim, facts)) for claim in claims]
