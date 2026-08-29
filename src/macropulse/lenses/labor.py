"""Labor slack and youth transition lens (unit S10, RQ1).

RQ1: how do youth unemployment, NEET, and school-to-work transition
indicators diverge from headline unemployment across the panel, and how
does that divergence change across data vintages?

Methodology: **component-first**. The lens never mixes indicators into a
single index score. Each component keeps its own identity (indicator,
value, missingness, source, vintage); the analysis is the RELATIONSHIPS
between components, computed per period and reported per component.
Full documentation: docs/LaborLensMethodology.md.

Components (all from the catalog's ``labor-slack-youth`` module plus the
headline ``unemployment_rate``):

- headline unemployment (percent)
- youth unemployment (percent)
- NEET rate (percent)
- tertiary enrollment (percent_gross; the school-to-work transition
  proxy - higher = staying in education, i.e. OUT of the youth labor
  force and NEET-eligible pool)

Derived relationships (each an explicit, documented quantity):

- ``youth_headline_gap``   youth unemployment - headline unemployment, in
  percentage points. The RQ1 "divergence" measure; positive = youth fare
  worse than the headline, negative = youth fare better.
- ``youth_ratio``          youth / headline (unitless multiple). Reported
  alongside the gap because a 2x ratio and a 20pp gap describe different
  labor markets (level-dependent); neither is collapsed into the other.
- ``neet_minus_unemployed``  NEET - headline unemployment, in percentage
  points. NEET includes non-participating youth (not counted as
  unemployed); the excess over unemployment measures the
  *discouraged/withdrawal* component of disengagement.
- ``enrollment_note``      tertiary enrollment is reported as-is with its
  own sign convention (higher = more youth in education). It is NOT
  combined arithmetically with the other components: enrollment growth
  mechanically lowers youth unemployment (composition, not welfare) and
  no causal or welfare claim is made (S01 non-claims).

Missingness: a relationship is computed only when every input exists and
is non-NULL; otherwise it is missing with an explicit reason naming the
missing component(s). No imputation, no partial arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macropulse.catalog import CATALOG

LENS_INDICATORS = {
    "unemployment_rate": "headline",
    "youth_unemployment_rate": "youth",
    "neet_rate": "neet",
    "tertiary_enrollment": "enrollment",
}

# Relationship definitions recorded for methodology traceability.
RELATIONSHIPS: dict[str, str] = {
    "youth_headline_gap": (
        "Youth unemployment minus headline unemployment, in percentage "
        "points (the RQ1 divergence measure). Positive = youth worse."
    ),
    "youth_ratio": (
        "Youth unemployment divided by headline unemployment (unitless "
        "multiple). Reported alongside the pp gap; level-dependent."
    ),
    "neet_minus_unemployed": (
        "NEET rate minus headline unemployment, in percentage points. "
        "Measures the withdrawn/discouraged component of youth "
        "disengagement not visible in unemployment."
    ),
}


class LensError(RuntimeError):
    """Raised when the lens is applied outside its rules."""


@dataclass(frozen=True)
class Component:
    """One indicator's value at one (period, vintage), identity preserved."""

    indicator_id: str
    period: date
    value: float | None
    missing_reason: str | None
    vintage: date | None = None  # None when the caller has no vintage info

    def __post_init__(self) -> None:
        if self.value is None and not self.missing_reason:
            raise ValueError(
                f"missing {self.indicator_id} at {self.period} needs a reason"
            )
        if self.value is not None and self.missing_reason:
            raise ValueError(
                f"{self.indicator_id} at {self.period} has both a value and "
                "a missing_reason"
            )


@dataclass(frozen=True)
class SlackProfile:
    """The component-first RQ1 view for one (country, period, vintage).

    Components carry their own missingness; relationships are computed
    only from present values and carry explicit reasons otherwise.
    """

    country_iso3: str
    period: date
    vintage: date
    headline: float | None
    youth: float | None
    neet: float | None
    enrollment: float | None
    missing_components: tuple[tuple[str, str], ...]  # (component, reason)

    @property
    def youth_headline_gap(self) -> float | None:
        if self.youth is None or self.headline is None:
            return None
        return self.youth - self.headline

    @property
    def youth_ratio(self) -> float | None:
        if self.youth is None or self.headline is None or self.headline == 0:
            return None
        return self.youth / self.headline

    @property
    def neet_minus_unemployed(self) -> float | None:
        if self.neet is None or self.headline is None:
            return None
        return self.neet - self.headline


