"""Indicator catalog and source audit (unit S02).

Defines the indicators MacroPulse will collect, with units, frequency,
source references, comparability notes, and fallback status. The catalog is
metadata only: it contains no observation values.

Source-code honesty rules:
- ``verified="confirmed"`` means the code is a long-established, widely
  documented series identifier. Even so, live retrieval in S04/S05 remains
  the authoritative check.
- ``verified="unverified"`` means the code is believed correct but must be
  confirmed against the live API during connector units before use in
  production pipelines.
"""

from __future__ import annotations

from typing import NamedTuple

SOURCE_SYSTEMS = ("fred", "world_bank", "ilostat")

FREQUENCIES = ("monthly", "quarterly", "annual")

SEASONAL_ADJUSTMENTS = ("seasonally_adjusted", "not_seasonally_adjusted", "varies")

VERIFICATION_STATUSES = ("confirmed", "unverified")

FALLBACK_STATUSES = (
    "primary-and-fallback",  # a fallback source is defined
    "primary-only",  # no acceptable fallback source yet
    "case-study-reserve",  # sourcing deferred to the S12 case study
)


class SourceRef(NamedTuple):
    system: str  # one of SOURCE_SYSTEMS
    code: str  # series/indicator identifier in that system
    verified: str  # one of VERIFICATION_STATUSES
    coverage: str  # which economies/periods this source covers


class Indicator(NamedTuple):
    indicator_id: str
    name: str
    module: str  # must match scope.MODULES
    unit: str
    frequency: str  # primary frequency; one of FREQUENCIES
    seasonal_adjustment: str
    primary_source: SourceRef
    fallback_source: SourceRef | None
    fallback_status: str  # one of FALLBACK_STATUSES
    comparability_notes: str
    limitations: str


