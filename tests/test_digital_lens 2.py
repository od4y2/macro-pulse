"""Tests for the S11 digital reach and inclusion gap lens (RQ2)."""

from __future__ import annotations

from datetime import date

import pytest

from macropulse.lenses.digital import (
    FEMALE_ACCOUNT_KEY,
    LENS_INDICATORS,
    RELATIONSHIPS,
    Component,
    DimensionGap,
    LensError,
    build_profile,
    measurement_gap,
    rank_covariation,
    validate_lens_catalog,
)

VINT = date(2024, 6, 1)


def comp(key, period, value, reason=None, vintage=VINT, source_code=None):
    code = (
        source_code
        or {
            "internet": "IT.NET.USER.ZS",
            "mobile": "IT.CEL.SETS.P2",
            "account": "FX.OWN.TOTL.ZS",
            "account_female": "FX.OWN.TOTL.FE.ZS",
        }[key]
    )
    indicator_id = {
        "internet": "internet_users_pct",
        "mobile": "mobile_subscriptions_per100",
        "account": "account_ownership_pct",
        "account_female": None,
    }[key]
    return Component(
        key=key,
        indicator_id=indicator_id,
        source_code=code,
        period=period,
        value=value,
        missing_reason=reason,
        vintage=vintage,
    )


# --- profile assembly: normal cases -------------------------------------------


def test_full_profile():
    components = [
        comp("internet", date(2023, 1, 1), 88.0),
        comp("mobile", date(2023, 1, 1), 110.0),
        comp("account", date(2023, 1, 1), 79.0),
        comp("account_female", date(2023, 1, 1), 74.0),
    ]
    p = build_profile(components, "USA")
    assert p.country_iso3 == "USA"
    assert p.period == date(2023, 1, 1)
    assert p.vintage == VINT
    assert p.internet == 88.0
    assert p.mobile == 110.0
    assert p.account == 79.0
    assert p.account_female == 74.0
    assert p.missing_components == ()


def test_relationships():
    p = build_profile(
        [
            comp("internet", date(2023, 1, 1), 88.0),
            comp("account", date(2023, 1, 1), 79.0),
            comp("account_female", date(2023, 1, 1), 74.0),
        ],
        "USA",
    )
    assert p.account_internet_gap == pytest.approx(-9.0)  # connected but excluded
    assert p.gender_account_gap == pytest.approx(-5.0)  # women below average


def test_gap_positive_directions():
    p = build_profile(
        [
            comp("internet", date(2023, 1, 1), 40.0),
            comp("account", date(2023, 1, 1), 55.0),
        ],
        "IND",
    )
    assert p.account_internet_gap == pytest.approx(15.0)


# --- missingness ------------------------------------------------------------------


def test_missing_component_named_not_imputed():
    p = build_profile(
        [
            comp("internet", date(2023, 1, 1), 88.0),
            comp("account", date(2023, 1, 1), None, "not_available"),
        ],
        "USA",
    )
    assert ("account", "not_available") in p.missing_components
    assert ("mobile", "component_not_fetched") in p.missing_components
    assert p.account_internet_gap is None  # never guessed
    assert p.gender_account_gap is None


def test_gender_gap_missing_without_female():
    p = build_profile(
        [
            comp("internet", date(2023, 1, 1), 88.0),
            comp("account", date(2023, 1, 1), 79.0),
        ],
        "USA",
    )
    assert p.gender_account_gap is None
    assert (FEMALE_ACCOUNT_KEY, "component_not_fetched") in p.missing_components


def test_component_invariants():
    with pytest.raises(ValueError, match="needs a reason"):
        comp("internet", date(2023, 1, 1), None, None)
    with pytest.raises(ValueError, match="both"):
        comp("internet", date(2023, 1, 1), 88.0, "stale")


# --- invalid cases -----------------------------------------------------------------


def test_no_lens_components_rejected():
    with pytest.raises(LensError, match="no RQ2 lens components"):
        build_profile([], "USA")


def test_unknown_keys_ignored_and_valid_required():
    # Unknown keys contribute nothing (cpi is not an RQ2 component).
    p = build_profile(
        [
            comp("internet", date(2023, 1, 1), 88.0),
            Component(
                key="cpi",
                indicator_id="cpi_inflation",
                source_code="CPI",
                period=date(2023, 1, 1),
                value=2.5,
                missing_reason=None,
                vintage=VINT,
            ),
        ],
        "USA",
    )
    assert p.internet == 88.0
    assert len(p.missing_components) == 3  # mobile, account, female unfetched