def _catalog_direction(indicator_id: str) -> str:
    for ind in CATALOG:
        if ind.indicator_id == indicator_id:
            return ind.direction
    raise LensError(f"indicator {indicator_id!r} is not in the catalog")


def build_profile(
    components: list[Component],
    country_iso3: str,
) -> SlackProfile:
    """Assemble one (country, period, vintage) profile from components.

    All components must share the same period and vintage (one coherent
    snapshot; vintage-divergence analysis compares SEPARATE profiles).
    At least one component must be present.
    """
    periods = {c.period for c in components}

    lens_only = [c for c in components if c.indicator_id in LENS_INDICATORS]
    if not lens_only:
        raise LensError(
            "no RQ1 lens indicators among components: "
            f"{[c.indicator_id for c in components]}"
        )
    components = lens_only

    period = components[0].period
    for c in components:
        if c.period != period:
            raise LensError(
                f"components span multiple periods: {sorted(periods)}"
            )

    # Vintage: the components' shared vintage when they carry one; the
    # period itself when they do not (snapshot semantics: WB/ILOSTAT
    # vintage = retrieval date; a caller assembling from one fetch has a
    # coherent snapshot by construction).
    vintages = {c.vintage for c in components if c.vintage is not None}
    if len(vintages) > 1:
        raise LensError(
            f"components span multiple vintages: {sorted(vintages)}; "
            "build one profile per vintage instead"
        )
    vint = vintages.pop() if vintages else period

    def value_of(indicator_id: str) -> tuple[float | None, str | None]:
        for c in components:
            if c.indicator_id == indicator_id:
                return c.value, c.missing_reason
        return None, "component_not_fetched"

    headline, headline_reason = value_of("unemployment_rate")
    youth, youth_reason = value_of("youth_unemployment_rate")
    neet, neet_reason = value_of("neet_rate")
    enrollment, enrollment_reason = value_of("tertiary_enrollment")

    missing: list[tuple[str, str]] = []
    for name, value, reason in (
        ("headline", headline, headline_reason),
        ("youth", youth, youth_reason),
        ("neet", neet, neet_reason),
        ("enrollment", enrollment, enrollment_reason),
    ):
        if value is None:
            missing.append((name, reason or "unknown"))

    return SlackProfile(
        country_iso3=country_iso3,
        period=period,
        vintage=vint,
        headline=headline,
        youth=youth,
        neet=neet,
        enrollment=enrollment,
        missing_components=tuple(missing),
    )


def youth_headline_gap_series(
    headline: dict[date, float | None],
    youth: dict[date, float | None],
    reasons: dict[str, dict[date, str]] | None = None,
) -> dict[date, float | None]:
    """The RQ1 divergence series: youth - headline per period (pp).

    Only periods where BOTH values exist produce a number; every other
    period maps to None (explicit missingness upstream; this function
    computes, it does not impute). ``reasons`` (optional) is a nested
    {indicator: {period: reason}} map the caller already holds.
    """
    reasons = reasons or {}
    out: dict[date, float | None] = {}
    for period in sorted(set(headline) | set(youth)):
        h, y = headline.get(period), youth.get(period)
        if h is not None and y is not None:
            out[period] = y - h
        else:
            out[period] = None
            if h is None:
                reasons.setdefault("headline", {}).setdefault(period, "missing")
            if y is None:
                reasons.setdefault("youth", {}).setdefault(period, "missing")
    return out


def divergence_by_vintage(
    profiles: list[SlackProfile],
) -> dict[date, list[float]]:
    """RQ1's vintage question: the youth-headline gap per (period, vintage).

    Groups profiles by period; returns period -> sorted list of gaps from
    every vintage that has one. Multiple entries = the divergence itself
    was revised; single = stable across stored vintages. Descriptive only
    - no claim about which vintage is "right".
    """
    out: dict[date, list[float]] = {}
    for profile in profiles:
        gap = profile.youth_headline_gap
        if gap is None:
            continue
        out.setdefault(profile.period, []).append(gap)
    return {period: sorted(gaps) for period, gaps in out.items()}


def validate_lens_catalog() -> list[str]:
    """Consistency check: lens indicators exist and carry directions."""
    problems: list[str] = []
    for indicator_id in LENS_INDICATORS:
        try:
            _catalog_direction(indicator_id)
        except LensError as exc:
            problems.append(str(exc))
    return problems


__all__ = [
    "LENS_INDICATORS",
    "RELATIONSHIPS",
    "Component",
    "LensError",
    "SlackProfile",
    "build_profile",
    "divergence_by_vintage",
    "validate_lens_catalog",
    "youth_headline_gap_series",
]