CATALOG: tuple[Indicator, ...] = (
    # --- traditional-indicators -------------------------------------------
    Indicator(
        indicator_id="gdp_real_growth",
        name="Real GDP growth (annual %)",
        module="traditional-indicators",
        unit="percent_per_year",
        frequency="annual",
        seasonal_adjustment="varies",
        primary_source=SourceRef(
            system="world_bank",
            code="NY.GDP.MKTP.KD.ZG",
            verified="confirmed",
            coverage="All ten panel economies; annual; WB national-accounts rebasing caveats apply",
        ),
        fallback_source=SourceRef(
            system="fred",
            code="CLVMNACSCAB1GQDE",
            verified="confirmed",
            coverage="Germany only (Eurostat via FRED, quarterly SA); other economies lack usable FRED GDP mirrors (verified live 2026-08-19)",
        ),
        fallback_status="primary-and-fallback",
        comparability_notes=(
            "WB series are rebased periodically; growth rates for China follow "
            "national methodology and are not strictly comparable with SNA-default economies"
        ),
        limitations=(
            "Annual frequency hides intra-year dynamics; vintage revisions are large "
            "for recent years and must be preserved (see RQ4)"
        ),
    ),
    Indicator(
        indicator_id="cpi_inflation",
        name="Consumer price inflation (annual %)",
        module="traditional-indicators",
        unit="percent_per_year",
        frequency="annual",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="world_bank",
            code="FP.CPI.TOTL.ZG",
            verified="confirmed",
            coverage="All ten panel economies; annual",
        ),
        fallback_source=SourceRef(
            system="fred",
            code="CPIAUCSL",
            verified="confirmed",
            coverage="United States only; monthly, seasonally adjusted index (YoY derived)",
        ),
        fallback_status="primary-and-fallback",
        comparability_notes=(
            "WB annual inflation vs FRED monthly SA index-derived YoY are not "
            "interchangeable; label the source on every observation"
        ),
        limitations="CPI basket composition differs across economies; weights revise infrequently",
    ),
    Indicator(
        indicator_id="unemployment_rate",
        name="Unemployment rate, total (% of labor force)",
        module="traditional-indicators",
        unit="percent",
        frequency="annual",
        seasonal_adjustment="varies",
        primary_source=SourceRef(
            system="world_bank",
            code="SL.UEM.TOTL.ZS",
            verified="confirmed",
            coverage="All ten panel economies; ILO-modeled estimates, annual",
        ),
        fallback_source=SourceRef(
            system="fred",
            code="UNRATE",
            verified="confirmed",
            coverage="United States only; monthly, seasonally adjusted (BLS household survey)",
        ),
        fallback_status="primary-and-fallback",
        comparability_notes=(
            "ILO-modeled estimates harmonize definitions but lag national releases; "
            "national series (e.g., BLS UNRATE) differ in scope and timing"
        ),
        limitations=(
            "Headline unemployment hides slack captured by RQ1 lenses; modeled "
            "estimates smooth breaks in national methodology"
        ),
    ),
    # --- labor-slack-youth (RQ1) --------------------------------------------
    Indicator(
        indicator_id="youth_unemployment_rate",
        name="Youth unemployment rate, ages 15-24 (% of labor force)",
        module="labor-slack-youth",
        unit="percent",
        frequency="annual",
        seasonal_adjustment="varies",
        primary_source=SourceRef(
            system="world_bank",
            code="SL.UEM.1524.ZS",
            verified="confirmed",
            coverage="All ten panel economies; ILO-modeled estimates, annual",
        ),
        fallback_source=SourceRef(
            system="ilostat",
            code="DF_SDG_0852_SEX_AGE_RT",
            verified="confirmed",
            coverage="ILOSTAT SDMX 8.5.2 unemployment rate by sex and age; filter SEX_T and the 15-24 age dimension",
        ),
        fallback_status="primary-and-fallback",
        comparability_notes=(
            "Age-band definitions (15-24 vs 16-24) differ between ILO harmonization "
            "and national releases (e.g., US BLS uses 16-24)"
        ),
        limitations="Small labor-force denominator at country/age level makes rates volatile",
    ),
    Indicator(
        indicator_id="neet_rate",
        name="Youth not in education, employment or training (NEET, % of youth)",
        module="labor-slack-youth",
        unit="percent",
        frequency="annual",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="world_bank",
            code="SL.UEM.NEET.ZS",
            verified="confirmed",
            coverage="All ten panel economies; annual; sparse for some economies (verified live 2026-08-19)",
        ),
        fallback_source=SourceRef(
            system="ilostat",
            code="DF_EIP_NEET_SEX_RT",
            verified="confirmed",
            coverage="ILOSTAT SDMX NEET rate by sex (EIP); filter SEX_T (verified live 2026-08-19)",
        ),
        fallback_status="primary-and-fallback",
        comparability_notes=(
            "NEET definitions (age band, education enrollment reference week) vary; "
            "verify exact code and definition in S05 before cross-country use"
        ),
        limitations="Very sparse in parts of the panel; missingness must be surfaced, not imputed silently",
    ),
    Indicator(
        indicator_id="tertiary_enrollment",
        name="School enrollment, tertiary (% gross)",
        module="labor-slack-youth",
        unit="percent_gross",
        frequency="annual",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="world_bank",
            code="SE.TER.ENRR",
            verified="confirmed",
            coverage="All ten panel economies; annual; UIS-sourced with lags",
        ),
        fallback_source=None,
        fallback_status="primary-only",
        comparability_notes="Gross enrollment can exceed 100% due to over-age participation",
        limitations="Reporting lags of 1-2 years are common; not a real-time transition signal",
    ),
    # --- digital-inclusion (RQ2) --------------------------------------------
    Indicator(
        indicator_id="internet_users_pct",
        name="Individuals using the Internet (% of population)",
        module="digital-inclusion",
        unit="percent",
        frequency="annual",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="world_bank",
            code="IT.NET.USER.ZS",
            verified="confirmed",
            coverage="All ten panel economies; annual; ITU-sourced",
        ),
        fallback_source=None,
        fallback_status="primary-only",
        comparability_notes="ITU estimates; survey questions and reference years differ across economies",
        limitations="No monthly frequency; urban/rural and gender gaps require linked series (see S11)",
    ),
    Indicator(
        indicator_id="mobile_subscriptions_per100",
        name="Mobile cellular subscriptions (per 100 people)",
        module="digital-inclusion",
        unit="per_100_people",
        frequency="annual",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="world_bank",
            code="IT.CEL.SETS.P2",
            verified="confirmed",
            coverage="All ten panel economies; annual",
        ),
        fallback_source=None,
        fallback_status="primary-only",
        comparability_notes="Counts subscriptions, not people; multiple-SIM ownership inflates values above 100",
        limitations="Weak proxy for individual access; use only alongside usage series",
    ),
    Indicator(
        indicator_id="account_ownership_pct",
        name="Account ownership at a financial institution or mobile-money provider (% of adults)",
        module="digital-inclusion",
        unit="percent_of_adults",
        frequency="annual",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="world_bank",
            code="FX.OWN.TOTL.ZS",
            verified="confirmed",
            coverage="Global Findex survey years only (2011/2014/2017/2021/2025 waves; verified live 2026-08-19)",
        ),
        fallback_source=SourceRef(
            system="world_bank",
            code="FX.OWN.TOTL.FE.ZS",
            verified="confirmed",
            coverage="Female variant for the gender gap; same survey years (verified live 2026-08-19)",
        ),
        fallback_status="primary-and-fallback",
        comparability_notes=(
            "Findex is survey-based and triennial; interpolation across survey years "
            "must be labelled synthetic if ever used"
        ),
        limitations="Survey years only - large temporal gaps by design; no intra-period readings",
    ),
    # --- payment-resilience-healthcare (RQ3) --------------------------------
    Indicator(
        indicator_id="digital_payments_made_pct",
        name="Made or received digital payments in the past year (% of adults)",
        module="payment-resilience-healthcare",
        unit="percent_of_adults",
        frequency="annual",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="world_bank",
            code="g20.any",
            verified="confirmed",
            coverage="Global Findex 'Made or received a digital payment (% age 15+)'; survey years only (verified live 2026-08-19)",
        ),
        fallback_source=None,
        fallback_status="case-study-reserve",
        comparability_notes="Findex survey-based; measurement of 'digital payment' changed between waves",
        limitations="Case-study sourcing (episodes, national sources) is defined in S12",
    ),
    Indicator(
        indicator_id="health_expenditure_pct_gdp",
        name="Current health expenditure (% of GDP)",
        module="payment-resilience-healthcare",
        unit="percent_of_gdp",
        frequency="annual",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="world_bank",
            code="SH.XPD.CHEX.GD.ZS",
            verified="confirmed",
            coverage="All ten panel economies; annual; WHO-sourced",
        ),
        fallback_source=None,
        fallback_status="primary-only",
        comparability_notes="WHO national health accounts methodology; breaks at methodology changes",
        limitations="Macro context for the case study only; not a resilience measure itself",
    ),
    # --- vintage-transparency (RQ4, metadata-side) ---------------------------
    Indicator(
        indicator_id="policy_rate",
        name="Short-term policy/interest rate (%, end-of-period or daily)",
        module="traditional-indicators",
        unit="percent_per_annum",
        frequency="monthly",
        seasonal_adjustment="not_seasonally_adjusted",
        primary_source=SourceRef(
            system="fred",
            code="FEDFUNDS",
            verified="confirmed",
            coverage="United States; other panel economies need FRED mirrors or central-bank sources (S04/S05 audit)",
        ),
        fallback_source=None,
        fallback_status="primary-only",
        comparability_notes=(
            "Policy instruments differ (corridor vs floor systems); cross-country "
            "comparability is limited and must be stated"
        ),
        limitations="Coverage outside the US is a known gap; resolve during S04/S05 audits",
    ),
)


