"""Structured AI briefing layer (units S16 + LLM prose source).

Prose derives only from validated JSON (``BriefingFacts``), every
statement is an atomic claim adjudicated against that JSON with a
closed rejection vocabulary, the rendered document passes a
banned-phrase check (no causal claims / advice / forecasts / merit
rankings) and - on the LLM path - a numeric-fidelity check against the
validated claims, and every attempt - passed or rejected - is persisted
to ``briefing_runs`` / ``briefing_claims`` for audit.

``generate_briefing`` is the on-demand entry point: it tries the LLM
prose source (``llm.py``, OpenAI-compatible wire format configured via
``LLM_*`` environment variables) and guarantees the deterministic
template document as a fallback, with a warning naming the reason.
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
from macropulse.briefing.generate import (
    FALLBACK_WARNINGS,
    BriefingOutcome,
    compose_document,
    generate_briefing,
)
from macropulse.briefing.llm import (
    LLM_PROMPT_VERSION,
    LLM_TIMEOUT_SECONDS,
    SUPPORTED_PROVIDERS,
    HttpLlmSource,
    LLMConfigError,
    LLMError,
    LLMResponseError,
    LLMSettings,
    LlmSource,
    LLMTransportError,
    build_prompt,
    build_system_prompt,
)
from macropulse.briefing.prose import (
    BANNED_PATTERNS,
    check_numeric_fidelity,
    check_prose,
    numeric_tokens,
    render_briefing,
    render_rejection_report,
)
from macropulse.briefing.run import (
    BRIEFING_STATUSES,
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROMPT_VERSION,
    record_briefing_run,
)

__all__ = [
    "BANNED_PATTERNS",
    "BRIEFING_STATUSES",
    "CLAIM_KINDS",
    "DETERMINISTIC_MODEL",
    "DETERMINISTIC_PROMPT_VERSION",
    "FALLBACK_WARNINGS",
    "LLM_PROMPT_VERSION",
    "LLM_TIMEOUT_SECONDS",
    "REJECTION_REASONS",
    "SUPPORTED_PROVIDERS",
    "Adjudication",
    "AvailabilityClaim",
    "BriefingFact",
    "BriefingFacts",
    "BriefingOutcome",
    "ChangeClaim",
    "Claim",
    "ExcludedObservation",
    "FactRef",
    "HttpLlmSource",
    "LLMConfigError",
    "LLMError",
    "LLMResponseError",
    "LLMSettings",
    "LLMTransportError",
    "LevelClaim",
    "LlmSource",
    "MissingObservation",
    "adjudicate",
    "adjudicate_all",
    "build_claims",
    "build_prompt",
    "build_system_prompt",
    "check_numeric_fidelity",
    "check_prose",
    "compose_document",
    "generate_briefing",
    "numeric_tokens",
    "record_briefing_run",
    "render_briefing",
    "render_rejection_report",
]
