"""Typeset presentation of every formula MacroPulse computes (unit S19).

The platform records its formulas twice already: as CODE (the functions
that compute them) and as REGISTRY TEXT (the dicts the methodology
surfaces serve from - ``metrics.FORMULAS``,
``lenses.labor.RELATIONSHIPS``, ``lenses.digital.RELATIONSHIPS``).
This module adds the third face a research report needs: scientific
notation, typeset for rendering.

Governance carries over unchanged:

1. **Anchoring.** Every registry-backed entry carries the registry's
   text EXACTLY; ``validate_typeset()`` compares against the live
   registries, so a registry edit that leaves the typeset layer behind
   is a reported problem, not silent drift. Quantities without a
   registry entry (Spearman rank covariation, panel coverage) are
   anchored to their computing functions by import - the entry cannot
   outlive the code it documents.
2. **No invented math.** The LaTeX restates what the registry text and
   the function docstrings state. Directions, window guards, and
   missingness rules appear in the notation table (and the report's
   captions), never as silent constants inside the math.
3. **Coverage is closed.** Every key in all three registries must
   have a typeset entry, and every registry anchor must resolve - the
   validator checks both directions of the mapping.
"""

from __future__ import annotations

from dataclasses import dataclass

from macropulse.lenses.digital import RELATIONSHIPS as DIGITAL_RELATIONSHIPS
from macropulse.lenses.digital import rank_covariation
from macropulse.lenses.labor import RELATIONSHIPS as LABOR_RELATIONSHIPS
from macropulse.metrics.standardize import panel_coverage
from macropulse.metrics.transforms import FORMULAS

# The text registries the typeset layer anchors to (label -> live dict).
REGISTRY_SOURCES: dict[str, dict[str, str]] = {
    "metrics.FORMULAS": FORMULAS,
    "labor.RELATIONSHIPS": LABOR_RELATIONSHIPS,
    "digital.RELATIONSHIPS": DIGITAL_RELATIONSHIPS,
}

# The code symbols behind the non-registry quantities (label -> object).
CODE_SOURCES: dict[str, object] = {
    "macropulse.lenses.digital.rank_covariation": rank_covariation,
    "macropulse.metrics.standardize.panel_coverage": panel_coverage,
}


@dataclass(frozen=True)
class TypesetFormula:
    """One formula, ready for display math.

    ``latex`` is the display-math BODY - no ``$$`` delimiters (the
    renderer adds them). ``notation`` maps every symbol the reader has
    not seen yet to its meaning. ``anchors`` carries
    ``(registry label, exact registry text)`` pairs; ``code_anchors``
    carries labels from ``CODE_SOURCES`` for quantities computed by a
    function that has no registry entry.
    """

    key: str
    latex: str
    notation: tuple[tuple[str, str], ...]
    anchors: tuple[tuple[str, str], ...] = ()
    code_anchors: tuple[str, ...] = ()


