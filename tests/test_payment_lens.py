"""Tests for the payment resilience lens (S12, RQ3 profile half)."""

from datetime import date

import pytest

from macropulse.lenses.payment import (
    COMBINATION_POLICY,
    LENS_INDICATORS,
    Component,
    LensError,
    PaymentProfile,
    build_profile,
    validate_lens_catalog,
)

VINT = date(2026, 8, 29)


def comp(key, period, value, reason=None, vintage=VINT, indicator_id=None):
    indicator = (
        indicator_id
        or {
            "digital_payments": "digital_payments_made_pct",
            "health_expenditure": "health_expenditure_pct_gdp",
        }[key]
    )
    code = {
        "digital_payments": "g20.any",
        "health_expenditure": "SH.XPD.CHEX.GD.ZS",
    }[key]
    return Component(
        key=key,
        indicator_id=indicator,
        source_code=code,
        period=period,
        value=value,
        missing_reason=reason,
        vintage=vintage,
    )


# --- profile assembly ---------------------------------------------------------


def test_full_profile():
    profile = build_profile(
        [
            comp("digital_payments", date(2021, 1, 1), 86.0),
            comp("health_expenditure", date(2021, 1, 1), 5.4),
        ],
        "CHN",
    )
    assert profile.country_iso3 == "CHN"
    assert profile.digital_payments == 86.0
    assert profile.health_expenditure == 5.4
    assert profile.missing_components == ()
    assert profile.period == date(2021, 1, 1)
    assert profile.vintage == VINT


def test_partial_profile_names_missing_component():
    profile = build_profile(
        [
            comp("digital_payments", date(2021, 1, 1), 86.0),
            comp("health_expenditure", date(2021, 1, 1), None, "component_not_fetched"),
        ],
        "CHN",
    )
    assert profile.health_expenditure is None
    assert profile.missing_components == (
        ("health_expenditure", "component_not_fetched"),
    )


def test_unfetched_component_gets_named_reason():
    profile = build_profile(
        [comp("digital_payments", date(2021, 1, 1), 86.0)],
        "CHN",
    )
    assert profile.health_expenditure is None
    assert ("health_expenditure", "component_not_fetched") in profile.missing_components


def test_all_components_missing_still_builds():
    profile = build_profile(
        [
            comp("digital_payments", date(2021, 1, 1), None, "component_not_fetched"),
            comp("health_expenditure", date(2021, 1, 1), None, "component_not_fetched"),
        ],
        "CHN",
    )
    assert profile.digital_payments is None
    assert profile.health_expenditure is None
    assert len(profile.missing_components) == 2


def test_non_lens_keys_ignored():
    profile = build_profile(
        [
            comp("digital_payments", date(2021, 1, 1), 86.0),
            Component(
                key="cpi",
                indicator_id="cpi_inflation",
                source_code="CPIAUCSL",
                period=date(2021, 1, 1),
                value=5.0,
                missing_reason=None,
                vintage=VINT,
            ),
        ],
        "CHN",
    )
    assert profile.digital_payments == 86.0
    assert not hasattr(profile, "cpi")


# --- invalid assemblies -------------------------------------------------------


def test_no_lens_components_rejected():
    with pytest.raises(LensError):
        build_profile(
            [
                Component(
                    key="cpi",
                    indicator_id="cpi_inflation",
                    source_code="CPIAUCSL",
                    period=date(2021, 1, 1),
                    value=5.0,
                    missing_reason=None,
                    vintage=VINT,
                )
            ],
            "CHN",
        )


def test_multi_period_rejected():
    with pytest.raises(LensError, match="multiple periods"):
        build_profile(
            [
                comp("digital_payments", date(2021, 1, 1), 86.0),
                comp("health_expenditure", date(2022, 1, 1), 5.4),
            ],
            "CHN",
        )


def test_multi_vintage_rejected():
    with pytest.raises(LensError, match="multiple vintages"):
        build_profile(
            [
                comp("digital_payments", date(2021, 1, 1), 86.0),
                comp(
                    "health_expenditure",
                    date(2021, 1, 1),
                    5.4,
                    vintage=date(2025, 6, 1),
                ),
            ],
            "CHN",
        )


def test_duplicate_keys_rejected():
    with pytest.raises(LensError, match="duplicate"):
        build_profile(
            [
                comp("digital_payments", date(2021, 1, 1), 86.0),
                comp("digital_payments", date(2021, 1, 1), 90.0),
            ],
            "CHN",
        )


def test_missing_vintage_falls_back_to_period():
    profile = build_profile(
        [
            comp("digital_payments", date(2021, 1, 1), 86.0, vintage=None),
            comp("health_expenditure", date(2021, 1, 1), 5.4, vintage=None),
        ],
        "CHN",
    )
    assert profile.vintage == date(2021, 1, 1)


# --- component invariants -----------------------------------------------------


def test_null_requires_reason():
    with pytest.raises(ValueError, match="needs a reason"):
        comp("digital_payments", date(2021, 1, 1), None)


def test_value_must_not_carry_reason():
    with pytest.raises(ValueError, match="missing_reason"):
        comp("digital_payments", date(2021, 1, 1), 86.0, reason="input_missing")


# --- the no-relationship policy ------------------------------------------------


def test_no_derived_relationship_on_profile():
    """The lens defines NO arithmetic between payment prevalence and
    health spending (COMBINATION_POLICY). If a relationship property
    appears on the profile, the policy has silently drifted."""
    fields = set(PaymentProfile.__dataclass_fields__)
    assert fields == {
        "country_iso3",
        "period",
        "vintage",
        "digital_payments",
        "health_expenditure",
        "missing_components",
    }
    properties = {
        name
        for name, value in vars(PaymentProfile).items()
        if isinstance(value, property)
    }
    assert properties == set()  # levels only - no derived fields, no properties
    assert "no arithmetic relationship" in COMBINATION_POLICY


# --- catalog consistency --------------------------------------------------------


def test_lens_indicators_are_catalog_indicators():
    assert LENS_INDICATORS == {
        "digital_payments_made_pct": "digital_payments",
        "health_expenditure_pct_gdp": "health_expenditure",
    }


def test_validate_lens_catalog_clean():
    assert validate_lens_catalog() == []