def validate_catalog() -> list[str]:
    """Return a list of catalog violations; empty means the catalog is valid."""
    from macropulse.scope import MODULES  # local import to avoid cycles

    problems: list[str] = []

    ids = [i.indicator_id for i in CATALOG]
    if len(ids) != len(set(ids)):
        problems.append("duplicate indicator ids")
    if len(CATALOG) == 0:
        problems.append("catalog is empty")

    for ind in CATALOG:
        if ind.module not in MODULES:
            problems.append(f"{ind.indicator_id}: unknown module {ind.module!r}")
        if ind.frequency not in FREQUENCIES:
            problems.append(f"{ind.indicator_id}: invalid frequency {ind.frequency!r}")
        if ind.seasonal_adjustment not in SEASONAL_ADJUSTMENTS:
            problems.append(
                f"{ind.indicator_id}: invalid seasonal_adjustment {ind.seasonal_adjustment!r}"
            )
        if ind.fallback_status not in FALLBACK_STATUSES:
            problems.append(
                f"{ind.indicator_id}: invalid fallback_status {ind.fallback_status!r}"
            )
        if not ind.unit or not ind.comparability_notes or not ind.limitations:
            problems.append(f"{ind.indicator_id}: unit, comparability, or limitations missing")

        for ref in (ind.primary_source, ind.fallback_source):
            if ref is None:
                continue
            if ref.system not in SOURCE_SYSTEMS:
                problems.append(f"{ind.indicator_id}: unknown source system {ref.system!r}")
            if ref.verified not in VERIFICATION_STATUSES:
                problems.append(
                    f"{ind.indicator_id}: invalid verification status {ref.verified!r}"
                )
            if not ref.code or not ref.coverage:
                problems.append(f"{ind.indicator_id}: source ref missing code or coverage")
            if any(ch.isspace() for ch in ref.code):
                problems.append(
                    f"{ind.indicator_id}: source code {ref.code!r} contains whitespace "
                    "(notes belong in coverage)"
                )

        if ind.fallback_status == "primary-and-fallback" and ind.fallback_source is None:
            problems.append(f"{ind.indicator_id}: fallback_status requires a fallback_source")
        if ind.fallback_status == "primary-only" and ind.fallback_source is not None:
            problems.append(f"{ind.indicator_id}: primary-only must not define a fallback_source")

    return problems


def indicators_needing_verification() -> list[tuple[str, str]]:
    """Return (indicator_id, code) pairs still marked unverified."""
    pairs: list[tuple[str, str]] = []
    for ind in CATALOG:
        for ref in (ind.primary_source, ind.fallback_source):
            if ref is not None and ref.verified == "unverified":
                pairs.append((ind.indicator_id, ref.code))
    return pairs
