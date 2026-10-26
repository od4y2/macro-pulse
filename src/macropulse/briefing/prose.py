"""Deterministic prose assembly and banned-phrase rejection tests (S16).

``render_briefing`` assembles a document ONLY from validated claims:
rejected claims never reach the prose (their fate is the separate
rejection report, and a count of them appears under Limitations so the
document cannot hide that anything was tried and refused).

``check_prose`` is the phrase-level rejection layer enforcing the
project's non-claims boundary on any text - template output now, LLM
output later: causal phrasing, investment advice, forecasting, and
merit rankings are banned patterns (a closed, named vocabulary). The
rendered document is itself run through this check in tests and in the
live demo.

``check_numeric_fidelity`` is the number-level rejection layer for
non-template prose (the LLM path): every numeric token in the text must
decimal-equal a token in the validated claims, so a fabricated number
can never reach the rendered document.

The closing boundary line of the document cites the code-level
``NON_CLAIMS`` constant from ``macropulse.scope`` - a standing scope
statement, not a data claim.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from macropulse.briefing.claims import Adjudication, Claim
from macropulse.briefing.facts import BriefingFacts

# Closed vocabulary of banned phrase classes -> compiled patterns.
# Case-insensitive; word-bounded so legitimate words are not clipped.
BANNED_PATTERNS: dict[str, re.Pattern[str]] = {
    "causal_phrase": re.compile(
        r"\b(?:because|caused|causes|due to|leads to|led to|driven by|"
        r"as a result)\b",
        re.IGNORECASE,
    ),
    "advice_phrase": re.compile(
        r"\b(?:should\s+(?:buy|sell|invest)|recommend\w*|investment advice|"
        r"price target|trading signal)\b",
        re.IGNORECASE,
    ),
    "forecast_phrase": re.compile(
        r"\b(?:will\s+(?:rise|fall|grow|decline|increase|decrease|improve|"
        r"deteriorate)|expected to|forecast\w*|projected|outlook)\b",
        re.IGNORECASE,
    ),
    "merit_ranking_phrase": re.compile(
        r"\b(?:best|worst|strongest|weakest|top[- ]performing|outperform\w*|"
        r"ranked)\b",
        re.IGNORECASE,
    ),
}


def check_prose(text: str) -> list[str]:
    """Banned-phrase reasons found in ``text``; empty means the text passes."""
    return [
        reason for reason, pattern in BANNED_PATTERNS.items() if pattern.search(text)
    ]


# Numeric fidelity guard: a number token is a run of digits (optionally
# comma-grouped, optionally with a decimal fraction). ISO dates tokenize
# into their components ("2025-01-01" -> 2025, 01, 01), which is exactly
# what we want - dates in prose must match dates in the claims too.
NUMBER_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _number_pairs(text: str) -> list[tuple[str, Decimal]]:
    """Numeric tokens of ``text`` as (raw, value) pairs, in order."""
    pairs: list[tuple[str, Decimal]] = []
    for raw in NUMBER_TOKEN.findall(text):
        try:
            pairs.append((raw, Decimal(raw.replace(",", ""))))
        except InvalidOperation:  # defensive: malformed comma grouping
            continue
    return pairs


def numeric_tokens(text: str) -> set[Decimal]:
    """Distinct numeric values appearing in ``text`` (commas stripped)."""
    return {value for _, value in _number_pairs(text)}


def check_numeric_fidelity(text: str, validated_claims: Sequence[Claim]) -> list[str]:
    """Raw numeric tokens in ``text`` not backed by the validated claims.

    Every number in the prose must decimal-equal some number in the
    validated claim texts ("2.90" passes against a claim stating 2.9;
    date components pass because ISO dates appear in claim text). A
    non-empty result means the prose fabricated numbers - the caller
    must not render it. Empty claim list: every number is a violation.
    """
    allowed: set[Decimal] = set()
    for claim in validated_claims:
        allowed |= numeric_tokens(claim.text)
    violations: list[str] = []
    seen: set[Decimal] = set()
    for raw, value in _number_pairs(text):
        if value in allowed or value in seen:
            continue
        violations.append(raw)
        seen.add(value)
    return violations


DOCUMENT_TITLE = "MacroPulse structured briefing"


def scope_line(facts: BriefingFacts) -> str:
    """The deterministic scope statement (counts come from the facts)."""
    economies = sorted({f.country_iso3 for f in facts.facts})
    indicators = sorted({f.indicator_id for f in facts.facts})
    return (
        f"Scope: {len(economies)} economies, {len(indicators)} indicator(s), "
        f"{len(facts.facts)} validated observations (evidence: real). "
        f"{len(facts.excluded)} observation(s) excluded - not real evidence, "
        f"never stated as observed; {len(facts.missing)} recorded missing."
    )


def limitation_lines(
    facts: BriefingFacts,
    rejected: list[tuple[Claim, Adjudication]],
) -> list[str]:
    """The deterministic Limitations section body.

    Worded to contain none of the banned literals: the document must
    pass its own check_prose gate mechanically, with no exemption for
    good intentions - a disclaimer that used the banned phrases would
    be indistinguishable, to the check, from prose committing them.
    """
    lines: list[str] = []
    if facts.excluded:
        labels = sorted({e.evidence_label for e in facts.excluded})
        lines.append(
            f"- {len(facts.excluded)} observation(s) excluded (evidence "
            f"labels: {', '.join(labels)}) - not stated as observed."
        )
    if rejected:
        reasons = sorted({a.reason for _, a in rejected if a.reason})
        lines.append(
            f"- {len(rejected)} candidate claim(s) rejected during validation "
            f"(reasons: {', '.join(reasons)}); rejected text is not shown as "
            "statements."
        )
    lines.append(
        "- This briefing states observed values with citations only; it "
        "makes no causal statements, no rankings of merit, no "
        "forward-looking statements, and no financial guidance (see "
        "macropulse.scope.NON_CLAIMS)."
    )
    return lines


def render_briefing(
    facts: BriefingFacts,
    adjudicated: list[tuple[Claim, Adjudication]],
) -> str:
    """Assemble the document from validated claims only.

    Pure function of its inputs - no clock reads, no I/O. The header
    counts come from the facts payload itself.
    """
    validated = [(c, a) for c, a in adjudicated if a.validated]
    rejected = [(c, a) for c, a in adjudicated if not a.validated]

    lines: list[str] = []
    lines.append(DOCUMENT_TITLE)
    lines.append("=============================")
    lines.append("")
    lines.append(scope_line(facts))
    lines.append("")

    lines.append("Statements")
    lines.append("----------")
    statements = [c for c, _ in validated if c.kind in ("level", "change")]
    if statements:
        lines.extend(f"- {c.text}" for c in statements)
    else:
        lines.append("- No validated value statements.")
    lines.append("")

    lines.append("Availability")
    lines.append("------------")
    availability = [c for c, _ in validated if c.kind == "availability"]
    if availability:
        lines.extend(f"- {c.text}" for c in availability)
    else:
        lines.append("- No missing observations in the served set.")
    lines.append("")

    lines.append("Limitations")
    lines.append("-----------")
    lines.extend(limitation_lines(facts, rejected))
    return "\n".join(lines)


def render_rejection_report(
    adjudicated: list[tuple[Claim, Adjudication]],
) -> str:
    """One line per rejected claim with its reason (the audit trail)."""
    rejected = [(c, a) for c, a in adjudicated if not a.validated]
    if not rejected:
        return "Rejection report: no claims rejected."
    lines = ["Rejection report"]
    for claim, adjudication in rejected:
        lines.append(f"- REJECTED ({adjudication.reason}): {claim.text}")
    return "\n".join(lines)
