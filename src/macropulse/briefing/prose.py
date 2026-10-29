"""Deterministic prose assembly and rejection tests (S16 + readability frame).

``render_briefing`` assembles a document ONLY from validated claims:
rejected claims never reach the prose (their fate is the separate
rejection report, and a count of them appears under Limitations so the
document cannot hide that anything was tried and refused).

The document is markdown with a machine-composed readability frame
(2026-10-29 redesign): ``## Headlines`` (deterministic bullets from
validated claim fields) and ``## Key figures`` (a table) carry
DISPLAY-ROUNDED values under a visible ``ROUNDING_NOTE``; ``##
Statements`` carries the validated claim texts verbatim at full
precision; ``## Availability`` is compacted to per-indicator counts
(the full per-observation detail lives in the persisted claims audit).
All frame builders here are shared with ``generate.compose_document``
so both document paths read the same way.

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

``check_frame_conflict`` is the structure-level rejection layer for the
LLM draft (llm-v3): the draft must carry its own ``## Overview`` and
``## Statements`` headings and must NOT carry any machine-frame heading
(Headlines, Key figures, Availability, Limitations, Scope) - the frame
is composed around the draft, never echoed by it.

The closing boundary line of the document cites the code-level
``NON_CLAIMS`` constant from ``macropulse.scope`` - a standing scope
statement, not a data claim.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

from macropulse.briefing.claims import Adjudication, Claim
from macropulse.briefing.facts import BriefingFact, BriefingFacts
from macropulse.scope import COUNTRIES

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


# Frame-structure guard for the LLM draft (llm-v3). The draft must open
# its own two sections and must never echo a machine-frame heading -
# enforced mechanically, not by trusting the prompt instruction.
FRAME_HEADING_NAMES = (
    "Headlines",
    "Key figures",
    "Availability",
    "Limitations",
    "Scope",
)
REQUIRED_DRAFT_HEADINGS = ("Overview", "Statements")

# A markdown heading line: up to 3 leading spaces, 1-6 '#'s, then the
# heading text. Whole-line matches only, so an inline mention of
# "limitations" in prose never trips the check.
_HEADING_LINE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.*?)[ \t]*$", re.MULTILINE)


def check_frame_conflict(draft: str) -> list[str]:
    """Structural problems in an LLM draft; empty means it fits the frame.

    Reports missing required headings (``Overview``, ``Statements``) and
    forbidden machine-frame headings (``FRAME_HEADING_NAMES``). Heading
    names are compared case-insensitively and must match the whole
    heading text - a sentence mentioning "key figures" is not a heading.
    """
    headings = [
        match.group(1).strip().lower() for match in _HEADING_LINE.finditer(draft)
    ]
    issues: list[str] = []
    for name in REQUIRED_DRAFT_HEADINGS:
        if name.lower() not in headings:
            issues.append(f"missing_heading: {name}")
    forbidden = {name.lower() for name in FRAME_HEADING_NAMES}
    for heading in headings:
        if heading in forbidden:
            issues.append(f"frame_heading: {heading}")
    return issues


DOCUMENT_TITLE = "# MacroPulse briefing"

# Display rounding (user-approved policy, 2026-10-29): the machine-composed
# Headlines / Key figures sections round for readability and say so; the
# Statements section and the persisted claims carry full precision exactly
# as served. Rounding is presentation, never a restatement of the record.
ROUNDING_NOTE = (
    "_Values in Headlines and Key figures are rounded for display "
    "(2 decimals); Statements carry full precision exactly as served._"
)


def _country_name(country_iso3: str) -> str:
    """Panel display name for an iso3; the iso3 itself when not on the panel.

    Never a fabricated name: an unknown code renders as the code.
    """
    return next(
        (c.name for c in COUNTRIES if c.iso3 == country_iso3), country_iso3
    )


def title_line(
    facts: BriefingFacts | None = None, country_iso3: str | None = None
) -> str:
    """The markdown title, naming the country (or countries) it covers.

    An explicit ``country_iso3`` wins (the generation path knows it);
    otherwise the countries are derived from the facts payload (all three
    partitions, sorted). One country: "— Germany (DEU)". Several: the
    names joined. None (the empty-scope document): the bare title.
    """
    countries: list[str]
    if country_iso3 is not None:
        countries = [country_iso3]
    elif facts is not None:
        countries = sorted(
            {f.country_iso3 for f in facts.facts}
            | {m.country_iso3 for m in facts.missing}
            | {e.country_iso3 for e in facts.excluded}
        )
    else:
        countries = []
    if not countries:
        return DOCUMENT_TITLE
    if len(countries) == 1:
        iso3 = countries[0]
        name = _country_name(iso3)
        suffix = f" ({iso3})" if name != iso3 else ""
        return f"{DOCUMENT_TITLE} — {name}{suffix}"
    names = ", ".join(_country_name(iso3) for iso3 in countries)
    return f"{DOCUMENT_TITLE} — {names}"


def display_value(value: float) -> str:
    """A value rounded for display: 2 decimals, trailing zeros stripped.

    Decimal ROUND_HALF_UP over ``repr(value)`` - never Python's ``round``
    (banker's rounding over binary floats would show 2.675 as "2.67").
    A nonzero value that rounds to zero is shown as "<0.01" (or ">-0.01"
    when negative): display rounding must never flatten a real observed
    value to "0", which would fabricate a zero. Non-finite input renders
    as ``repr`` rather than crashing document generation. No thousands
    separators, no scientific notation.
    """
    if not math.isfinite(value):
        return repr(value)
    if value == 0:
        return "0"
    with localcontext() as ctx:
        ctx.prec = 60  # huge floats quantize without InvalidOperation
        quantized = Decimal(repr(value)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    if quantized == 0:
        return "<0.01" if value > 0 else ">-0.01"
    text = f"{quantized:f}".rstrip("0").rstrip(".")
    return text or "0"


def _md_cell(text: str) -> str:
    """Make ``text`` safe inside a markdown table cell."""
    return text.replace("|", "\\|")


def _direction(current: float, prior: float) -> str:
    """House direction wording (descriptive comparison only)."""
    if current > prior:
        return "up from"
    if current < prior:
        return "down from"
    return "unchanged from"


def _indicator_label(facts: BriefingFacts, indicator_id: str) -> str:
    """"Name [id]" - or just the id when no distinct name is known."""
    name = facts.indicator_label(indicator_id)
    return name if name == indicator_id else f"{name} [{indicator_id}]"


# How many entries the Headlines section carries (the Key figures table
# is exhaustive). Selection is deterministic - sorted by (country,
# indicator), never merit-based, since merit rankings are a banned
# phrase class.
_HEADLINE_LIMIT = 4


def _display_entries(validated: Sequence[Claim]) -> list[tuple[str, str, Claim]]:
    """One (country, indicator, claim) entry per series, sorted.

    Prefers the validated change claim (richer: value + prior +
    direction) and falls back to the level claim - so the frame shows a
    comparison exactly when the claims layer validated one (consecutive
    periods only), and never computes one itself.
    """
    levels = {
        (c.country_iso3, c.indicator_id): c for c in validated if c.kind == "level"
    }
    changes = {
        (c.country_iso3, c.indicator_id): c for c in validated if c.kind == "change"
    }
    entries: list[tuple[str, str, Claim]] = []
    for key in sorted(levels.keys() | changes.keys()):
        entries.append((key[0], key[1], changes.get(key) or levels[key]))
    return entries


def _facts_index(facts: BriefingFacts) -> dict[tuple[str, str, str], BriefingFact]:
    return {
        (f.indicator_id, f.country_iso3, f.period): f for f in facts.facts
    }


def headline_lines(facts: BriefingFacts, validated: Sequence[Claim]) -> list[str]:
    """The machine-composed Headlines bullets (both document paths).

    Built from validated claim STRUCTURED fields only - no text parsing,
    no computation beyond display rounding. The first ``_HEADLINE_LIMIT``
    series (sorted by country, indicator) get a bullet; the comparison
    clause appears only when a validated change claim exists (never
    computed across periods). Multi-country payloads name the economy
    per bullet. A recorded-missing summary bullet closes the block when
    availability claims exist, pointing at the itemized Availability
    section.
    """
    entries = _display_entries(validated)
    index = _facts_index(facts)
    multi = len({country for country, _, _ in entries}) > 1

    lines: list[str] = []
    for country, indicator, claim in entries[:_HEADLINE_LIMIT]:
        label = _md_cell(_indicator_label(facts, indicator))
        fact = index.get((indicator, country, claim.period))
        unit = f" {fact.unit}" if fact is not None else ""
        suffix = f" ({country})" if multi else ""
        if claim.kind == "change":
            lines.append(
                f"- **{label}**: **{display_value(claim.value)}**{unit} "
                f"in {claim.period}, "
                f"{_direction(claim.value, claim.prior_value)} "
                f"{display_value(claim.prior_value)} in "
                f"{claim.prior_period}{suffix}."
            )
        else:
            lines.append(
                f"- **{label}**: **{display_value(claim.value)}**{unit} "
                f"in {claim.period}{suffix}."
            )
    if not entries:
        lines.append("- No validated value statements.")

    availability = [c for c in validated if c.kind == "availability"]
    if availability:
        ids = sorted({c.indicator_id for c in availability})
        lines.append(
            f"- Recorded missing: {len(availability)} observation(s) "
            f"across {len(ids)} indicator(s) - itemized under Availability."
        )
    return lines


def key_figures_table(
    facts: BriefingFacts, validated: Sequence[Claim]
) -> list[str]:
    """The markdown Key figures table: one row per series with a claim.

    Values are display-rounded (the ROUNDING_NOTE covers this section);
    unit and source come from the cited observation in the facts, never
    from text parsing. Rows are sorted by (country, indicator) -
    deterministic, not merit-based. A series without a validated change
    claim names that honestly ("no consecutive prior period") instead of
    inventing a comparison. Multi-country payloads gain an Economy
    column.
    """
    entries = _display_entries(validated)
    if not entries:
        return ["- No validated value statements."]

    index = _facts_index(facts)
    multi = len({country for country, _, _ in entries}) > 1

    columns = ["Indicator", "Latest period", "Value", "Change", "Source"]
    if multi:
        columns.insert(0, "Economy")
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    for country, indicator, claim in entries:
        fact = index.get((indicator, country, claim.period))
        unit = _md_cell(fact.unit) if fact is not None else ""
        source = (
            _md_cell(f"{fact.source_system} {fact.source_code}")
            if fact is not None
            else "-"
        )
        if claim.kind == "change":
            change_cell = (
                f"{_direction(claim.value, claim.prior_value)} "
                f"**{display_value(claim.prior_value)}** ({claim.prior_period})"
            )
        else:
            change_cell = "no consecutive prior period"
        cells = [
            _md_cell(_indicator_label(facts, indicator)),
            claim.period,
            f"**{display_value(claim.value)}** {unit}".strip(),
            change_cell,
            source,
        ]
        if multi:
            cells.insert(0, country)
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def availability_summary_lines(
    facts: BriefingFacts, validated: Sequence[Claim]
) -> list[str]:
    """Recorded missingness, compacted to one line per indicator.

    The per-observation wall (354 bullets for a panel-scale country) is
    presentation noise that HID rather than revealed: the document names
    every indicator with counts and recorded reasons, while the full
    per-observation detail stays in the run's persisted claims (the
    audit trail, served by GET /briefing/{run_id} and the dashboard
    expander). Missingness is still never hidden - it is summarized
    honestly and itemized in the record.
    """
    availability = [c for c in validated if c.kind == "availability"]
    if not availability:
        return ["- No missing observations in the served set."]

    by_indicator: dict[str, list[Claim]] = {}
    for claim in availability:
        by_indicator.setdefault(claim.indicator_id, []).append(claim)

    lines: list[str] = []
    for indicator_id in sorted(by_indicator):
        claims = by_indicator[indicator_id]
        reasons = sorted(
            {c.missing_reason or "no reason recorded" for c in claims}
        )
        lines.append(
            f"- {_md_cell(_indicator_label(facts, indicator_id))}: "
            f"{len(claims)} observation(s) recorded missing "
            f"(reasons: {', '.join(reasons)})."
        )
    lines.append(
        "- The full per-observation list is persisted with this run's "
        "claims (audit trail)."
    )
    return lines


def frame_head_lines(
    facts: BriefingFacts,
    validated: Sequence[Claim],
    country_iso3: str | None = None,
) -> list[str]:
    """The shared machine frame head: title, scope, Headlines, Key figures.

    Both document paths (``render_briefing`` here and
    ``generate.compose_document``) open with this block, so the
    readability frame never drifts between the LLM and fallback outputs.
    The ROUNDING_NOTE renders only when there are rounded rows to cover.
    """
    lines: list[str] = []
    lines.append(title_line(facts, country_iso3))
    lines.append("")
    lines.append(scope_line(facts))
    lines.append("")
    lines.append("## Headlines")
    lines.extend(headline_lines(facts, validated))
    lines.append("")
    lines.append("## Key figures")
    lines.extend(key_figures_table(facts, validated))
    if _display_entries(validated):
        lines.append("")
        lines.append(ROUNDING_NOTE)
    lines.append("")
    return lines


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
    country_iso3: str | None = None,
) -> str:
    """Assemble the fallback document from validated claims only.

    Pure function of its inputs - no clock reads, no I/O. The header
    counts come from the facts payload itself. Structure mirrors the LLM
    path's machine frame (Headlines, Key figures, Statements, compacted
    Availability, Limitations) minus the Overview section, which only a
    gated LLM draft carries. Statements render the validated claim texts
    verbatim - full precision, full citations, exactly as adjudicated.
    """
    validated = [c for c, a in adjudicated if a.validated]
    rejected = [(c, a) for c, a in adjudicated if not a.validated]

    lines: list[str] = []
    lines.extend(frame_head_lines(facts, validated, country_iso3))

    lines.append("## Statements")
    statements = [c for c in validated if c.kind in ("level", "change")]
    if statements:
        lines.extend(f"- {c.text}" for c in statements)
    else:
        lines.append("- No validated value statements.")
    lines.append("")

    lines.append("## Availability")
    lines.extend(availability_summary_lines(facts, validated))
    lines.append("")

    lines.append("## Limitations")
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
