"""Digital reach and inclusion gap lens (unit S11, RQ2).

RQ2: how do internet, mobile, and account-ownership rates co-vary with
income and gender across the panel, and where do measurement gaps hide
digital exclusion?

**Two dimensions** (the unit's objective, made explicit):

1. **Reach** - how far digital access extends: internet usage, mobile
   subscriptions, account ownership (levels, each with its own identity).
2. **Inclusion gaps** - who is left inside vs outside: the
   account-vs-internet gap (financial exclusion among the connected) and
   the gender account gap (female deficit).

Methodology follows S10's component-first pattern: no index, no composite
score, each component keeps its identity; relationships are explicit,
documented arithmetic; missingness is named, never imputed. Full
documentation: docs/DigitalLensMethodology.md.

Components:

- ``internet``    individuals using the Internet (% of population; WB
                  IT.NET.USER.ZS, ITU-sourced estimates)
- ``mobile``      mobile subscriptions per 100 people (WB
                  IT.CEL.SETS.P2; counts SIMs, not people)
- ``account``     account ownership (% of ADULTS; WB Findex
                  FX.OWN.TOTL.ZS, survey years only)
- ``account_female`` female account ownership (% of adults; WB Findex
                  FX.OWN.TOTL.FE.ZS - the catalog's account-ownership
                  fallback reference, repurposed here as the gender
                  dimension. NOT a catalog indicator of its own.)

Relationships:

- ``account_internet_gap``  account - internet, in pp. CAVEAT: the two
  series use different denominators (adults vs population) - a documented
  comparability limitation, reported as-is rather than adjusted.
- ``gender_account_gap``    account_female - account, in pp. Female vs
  the ALL-ADULT average (which includes women) - a conservative proxy:
  the proper female-minus-male gap needs the male series, which is not
  in the locked catalog. Negative = women below the national average.

Co-variation (income dimension): ``rank_covariation`` - Spearman rank
correlation across countries, descriptive only (no causality; small-n
caveat applies and n is always reported alongside).

Measurement gaps (the blind-spot half of RQ2):
``measurement_gap`` reports, per dimension, how many years since the last
observed value relative to a caller-supplied reference year (the lens is
pure - no clock reads). Never-observed dimensions are named explicitly.
Findex is survey-wave data (multi-year gaps by design) while internet
usage is annual - the gap map makes that asymmetry visible instead of
hiding it behind interpolated lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macropulse.catalog import CATALOG

# Lens components: catalog indicators plus the female Findex auxiliary
# (identified by source code, not a catalog indicator id).
LENS_INDICATORS = {
    "internet_users_pct": "internet",
    "mobile_subscriptions_per100": "mobile",
    "account_ownership_pct": "account",
}
# The female account series: the catalog's fallback reference for
# account_ownership_pct, used here as the gender component.
FEMALE_ACCOUNT_SOURCE = "FX.OWN.TOTL.FE.ZS"
FEMALE_ACCOUNT_KEY = "account_female"

# Relationship definitions recorded for methodology traceability.
RELATIONSHIPS: dict[str, str] = {
    "account_internet_gap": (
        "Account ownership (adults) minus internet usage (population), in "
        "percentage points. Financial exclusion among the connected. "
        "Denominators differ (adults vs population) - a documented "
        "comparability limitation, reported unadjusted."
    ),
    "gender_account_gap": (
        "Female account ownership minus all-adult account ownership, in "
        "percentage points. Conservative proxy for the female-male gap "
        "(the male series is not in the locked catalog; the all-adult "
        "average includes women, understating the female deficit). "
        "Negative = women below the national average."
    ),
}


class LensError(RuntimeError):
    """Raised when the lens is applied outside its rules."""


@dataclass(frozen=True)
class Component:
    """One digital series' value at one (period, vintage), identity kept."""

    key: str  # internet | mobile | account | account_female
    indicator_id: str | None  # catalog id when the component is an indicator
    source_code: str  # WB API code actually fetched
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
class DigitalProfile:
    """The two-dimensional RQ2 view for one (country, period, vintage).

    Dimension 1 (reach): internet, mobile, account - levels as observed.
    Dimension 2 (inclusion gaps): account_internet_gap,
    gender_account_gap - explicit arithmetic on present values.
    """

    country_iso3: str
    period: date
    vintage: date
    internet: float | None
    mobile: float | None
    account: float | None
    account_female: float | None
    missing_components: tuple[tuple[str, str], ...]

    @property
    def account_internet_gap(self) -> float | None:
        if self.account is None or self.internet is None:
            return None
        return self.account - self.internet

    @property
    def gender_account_gap(self) -> float | None:
        if self.account_female is None or self.account is None:
            return None
        return self.account_female - self.account


_VALID_KEYS = {"internet", "mobile", "account", "account_female"}