TYPESET: dict[str, TypesetFormula] = {
    f.key: f
    for f in (
        # --- metric transforms (S08) ---------------------------------------
        TypesetFormula(
            key="pct_change",
            latex=r"100\,\left(\frac{v_t}{v_{t-L}} - 1\right)",
            notation=(
                ("v_t", "value at period t"),
                ("L", "lag in months (positive integer)"),
            ),
            anchors=(
                (
                    "metrics.FORMULAS",
                    ("Percent change over a lag of L months: 100 * (v_t / "
                    "v_{t-L} - 1). Requires a positive non-zero base; "
                    "missing inputs stay missing."),
                ),
            ),
        ),
        TypesetFormula(
            key="yoy",
            latex=r"100\,\left(\frac{v_t}{v_{t-12\,\mathrm{m}}} - 1\right)",
            notation=(
                ("v_t", "value at period t"),
                ("v_{t-12\\,\\mathrm{m}}", "same period one year earlier"),
            ),
            anchors=(
                (
                    "metrics.FORMULAS",
                    ("Year-over-year percent change: 100 * (v_t / v_{t-12m} - "
                    "1), i.e. pct_change with L = 12 months. Same period "
                    "one year earlier."),
                ),
            ),
        ),
        TypesetFormula(
            key="mom",
            latex=r"100\,\left(\frac{v_t}{v_{t-1\,\mathrm{m}}} - 1\right)",
            notation=(
                ("v_t", "value at period t"),
                ("v_{t-1\\,\\mathrm{m}}", "the previous month (monthly series only)"),
            ),
            anchors=(
                (
                    "metrics.FORMULAS",
                    ("Month-over-month percent change: 100 * (v_t / v_{t-1m} - "
                    "1), i.e. pct_change with L = 1 month. Monthly series "
                    "only."),
                ),
            ),
        ),
        TypesetFormula(
            key="pp_change",
            latex=r"\delta_t = v_t - v_{t-L}",
            notation=(
                ("\\delta_t", "percentage-point change"),
                ("v_t", "value at period t"),
                ("L", "lag in months"),
            ),
            anchors=(
                (
                    "metrics.FORMULAS",
                    ("Percentage-point change over a lag of L months: v_t - "
                    "v_{t-L}. For rate-type series where percent-of-percent "
                    "is meaningless. Defined for any sign of input."),
                ),
            ),
        ),
        TypesetFormula(
            key="annualized_pct",
            latex=r"100\,\left(\left(1 + \frac{r}{100}\right)^{12/L} - 1\right)",
            notation=(
                ("r", "period-over-period percent change (in percent)"),
                ("12/L", "whole compounding periods per year (12 % L == 0)"),
            ),
            anchors=(
                (
                    "metrics.FORMULAS",
                    ("Annualized percent rate from a period-over-period "
                    "percent change r (lag L months): (1 + r/100)^(12/L) - "
                    "1, expressed in percent. Requires 12 % L == 0 (whole "
                    "compounding periods per year)."),
                ),
            ),
        ),
        TypesetFormula(
            key="rolling_mean",
            latex=r"\bar{v}_t = \frac{1}{W}\sum_{i=0}^{W-1} v_{t-i}",
            notation=(
                ("\\bar{v}_t", "trailing mean at period t"),
                ("W", "window length in periods (frequency steps)"),
                ("v_{t-i}", "the i-th previous period; every member must exist"),
            ),
            anchors=(
                (
                    "metrics.FORMULAS",
                    ("Trailing arithmetic mean over the last W consecutive "
                    "periods (frequency step): sum(v) / W. Every window "
                    "member must exist with a non-NULL value; partial "
                    "windows are missing, never half-computed."),
                ),
            ),
        ),
        # --- robust standardization (S09) -----------------------------------
        TypesetFormula(
            key="robust_z",
            latex=(
                r"z_t = \frac{v_t - \operatorname{median}(W_t)}"
                r"{\operatorname{MAD}(W_t)}"
            ),
            notation=(
                ("z_t", "robust standardized score (direction-adjusted so positive = favorable)"),
                ("W_t", "the trailing N consecutive periods (frequency step)"),
                ("\\operatorname{median}(W_t)", "window median"),
                ("\\operatorname{MAD}(W_t)", "window median absolute deviation"),
            ),
            anchors=(
                (
                    "metrics.FORMULAS",
                    ("Robust fixed-window standardization (S09): "
                    "(v_t - median(window)) / MAD(window) over the trailing "
                    "N consecutive periods (frequency step), "
                    "direction-adjusted so positive = favorable; window "
                    "occupancy >= 3 non-missing members. Zero MAD is "
                    "missing (zero_scale), never fabricated."),
                ),
            ),
        ),
        # --- labor lens relationships (S10) ---------------------------------
        TypesetFormula(
            key="youth_headline_gap",
            latex=r"g_t = u^{\mathrm{youth}}_t - u^{\mathrm{headline}}_t",
            notation=(
                ("g_t", "divergence in percentage points (positive = youth worse)"),
                ("u^{\\mathrm{youth}}_t", "youth unemployment rate"),
                ("u^{\\mathrm{headline}}_t", "headline unemployment rate"),
            ),
            anchors=(
                (
                    "metrics.FORMULAS",
                    ("Youth unemployment minus headline unemployment, in "
                    "percentage points (RQ1 divergence measure, S10 labor "
                    "lens). Positive = youth fare worse than the headline. "
                    "Only computed when both inputs exist; never imputed."),
                ),
                (
                    "labor.RELATIONSHIPS",
                    ("Youth unemployment minus headline unemployment, in "
                    "percentage points (the RQ1 divergence measure). "
                    "Positive = youth worse."),
                ),
            ),
        ),
        TypesetFormula(
            key="youth_ratio",
            latex=r"R_t = \frac{u^{\mathrm{youth}}_t}{u^{\mathrm{headline}}_t}",
            notation=(
                ("R_t", "unitless multiple; None on zero headline"),
                ("u^{\\mathrm{youth}}_t", "youth unemployment rate"),
                ("u^{\\mathrm{headline}}_t", "headline unemployment rate"),
            ),
            anchors=(
                (
                    "labor.RELATIONSHIPS",
                    ("Youth unemployment divided by headline unemployment "
                    "(unitless multiple). Reported alongside the pp gap; "
                    "level-dependent."),
                ),
            ),
        ),
        TypesetFormula(
            key="neet_minus_unemployed",
            latex=r"d_t = \mathrm{NEET}_t - u^{\mathrm{headline}}_t",
            notation=(
                ("d_t", "withdrawn/discouraged component, in percentage points"),
                ("\\mathrm{NEET}_t", "NEET rate (not in education, employment or training)"),
                ("u^{\\mathrm{headline}}_t", "headline unemployment rate"),
            ),
            anchors=(
                (
                    "labor.RELATIONSHIPS",
                    ("NEET rate minus headline unemployment, in percentage "
                    "points. Measures the withdrawn/discouraged component "
                    "of youth disengagement not visible in unemployment."),
                ),
            ),
        ),
        # --- digital lens relationships (S11) --------------------------------
        TypesetFormula(
            key="account_internet_gap",
            latex=r"g_t = a_t - i_t",
            notation=(
                ("g_t", "exclusion among the connected, in percentage points"),
                ("a_t", "account ownership, share of adults"),
                ("i_t", "internet usage, share of population"),
            ),
            anchors=(
                (
                    "digital.RELATIONSHIPS",
                    ("Account ownership (adults) minus internet usage "
                    "(population), in percentage points. Financial "
                    "exclusion among the connected. Denominators differ "
                    "(adults vs population) - a documented comparability "
                    "limitation, reported unadjusted."),
                ),
            ),
        ),
        TypesetFormula(
            key="gender_account_gap",
            latex=r"g_t = a^{\mathrm{female}}_t - a^{\mathrm{all\ adults}}_t",
            notation=(
                ("g_t", "conservative gender gap, in percentage points (negative = women below the national average)"),
                ("a^{\\mathrm{female}}_t", "female account ownership"),
                ("a^{\\mathrm{all\\ adults}}_t", "all-adult account ownership"),
            ),
            anchors=(
                (
                    "digital.RELATIONSHIPS",
                    ("Female account ownership minus all-adult account "
                    "ownership, in percentage points. Conservative proxy "
                    "for the female-male gap (the male series is not in the "
                    "locked catalog; the all-adult average includes women, "
                    "understating the female deficit). Negative = women "
                    "below the national average."),
                ),
            ),
        ),
        # --- quantities without a text registry, anchored to code -----------
        TypesetFormula(
            key="spearman_rho",
            latex=r"\rho = 1 - \frac{6 \sum_{i=1}^{n} d_i^2}{n\,(n^2 - 1)}",
            notation=(
                ("\\rho", "Spearman rank correlation; always reported with n"),
                ("d_i", "rank difference of the i-th economy (ties share average ranks)"),
                ("n", "panel size (10 economies)"),
            ),
            code_anchors=("macropulse.lenses.digital.rank_covariation",),
        ),
        TypesetFormula(
            key="panel_coverage",
            latex=r"C = \frac{\sum_{c} n^{\mathrm{obs}}_c}{\sum_{c} n^{\mathrm{exp}}_c}",
            notation=(
                ("C", "panel coverage as a ratio of sums (S09)"),
                ("n^{\\mathrm{obs}}_c", "observed points for economy c"),
                ("n^{\\mathrm{exp}}_c", "expected points for economy c"),
            ),
            code_anchors=("macropulse.metrics.standardize.panel_coverage",),
        ),
    )
}


