"""On-demand briefing generation: LLM prose with guaranteed fallback.

One call, ``generate_briefing``, runs the full S16 pipeline over one
country's latest-vintage observations and tries the LLM prose source
(``briefing/llm.py``) on top of it:

    observations -> BriefingFacts -> build_claims -> adjudicate_all
                 -> [LLM prose] -> check_prose + check_numeric_fidelity
                                   + check_frame_conflict
                 -> compose_document            (LLM path)
        or       -> render_briefing + warning   (deterministic fallback)
                 -> record_briefing_run         (audit row either way)

The fallback is total: any configuration, transport, response,
banned-phrase, fabricated-number, or frame-structure failure yields the
deterministic template document, ``model="deterministic-template"``,
``status="fallback"``, and a warning naming the reason. The LLM never
gates the product - it only ever improves the prose that survives every
rejection layer.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from macropulse.briefing.claims import Adjudication, Claim, adjudicate_all, build_claims
from macropulse.briefing.facts import BriefingFacts
from macropulse.briefing.llm import (
    HttpLlmSource,
    LLMConfigError,
    LLMError,
    LLMResponseError,
    LlmSource,
    LLMTransportError,
    build_prompt,
)
from macropulse.briefing.prose import (
    availability_summary_lines,
    check_frame_conflict,
    check_numeric_fidelity,
    check_prose,
    frame_head_lines,
    limitation_lines,
    render_briefing,
)
from macropulse.briefing.run import (
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROMPT_VERSION,
    record_briefing_run,
)

# Closed vocabulary of fallback warning reasons (docs/AIBriefing.md).
FALLBACK_WARNINGS = (
    "llm_not_configured",
    "llm_transport_error",
    "llm_response_error",
    "banned_phrase",
    "fabricated_number",
    "frame_conflict",
    "empty_llm_prose",
    "no_validated_statements",
)

# How many fabricated tokens / error chars a warning may quote.
_MAX_WARNING_DETAIL = 200


class BriefingOutcome(BaseModel):
    """The generated document plus its honest provenance and status."""

    prose: str
    model: str
    prompt_version: str
    status: Literal["completed", "fallback"]
    used_llm: bool
    warning: str | None = None  # None on the clean LLM path
    run_id: int | None = None  # None when record_run=False


def compose_document(
    statements: str,
    facts: BriefingFacts,
    adjudicated: list[tuple[Claim, Adjudication]],
    country_iso3: str | None = None,
) -> str:
    """The machine-composed frame around gated LLM prose (D7).

    Title, scope counts, Headlines, Key figures, Availability, and
    Limitations are deterministic (built from validated claim fields and
    the facts, exactly as ``render_briefing`` builds them); only the
    Overview/Statements sections carry LLM prose, which reached this
    point having passed adjudication-derived prompting, ``check_prose``,
    and ``check_numeric_fidelity``. The draft is inserted as-is (it
    carries its own ``## Overview`` / ``## Statements`` headers under
    llm-v3); the frame never parses or rewrites it.
    """
    validated = [c for c, a in adjudicated if a.validated]
    rejected = [(c, a) for c, a in adjudicated if not a.validated]
    lines: list[str] = []
    lines.extend(frame_head_lines(facts, validated, country_iso3))
    lines.append(statements.strip())
    lines.append("")
    lines.append("## Availability")
    lines.extend(availability_summary_lines(facts, validated))
    lines.append("")
    lines.append("## Limitations")
    lines.extend(limitation_lines(facts, rejected))
    return "\n".join(lines)


def _detail(exc: LLMError) -> str:
    text = str(exc)
    if len(text) > _MAX_WARNING_DETAIL:
        text = text[:_MAX_WARNING_DETAIL] + "..."
    return text


def generate_briefing(
    session: Session,
    country_iso3: str,
    observations: list[dict[str, Any]],
    *,
    indicator_names: dict[str, str] | None = None,
    llm_source: LlmSource | None = None,
    record_run: bool = True,
) -> BriefingOutcome:
    """Generate one country's briefing; always returns a document.

    ``observations`` must all belong to ``country_iso3`` and be
    latest-vintage, contract-shaped dicts (the service's
    ``ObservationOut`` wire shape) - ``BriefingFacts.from_observations``
    raises ``ValueError`` on duplicates or out-of-vocabulary labels, and
    a foreign-country row is rejected here for the same reason: an
    ambiguous fact is not a fact.

    ``llm_source`` is injectable for tests; when None the real
    ``HttpLlmSource.from_env()`` is resolved at call time. ``record_run``
    persists the audit row (append-only) and returns its id.
    """
    for obs in observations:
        if obs.get("country_iso3") != country_iso3:
            raise ValueError(
                f"observation for {obs.get('country_iso3')!r} passed to a "
                f"{country_iso3!r} briefing - one country per run"
            )

    facts = BriefingFacts.from_observations(observations, indicator_names)
    adjudicated = adjudicate_all(build_claims(facts), facts)
    validated = [c for c, a in adjudicated if a.validated]

    prose: str
    model: str
    prompt_version: str
    status: Literal["completed", "fallback"]
    used_llm = False
    warning: str | None = None

    if not validated:
        # Nothing a statement may be derived from - the LLM is not even
        # called; the deterministic document names the empty scope.
        prose = render_briefing(facts, adjudicated, country_iso3)
        model, prompt_version = DETERMINISTIC_MODEL, DETERMINISTIC_PROMPT_VERSION
        status = "fallback"
        warning = "no_validated_statements"
    else:
        prose, model, prompt_version, status, used_llm, warning = _try_llm(
            facts, validated, adjudicated, llm_source, country_iso3
        )

    run_id = (
        record_briefing_run(
            session,
            model=model,
            prompt_version=prompt_version,
            adjudicated=adjudicated,
            status=status,
        )
        if record_run
        else None
    )
    return BriefingOutcome(
        prose=prose,
        model=model,
        prompt_version=prompt_version,
        status=status,
        used_llm=used_llm,
        warning=warning,
        run_id=run_id,
    )


def _try_llm(
    facts: BriefingFacts,
    validated: list[Claim],
    adjudicated: list[tuple[Claim, Adjudication]],
    llm_source: LlmSource | None,
    country_iso3: str,
) -> tuple[str, str, str, Literal["completed", "fallback"], bool, str | None]:
    """The LLM path with every gate; returns the outcome fields.

    Gate order: configuration -> transport -> response shape ->
    banned phrases -> numeric fidelity -> frame structure (llm-v3: the
    draft must carry its own Overview/Statements headings and must not
    echo a machine-frame heading). The first failure wins and produces
    the deterministic fallback plus the reason; integrity reasons win
    over structural ones.
    """

    def fallback(warning: str) -> tuple[str, str, str, Literal["fallback"], bool, str]:
        return (
            render_briefing(facts, adjudicated, country_iso3),
            DETERMINISTIC_MODEL,
            DETERMINISTIC_PROMPT_VERSION,
            "fallback",
            False,
            warning,
        )

    if llm_source is None:
        try:
            llm_source = HttpLlmSource.from_env()
        except LLMConfigError as exc:
            return fallback(f"llm_not_configured: {_detail(exc)}")

    try:
        llm_prose = llm_source.generate(build_prompt(facts, validated))
    except LLMConfigError as exc:
        return fallback(f"llm_not_configured: {_detail(exc)}")
    except LLMTransportError as exc:
        return fallback(f"llm_transport_error: {_detail(exc)}")
    except (LLMResponseError, LLMError) as exc:
        return fallback(f"llm_response_error: {_detail(exc)}")

    if not llm_prose.strip():
        return fallback("empty_llm_prose")
    banned = check_prose(llm_prose)
    if banned:
        return fallback(f"banned_phrase: {', '.join(banned)}")
    fabricated = check_numeric_fidelity(llm_prose, validated)
    if fabricated:
        quoted = ", ".join(fabricated[:5])
        suffix = ", ..." if len(fabricated) > 5 else ""
        return fallback(f"fabricated_number: {quoted}{suffix}")
    frame_issues = check_frame_conflict(llm_prose)
    if frame_issues:
        quoted = ", ".join(frame_issues[:5])
        suffix = ", ..." if len(frame_issues) > 5 else ""
        return fallback(f"frame_conflict: {quoted}{suffix}")

    return (
        compose_document(llm_prose, facts, adjudicated, country_iso3),
        llm_source.model,
        llm_source.prompt_version,
        "completed",
        True,
        None,
    )