def build_profile(
    components: list[Component],
    country_iso3: str,
) -> DigitalProfile:
    """Assemble one (country, period, vintage) profile from components.

    All components must share one period and one vintage (one coherent
    snapshot). At least one lens component must be present; unknown keys
    are rejected.
    """
    valid = [c for c in components if c.key in _VALID_KEYS]
    if not valid:
        raise LensError(
            f"no RQ2 lens components among keys: {[c.key for c in components]}"
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

    # Duplicate keys would make value selection ambiguous.
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

    def value_of(key: str) -> tuple[float | None, str | None]:
        v, r = values[key]
        if v is None and r is None:
            return None, "component_not_fetched"
        return v, r

    internet, internet_reason = value_of("internet")
    mobile, mobile_reason = value_of("mobile")
    account, account_reason = value_of("account")
    account_female, female_reason = value_of("account_female")

    missing: list[tuple[str, str]] = []
    for name, value, reason in (
        ("internet", internet, internet_reason),
        ("mobile", mobile, mobile_reason),
        ("account", account, account_reason),
        ("account_female", account_female, female_reason),
    ):
        if value is None:
            missing.append((name, reason or "unknown"))

    return DigitalProfile(
        country_iso3=country_iso3,
        period=period,
        vintage=vint,
        internet=internet,
        mobile=mobile,
        account=account,
        account_female=account_female,
        missing_components=tuple(missing),
    )


# --- co-variation (income dimension) -----------------------------------------


def rank_covariation(xs: list[float], ys: list[float]) -> tuple[float, int]:
    """Spearman rank correlation between two same-length series.

    Ties share average ranks. Returns ``(coefficient, n)`` - n is ALWAYS
    reported because small panels (ours is 10) make the coefficient
    fragile, and reporting r without n would hide that. Descriptive
    measure of co-movement ONLY: no causal claim is licensed by a high
    coefficient (S01 non-claims).
    """
    if len(xs) != len(ys):
        raise ValueError("series must have the same length")
    n = len(xs)
    if n < 2:
        raise ValueError("rank covariation needs at least 2 points")

    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: values[i])
        rank_of: dict[int, float] = {}
        i = 0
        while i < n:
            j = i
            while j + 1 < n and values[order[j + 1]] == values[order[i]]:
                j += 1
            average = (i + 1 + j + 1) / 2  # ranks are 1-based
            for k in range(i, j + 1):
                rank_of[order[k]] = average
            i = j + 1
        return [rank_of[i] for i in range(n)]

    rx, ry = ranks(xs), ranks(ys)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    var_x = sum((a - mean_rx) ** 2 for a in rx)
    var_y = sum((b - mean_ry) ** 2 for b in ry)
    if var_x == 0 or var_y == 0:
        raise ValueError("rank covariation undefined for constant series")
    return cov / (var_x * var_y) ** 0.5, n


# --- measurement gaps (the blind-spot half of RQ2) -----------------------------


@dataclass(frozen=True)
class DimensionGap:
    """How stale one dimension's latest real observation is."""

    dimension: str
    last_observed: int | None  # year, None = never observed
    years_since: int | None  # as_of - last_observed; None if never

    @property
    def never_observed(self) -> bool:
        return self.last_observed is None


def measurement_gap(
    observed_years: dict[str, list[int]], as_of: int
) -> dict[str, DimensionGap]:
    """Years since each dimension's latest observation, per the caller's
    reference year (the lens is pure - no clock reads).

    ``observed_years``: dimension -> years with a real, non-missing value.
    This makes measurement asymmetries VISIBLE (e.g. Findex survey waves
    vs annual internet series) instead of hidden behind interpolated lines.
    """
    out: dict[str, DimensionGap] = {}
    for dimension, years in observed_years.items():
        if years:
            last = max(years)
            out[dimension] = DimensionGap(dimension, last, as_of - last)
        else:
            out[dimension] = DimensionGap(dimension, None, None)
    return out


def validate_lens_catalog() -> list[str]:
    """Consistency: lens indicators exist in the catalog with directions."""
    problems: list[str] = []
    for indicator_id in LENS_INDICATORS:
        match = next((i for i in CATALOG if i.indicator_id == indicator_id), None)
        if match is None:
            problems.append(f"indicator {indicator_id!r} is not in the catalog")
        elif match.direction != "higher_is_better":
            problems.append(
                f"indicator {indicator_id!r}: digital reach must be "
                f"higher_is_better, got {match.direction!r}"
            )
    return problems


__all__ = [
    "FEMALE_ACCOUNT_KEY",
    "FEMALE_ACCOUNT_SOURCE",
    "LENS_INDICATORS",
    "RELATIONSHIPS",
    "Component",
    "DigitalProfile",
    "DimensionGap",
    "LensError",
    "build_profile",
    "measurement_gap",
    "rank_covariation",
    "validate_lens_catalog",
]
