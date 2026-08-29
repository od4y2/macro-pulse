"""Tests for the S10 labor slack and youth transition lens (RQ1)."""

from __future__ import annotations

from datetime import date

import pytest

from macropulse.lenses.labor import (
    LENS_INDICATORS,
    RELATIONSHIPS,
    Component,
    LensError,
    SlackProfile,
    build_profile,
    divergence_by_vintage,
    validate_lens_catalog,
    youth_headline_gap_series,
)

VINT = date(2024, 6, 1)


def comp(indicator_id, period, value, reason=None, vintage=VINT):
    return Component(
        indicator_id=indicator_id, period=period, value=value,
        missing_reason=reason, vintage=vintage,
    )


# --- profile assembly: normal cases -------------------------------------------


def test_full_profile():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 4.0),
        comp("youth_unemployment_rate", date(2023, 1, 1), 9.0),
        comp("neet_rate", date(2023, 1, 1), 12.0),
        comp("tertiary_enrollment", date(2023, 1, 1), 62.0),
    ]
    p = build_profile(components, "USA")
    assert p.country_iso3 == "USA"
    assert p.period == date(2023, 1, 1)
    assert p.vintage == VINT
    assert p.headline == 4.0
    assert p.youth == 9.0
    assert p.neet == 12.0
    assert p.enrollment == 62.0
    assert p.missing_components == ()


def test_profile_relationships():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 4.0),
        comp("youth_unemployment_rate", date(2023, 1, 1), 9.0),
        comp("neet_rate", date(2023, 1, 1), 12.0),
    ]
    p = build_profile(components, "USA")
    assert p.youth_headline_gap == pytest.approx(5.0)  # youth worse by 5pp
    assert p.youth_ratio == pytest.approx(2.25)
    assert p.neet_minus_unemployed == pytest.approx(8.0)  # withdrawal excess


def test_gap_negative_when_youth_fare_better():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 12.0),
        comp("youth_unemployment_rate", date(2023, 1, 1), 9.0),
    ]
    p = build_profile(components, "DEU")
    assert p.youth_headline_gap == pytest.approx(-3.0)
    assert p.youth_ratio == pytest.approx(0.75)


def test_ratio_is_none_when_headline_zero():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 0.0),
        comp("youth_unemployment_rate", date(2023, 1, 1), 2.0),
    ]
    p = build_profile(components, "USA")
    assert p.youth_ratio is None  # 2/0 is not fabricated
    assert p.youth_headline_gap == pytest.approx(2.0)  # gap still defined


# --- missingness ----------------------------------------------------------------


def test_missing_component_is_named_not_imputed():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 4.0),
        comp("youth_unemployment_rate", date(2023, 1, 1), None, "not_available"),
    ]
    p = build_profile(components, "USA")
    assert p.youth is None
    assert ("youth", "not_available") in p.missing_components
    # Relationships depending on the missing component are None, never guessed.
    assert p.youth_headline_gap is None
    assert p.youth_ratio is None
    # neet/enrollment were not fetched at all.
    assert ("neet", "component_not_fetched") in p.missing_components
    assert ("enrollment", "component_not_fetched") in p.missing_components
    # Headline-side relationships still compute.
    assert p.neet_minus_unemployed is None  # neet also missing


def test_relationships_missing_when_neet_missing():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 4.0),
        comp("neet_rate", date(2023, 1, 1), None, "not_available"),
    ]
    p = build_profile(components, "USA")
    assert p.neet_minus_unemployed is None


def test_component_invariants_enforced():
    with pytest.raises(ValueError, match="needs a reason"):
        Component("unemployment_rate", date(2023, 1, 1), None, None)
    with pytest.raises(ValueError, match="both"):
        Component("unemployment_rate", date(2023, 1, 1), 4.0, "stale")


# --- invalid cases ---------------------------------------------------------------


def test_non_lens_components_are_ignored():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 4.0),
        comp("cpi_inflation", date(2023, 1, 1), 2.5),
    ]
    p = build_profile(components, "USA")
    assert p.headline == 4.0
    # cpi contributes nothing to the lens profile.
    assert p.missing_components == (
        ("youth", "component_not_fetched"),
        ("neet", "component_not_fetched"),
        ("enrollment", "component_not_fetched"),
    )


def test_no_lens_indicators_rejected():
    components = [
        comp("cpi_inflation", date(2023, 1, 1), 2.5),
    ]
    with pytest.raises(LensError, match="no RQ1 lens indicators"):
        build_profile(components, "USA")