def test_multiple_periods_rejected():
    with pytest.raises(LensError, match="multiple periods"):
        build_profile(
            [
                comp("internet", date(2023, 1, 1), 88.0),
                comp("account", date(2022, 1, 1), 79.0),
            ],
            "USA",
        )


def test_multiple_vintages_rejected():
    with pytest.raises(LensError, match="multiple vintages"):
        build_profile(
            [
                comp("internet", date(2023, 1, 1), 88.0, vintage=VINT),
                comp("account", date(2023, 1, 1), 79.0, vintage=date(2025, 6, 1)),
            ],
            "USA",
        )


def test_duplicate_keys_rejected():
    with pytest.raises(LensError, match="duplicate component keys"):
        build_profile(
            [
                comp("internet", date(2023, 1, 1), 88.0),
                comp("internet", date(2023, 1, 1), 90.0),
            ],
            "USA",
        )


# --- rank covariation ----------------------------------------------------------------


def test_perfect_positive_covariation():
    r, n = rank_covariation([1.0, 2.0, 3.0, 4.0], [10.0, 20.0, 30.0, 40.0])
    assert r == pytest.approx(1.0)
    assert n == 4


def test_perfect_negative_covariation():
    r, n = rank_covariation([1.0, 2.0, 3.0, 4.0], [40.0, 30.0, 20.0, 10.0])
    assert r == pytest.approx(-1.0)
    assert n == 4


def test_mixed_covariation_value():
    # Hand-check: x=[1,2,3,4] ranks [1,2,3,4]; y=[2,1,4,3] ranks [2,1,4,3].
    r, n = rank_covariation([1.0, 2.0, 3.0, 4.0], [2.0, 1.0, 4.0, 3.0])
    assert r == pytest.approx(0.6)
    assert n == 4


def test_covariation_ties_share_average_ranks():
    # x has a tie (two 1.0s); Spearman with average ranks still lands in
    # [-1, 1] and is deterministic.
    r, n = rank_covariation([1.0, 1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0])
    assert -1.0 <= r <= 1.0
    assert n == 4


def test_covariation_is_scale_free():
    r1, _ = rank_covariation([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])
    r2, _ = rank_covariation([100.0, 200.0, 300.0], [0.1, 0.2, 0.3])
    assert r1 == pytest.approx(r2) == pytest.approx(1.0)


def test_covariation_length_mismatch_rejected():
    with pytest.raises(ValueError, match="same length"):
        rank_covariation([1.0, 2.0], [1.0, 2.0, 3.0])


def test_covariation_needs_two_points():
    with pytest.raises(ValueError, match="at least 2"):
        rank_covariation([1.0], [2.0])


def test_covariation_constant_series_rejected():
    with pytest.raises(ValueError, match="constant"):
        rank_covariation([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])


# --- measurement gaps ----------------------------------------------------------------


def test_measurement_gap_findex_vs_internet_asymmetry():
    gaps = measurement_gap(
        {
            "internet": [2015, 2016, 2023, 2024],
            "account": [2011, 2014, 2017, 2021, 2024],
        },
        as_of=2026,
    )
    assert gaps["internet"].last_observed == 2024
    assert gaps["internet"].years_since == 2
    assert gaps["account"].last_observed == 2024
    assert gaps["account"].years_since == 2


def test_measurement_gap_never_observed():
    gaps = measurement_gap({"internet": [2024], "account_female": []}, as_of=2026)
    assert gaps["account_female"].never_observed
    assert gaps["account_female"].last_observed is None
    assert gaps["account_female"].years_since is None


def test_measurement_gap_empty_map():
    assert measurement_gap({}, as_of=2026) == {}


def test_measurement_gap_dimension_frozen():
    g = DimensionGap("internet", 2024, 2)
    with pytest.raises(AttributeError):
        g.years_since = 0  # type: ignore[misc]


# --- catalog consistency ----------------------------------------------------------------


def test_lens_indicators_in_catalog_with_direction():
    assert validate_lens_catalog() == []


def test_lens_indicator_set():
    assert set(LENS_INDICATORS) == {
        "internet_users_pct",
        "mobile_subscriptions_per100",
        "account_ownership_pct",
    }


def test_relationship_definitions_exist():
    for name in ("account_internet_gap", "gender_account_gap"):
        assert name in RELATIONSHIPS
        assert len(RELATIONSHIPS[name]) > 40
