"""Locked research scope for MacroPulse (unit S01).

This module is the single machine-readable source of truth for the research
questions, non-claims, country panel, modules, and evidence vocabulary.
Downstream units must import from here instead of redefining these constants.
"""

from __future__ import annotations

from typing import NamedTuple


class Country(NamedTuple):
    iso3: str
    name: str
    rationale: str


class ResearchQuestion(NamedTuple):
    rq_id: str
    question: str
    lens: str
    unit: str


# Ten representative economies locked in S01 (student decision, 2026-08-19).
# Balanced global set: G7 core plus major emerging economies across four
# continents, all covered by FRED mirrors, World Bank, and ILOSTAT.
COUNTRIES: tuple[Country, ...] = (
    Country("USA", "United States", "FRED home turf; benchmark economy"),
    Country("CHN", "China", "Second-largest economy; vintage and methodology breaks"),
    Country("JPN", "Japan", "Developed, aging, deflation case study"),
    Country("DEU", "Germany", "EU anchor; energy-shock episode"),
    Country("GBR", "United Kingdom", "Post-Brexit labor market measurement"),
    Country("IND", "India", "Largest emerging economy; youth transition lens"),
    Country("BRA", "Brazil", "Latin America; commodity-cycle economy"),
    Country("KOR", "South Korea", "Advanced digital economy benchmark"),
    Country("ZAF", "South Africa", "African economy; high structural unemployment"),
    Country("MEX", "Mexico", "Nearshoring and remittances case"),
)

# Research questions locked in S01. Each maps to the unit that delivers it.
RESEARCH_QUESTIONS: tuple[ResearchQuestion, ...] = (
    ResearchQuestion(
        rq_id="RQ1",
        question=(
            "How do youth unemployment, NEET, and school-to-work transition "
            "indicators diverge from headline unemployment across the panel, "
            "and how does that divergence change across data vintages?"
        ),
        lens="labor-slack-youth",
        unit="S10",
    ),
    ResearchQuestion(
        rq_id="RQ2",
        question=(
            "How do internet, mobile, and account-ownership rates co-vary with "
            "income and gender across the panel, and where do measurement gaps "
            "hide digital exclusion?"
        ),
        lens="digital-inclusion",
        unit="S11",
    ),
    ResearchQuestion(
        rq_id="RQ3",
        question=(
            "What do payment-outage episodes reveal about resilience "
            "measurement in digitized healthcare systems, for the case-study "
            "subset of the panel?"
        ),
        lens="payment-resilience-healthcare",
        unit="S12",
    ),
    ResearchQuestion(
        rq_id="RQ4",
        question=(
            "Where do official release calendars, revisions, and methodology "
            "breaks create systematic blind spots in cross-country comparison?"
        ),
        lens="vintage-transparency",
        unit="S07",
    ),
)

# Claims the project explicitly does not make. Boundaries from
# docs/AuthoritativePlan.md and docs/DataGovernance.md.
NON_CLAIMS: tuple[str, ...] = (
    "No causal claims about macroeconomic outcomes without documented evidence.",
    "No investment advice, price targets, or trading signals.",
    "No fabricated values, release dates, citations, or test results.",
    "No presentation of synthetic, mocked, or cached data as observed data.",
    "AI-generated prose derives only from validated structured inputs.",
    "No claims of live API, cloud deployment, or production status without evidence.",
    "Cross-country comparisons are descriptive, not rankings or scores of merit.",
)

# Data-source labels that must tag every dataset and observation
# (docs/AuthoritativePlan.md delivery boundaries).
EVIDENCE_LABELS: frozenset[str] = frozenset(
    {"real", "synthetic", "mocked", "cached", "external"}
)

# Provenance fields every normalized observation must preserve
# (docs/Architecture.md section 3).
PROVENANCE_FIELDS: tuple[str, ...] = (
    "period",
    "release_time",
    "retrieval_time",
    "vintage",
    "unit",
    "frequency",
    "seasonal_adjustment",
    "source",
    "quality_grade",
)

# Analytical modules locked in S01. "traditional" is the baseline layer;
# the others are the blind-spot lenses.
MODULES: tuple[str, ...] = (
    "traditional-indicators",
    "labor-slack-youth",
    "digital-inclusion",
    "payment-resilience-healthcare",
    "vintage-transparency",
)


def validate_scope() -> list[str]:
    """Return a list of scope violations; empty means the locked scope is valid.

    Exposed so tests can assert invariants and so later units can fail fast
    if the scope file is edited inconsistently.
    """
    problems: list[str] = []

    iso3_codes = [c.iso3 for c in COUNTRIES]
    if len(iso3_codes) != len(set(iso3_codes)):
        problems.append("duplicate ISO3 codes in country panel")
    if len(COUNTRIES) != 10:
        problems.append(f"country panel must have 10 economies, found {len(COUNTRIES)}")
    for c in COUNTRIES:
        if len(c.iso3) != 3 or not c.iso3.isalpha() or not c.iso3.isupper():
            problems.append(f"invalid ISO3 code: {c.iso3!r}")
        if not c.name or not c.rationale:
            problems.append(f"country {c.iso3} missing name or rationale")

    rq_ids = [q.rq_id for q in RESEARCH_QUESTIONS]
    if len(rq_ids) != len(set(rq_ids)):
        problems.append("duplicate research question ids")
    lenses = [q.lens for q in RESEARCH_QUESTIONS]
    if len(lenses) != len(set(lenses)):
        problems.append("duplicate research question lenses")
    for q in RESEARCH_QUESTIONS:
        if not q.question.endswith("?"):
            problems.append(f"{q.rq_id} is not phrased as a question")
        if q.lens not in MODULES:
            problems.append(f"{q.rq_id} references unknown module {q.lens!r}")

    module_ids = list(MODULES)
    if len(module_ids) != len(set(module_ids)):
        problems.append("duplicate module ids")

    if len(NON_CLAIMS) == 0:
        problems.append("non-claims boundary is empty")

    required_labels = {"real", "synthetic", "mocked", "cached", "external"}
    if not required_labels.issubset(EVIDENCE_LABELS):
        problems.append("evidence vocabulary missing required governance labels")

    required_provenance = {
        "period", "release_time", "retrieval_time", "vintage", "unit",
        "frequency", "seasonal_adjustment", "source", "quality_grade",
    }
    if not required_provenance.issubset(set(PROVENANCE_FIELDS)):
        problems.append("provenance vocabulary missing required fields")

    return problems
