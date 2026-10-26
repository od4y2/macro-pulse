"""Payment resilience lens (unit S12, RQ3).

RQ3: what do payment-outage episodes reveal about resilience
measurement in digitized healthcare systems, for the case-study subset
of the panel?

This module is the PROFILE half of RQ3: observed payment-digitization
levels with macro context, per country. The EPISODE half (the bounded
China healthcare geography case, with citation-backed outage records)
lives in ``macropulse.case_study``.

Components (both are locked catalog indicators):

- ``digital_payments``  made or received a digital payment in the past
  year (% of adults; WB Findex ``g20.any``, survey waves only)
- ``health_expenditure`` current health expenditure (% of GDP; WB
  ``SH.XPD.CHEX.GD.ZS``) - MACRO CONTEXT ONLY. The catalog marks it
  "not a resilience measure itself"; it is reported, never combined.

**No arithmetic relationship is defined between the two components.**
Payment prevalence and health spending are different constructs with
different denominators; combining them (a ratio, a gap, a score) would
embed a dependence claim the evidence does not support (S01 non-claims).
RQ3's relationships live at the episode level, not between these levels.

Methodology follows S10/S11's component-first pattern: no index, no
composite score, each component keeps its identity; missingness is
named, never imputed. Full documentation:
docs/PaymentResilienceCaseStudy.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macropulse.catalog import CATALOG

LENS_INDICATORS = {
    "digital_payments_made_pct": "digital_payments",
    "health_expenditure_pct_gdp": "health_expenditure",
}

# Recorded so the no-relationship policy is traceable, not implicit.
COMBINATION_POLICY = (
    "digital_payments and health_expenditure are reported as levels only; "
    "no arithmetic relationship is defined between them (combining them "
    "would embed a dependence claim the evidence does not support)"
)


class LensError(RuntimeError):
    """Raised when the lens is applied outside its rules."""


@dataclass(frozen=True)
class Component:
    """One payment-lens series' value at one (period, vintage)."""

    key: str  # digital_payments | health_expenditure
    indicator_id: str | None  # catalog id when the component is an indicator
    source_code: str  # source code actually fetched
    period: date
    value: float | None
    missing_reason: str | None
    vintage: date | None = None

    def __post_init__(self) -> None:
        if self.value is None and not self.missing_reason:
            raise ValueError(f"missing {self.key} at {self.period} needs a reason")
        if self.value is not None and self.missing_reason:
            raise ValueError(
                f"{self.key} at {self.period} has both a value and a missing_reason"
            )


@dataclass(frozen=True)
class PaymentProfile:
    """The RQ3 levels view for one (country, period, vintage).

    Levels only - by design there is no derived relationship between the
    components (see COMBINATION_POLICY). The profile exists to establish
    the digitization context an outage episode interrupts.
    """

    country_iso3: str
    period: date
    vintage: date
    digital_payments: float | None
    health_expenditure: float | None
    missing_components: tuple[tuple[str, str], ...]


_VALID_KEYS = {"digital_payments", "health_expenditure"}


def build_profile(
    components: list[Component],
    country_iso3: str,
) -> PaymentProfile:
    """Assemble one (country, period, vintage) profile from components.

    All components must share one period and one vintage (one coherent
    snapshot). At least one lens component must be present; non-lens keys
    are ignored; duplicate keys are rejected.
    """
    valid = [c for c in components if c.key in _VALID_KEYS]
    if not valid:
        raise LensError(
            f"no RQ3 lens components among keys: {[c.key for c in components]}"
        )

    periods = {c.period for c in valid}
    if len(periods) > 1:
        raise LensError(f"components span multiple periods: {sorted(periods)}")

    vintages = {c.vintage for c in valid if c.vintage is not None}
    if len(vintages) > 1:
        raise LensError(
            f"components span multiple vintages: {sorted(vintages)}; "
            "build one profile per vintage instead"
        )

    keys = [c.key for c in valid]
    if len(keys) != len(set(keys)):
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        raise LensError(f"duplicate component keys: {dupes}")

    period = valid[0].period
    vint = vintages.pop() if vintages else period

    values: dict[str, tuple[float | None, str | None]] = {
        k: (None, None) for k in _VALID_KEYS
    }
    for c in valid:
        values[c.key] = (c.value, c.missing_reason)

    missing: list[tuple[str, str]] = []
    for key, (value, reason) in values.items():
        if value is None:
            missing.append((key, reason or "component_not_fetched"))

    return PaymentProfile(
        country_iso3=country_iso3,
        period=period,
        vintage=vint,
        digital_payments=values["digital_payments"][0],
        health_expenditure=values["health_expenditure"][0],
        missing_components=tuple(missing),
    )


def validate_lens_catalog() -> list[str]:
    """Consistency: lens indicators exist in the catalog with directions."""
    problems: list[str] = []
    for indicator_id in LENS_INDICATORS:
        match = next((i for i in CATALOG if i.indicator_id == indicator_id), None)
        if match is None:
            problems.append(f"indicator {indicator_id!r} is not in the catalog")
        elif match.direction != "higher_is_better":
            problems.append(
                f"indicator {indicator_id!r}: payment-lens indicators must be "
                f"higher_is_better, got {match.direction!r}"
            )
    return problems


__all__ = [
    "COMBINATION_POLICY",
    "LENS_INDICATORS",
    "Component",
    "LensError",
    "PaymentProfile",
    "build_profile",
    "validate_lens_catalog",
]