def _latex_problems(formula: TypesetFormula) -> list[str]:
    """Structural checks on the display-math body."""
    problems: list[str] = []
    latex = formula.latex
    if latex.count("{") != latex.count("}"):
        problems.append("unbalanced braces")
    if latex.count(r"\left") != latex.count(r"\right"):
        problems.append("unbalanced \\left/\\right")
    if "$" in latex:
        problems.append("contains its own $ delimiters")
    return problems


def validate_typeset() -> list[str]:
    """Problems found in the typeset registry; empty means it is sound.

    Checks: closed coverage of (and by) every text registry, exact
    anchor text, resolvable code anchors, balanced LaTeX, notation
    symbols present in the math, non-empty keys.
    """
    problems: list[str] = []

    for key in TYPESET:
        if not key.strip():
            problems.append("empty typeset key")

    # Every registry key must be typeset, and every registry anchor must
    # carry the registry's exact current text.
    for source_label, registry in REGISTRY_SOURCES.items():
        for key in registry:
            if key not in TYPESET:
                problems.append(f"{source_label} key {key!r} has no typeset entry")
        for entry in TYPESET.values():
            for label, text in entry.anchors:
                if label != source_label:
                    continue
                live = registry.get(entry.key)
                if live is None:
                    problems.append(
                        f"{source_label} anchor on unknown key {entry.key!r}"
                    )
                elif live != text:
                    problems.append(
                        f"{entry.key}: anchor text drifted from {source_label}"
                    )

    for entry in TYPESET.values():
        if not entry.anchors and not entry.code_anchors:
            problems.append(f"{entry.key}: no anchor (registry or code)")
        for label, _ in entry.anchors:
            if label not in REGISTRY_SOURCES:
                problems.append(f"{entry.key}: unknown registry source {label!r}")
        for label in entry.code_anchors:
            if label not in CODE_SOURCES or not callable(CODE_SOURCES[label]):
                problems.append(f"{entry.key}: unresolvable code anchor {label!r}")
        problems.extend(
            f"{entry.key}: {problem}"
            for problem in _latex_problems(entry)
        )
        for symbol, _ in entry.notation:
            if symbol not in entry.latex:
                problems.append(
                    f"{entry.key}: notation symbol {symbol!r} not in the latex"
                )

    return problems