def test_multiple_periods_rejected():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 4.0),
        comp("youth_unemployment_rate", date(2022, 1, 1), 9.0),
    ]
    with pytest.raises(LensError, match="multiple periods"):
        build_profile(components, "USA")


def test_multiple_vintages_rejected():
    components = [
        comp("unemployment_rate", date(2023, 1, 1), 4.0, vintage=VINT),
        comp("youth_unemployment_rate", date(2023, 1, 1), 9.0,
             vintage=date(2025, 6, 1)),
    ]
    with pytest.raises(LensError, match="multiple vintages"):
        build_profile(components, "USA")


def test_no_vintage_falls_back_to_period():
    components = [
        Component("unemployment_rate", date(2023, 1, 1), 4.0, None, None),
    ]
    p = build_profile(components, "USA")
    assert p.vintage == date(2023, 1, 1)


# --- youth-headline gap series -----------------------------------------------------


def test_gap_series_computes_both_present_periods():
    headline = {date(2022, 1, 1): 4.0, date(2023, 1, 1): 3.5, date(2024, 1, 1): 3.8}
    youth = {date(2022, 1, 1): 8.0, date(2023, 1, 1): 7.0}
    out = youth_headline_gap_series(headline, youth)
    assert out[date(2022, 1, 1)] == pytest.approx(4.0)
    assert out[date(2023, 1, 1)] == pytest.approx(3.5)
    assert out[date(2024, 1, 1)] is None  # youth missing -> explicit None


def test_gap_series_empty_inputs():
    assert youth_headline_gap_series({}, {}) == {}


# --- divergence by vintage (RQ1's vintage question) --------------------------------


def _profile(period, vintage, headline, youth):
    components = [
        comp("unemployment_rate", period, headline, vintage=vintage),
        comp("youth_unemployment_rate", period, youth, vintage=vintage),
    ]
    return build_profile(components, "USA")


def test_divergence_revised_across_vintages():
    profiles = [
        _profile(date(2023, 1, 1), date(2023, 6, 1), 4.0, 9.0),   # gap 5.0
        _profile(date(2023, 1, 1), date(2024, 6, 1), 4.1, 9.3),   # gap 5.2
        _profile(date(2024, 1, 1), date(2024, 6, 1), 3.8, 8.0),   # gap 4.2
    ]
    out = divergence_by_vintage(profiles)
    assert out == {
        date(2023, 1, 1): [pytest.approx(5.0), pytest.approx(5.2)],
        date(2024, 1, 1): [pytest.approx(4.2)],
    }


def test_divergence_skips_profiles_without_gap():
    profiles = [
        _profile(date(2023, 1, 1), VINT, 4.0, 9.0),
        # headline missing -> no gap -> skipped, not imputed
        build_profile(
            [comp("youth_unemployment_rate", date(2023, 1, 1), 9.0)], "USA"
        ),
    ]
    out = divergence_by_vintage(profiles)
    assert out == {date(2023, 1, 1): [pytest.approx(5.0)]}


def test_divergence_empty():
    assert divergence_by_vintage([]) == {}


# --- catalog consistency ------------------------------------------------------------


def test_lens_indicators_all_in_catalog_with_direction():
    problems = validate_lens_catalog()
    assert problems == []


def test_relationship_definitions_exist():
    for name in ("youth_headline_gap", "youth_ratio", "neet_minus_unemployed"):
        assert name in RELATIONSHIPS
        assert len(RELATIONSHIPS[name]) > 40


def test_lens_indicator_set():
    assert set(LENS_INDICATORS) == {
        "unemployment_rate",
        "youth_unemployment_rate",
        "neet_rate",
        "tertiary_enrollment",
    }


def test_enrollment_is_reported_not_combined():
    # The component-first rule: enrollment enters the profile as a reported
    # component with its own identity; no lens relationship consumes it
    # (composition vs welfare separation).
    p = SlackProfile(
        country_iso3="USA", period=date(2023, 1, 1), vintage=VINT,
        headline=4.0, youth=9.0, neet=12.0, enrollment=62.0,
        missing_components=(),
    )
    # Only the three documented relationships exist on the profile.
    relationships = {
        "youth_headline_gap", "youth_ratio", "neet_minus_unemployed",
    }
    properties = {
        name for name in dir(p) if not name.startswith("_") and name not in {
            "country_iso3", "period", "vintage", "headline", "youth", "neet",
            "enrollment", "missing_components",
        }
    }
    assert properties == relationships
