"""Structured AI briefing layer (unit S16).

Prose derives only from validated JSON (``BriefingFacts``), every
statement is an atomic claim adjudicated against that JSON with a
closed rejection vocabulary, the rendered document passes a
banned-phrase check (no causal claims / advice / forecasts / merit
rankings), and every attempt - passed or rejected - is persisted to
``briefing_runs`` / ``briefing_claims`` for audit.
"""

from macropulse.briefing.claims import (
    CLAIM_KINDS,
    REJECTION_REASONS,
    Adjudication,
    AvailabilityClaim,
    ChangeClaim,
    Claim,
    FactRef,
    LevelClaim,
    adjudicate,
    adjudicate_all,
    build_claims,
)
from macropulse.briefing.facts import (
    BriefingFact,
    BriefingFacts,
    ExcludedObservation,
    MissingObservation,
)
from macropulse.briefing.prose import (
    BANNED_PATTERNS,
    check_prose,
    render_briefing,
    render_rejection_report,
)
from macropulse.briefing.run import (
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROMPT_VERSION,
    record_briefing_run,
)

__all__ = [
    "BANNED_PATTERNS",
    "CLAIM_KINDS",
    "DETERMINISTIC_MODEL",
    "DETERMINISTIC_PROMPT_VERSION",
    "REJECTION_REASONS",
    "Adjudication",
    "AvailabilityClaim",
    "BriefingFact",
    "BriefingFacts",
    "ChangeClaim",
    "Claim",
    "ExcludedObservation",
    "FactRef",
    "LevelClaim",
    "MissingObservation",
    "adjudicate",
    "adjudicate_all",
    "build_claims",
    "check_prose",
    "record_briefing_run",
    "render_briefing",
    "render_rejection_report",
]
