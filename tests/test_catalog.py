"""Tests for the indicator catalog and source audit (unit S02)."""

import pytest

from macropulse import catalog
from macropulse.catalog import CATALOG, Indicator, SourceRef, validate_catalog
from macropulse.catalog_report import render_report
from macropulse.scope import MODULES

# --- Normal cases -----------------------------------------------------------

def test_catalog_validates_cleanly() -> None:
    assert validate_catalog() == []


def test_every_module_has_coverage() -> None:
    covered = {i.module for i in CATALOG}
    # vintage-transparency (RQ4) has no standalone indicators by design: it is
    # realized through provenance fields on every observation and the release
    # calendar built in S07, not through its own data series.
    assert covered == set(MODULES) - {"vintage-transparency"}
    assert "vintage-transparency" not in covered


def test_required_rq1_rq2_indicators_present() -> None:
    ids = {i.indicator_id for i in CATALOG}
    # RQ1 labor slack and youth transition
    assert {"youth_unemployment_rate", "neet_rate"} <= ids
    # RQ2 digital reach and inclusion
    assert {"internet_users_pct", "mobile_subscriptions_per100", "account_ownership_pct"} <= ids


def test_report_renders_and_flags_unverified() -> None:
    report = render_report()
    assert "MacroPulse indicator catalog" in report
    assert "awaiting live verification" in report
    n_unverified = len(catalog.indicators_needing_verification())
    assert n_unverified > 0  # honesty: we know some codes are unverified
    assert f"(S04/S05): {n_unverified}" in report


# --- Boundary cases ----------------------------------------------------------

def test_source_codes_have_no_whitespace() -> None:
    for ind in CATALOG:
        for ref in (ind.primary_source, ind.fallback_source):
            if ref is not None:
                assert not any(ch.isspace() for ch in ref.code)


def test_unverified_codes_exist_and_are_counted() -> None:
    pairs = catalog.indicators_needing_verification()
    assert all(code for _, code in pairs)
    for ind_id, code in pairs:
        ind = next(i for i in CATALOG if i.indicator_id == ind_id)
        refs = [r for r in (ind.primary_source, ind.fallback_source) if r]
        assert any(r.code == code and r.verified == "unverified" for r in refs)


# --- Missing cases -----------------------------------------------------------

def test_missing_fallback_source_rejected_when_status_requires_it() -> None:
    original = catalog.CATALOG
    ind = original[0]
    try:
        catalog.CATALOG = (
            Indicator(
                indicator_id=ind.indicator_id, name=ind.name, module=ind.module,
                unit=ind.unit, frequency=ind.frequency,
                seasonal_adjustment=ind.seasonal_adjustment,
                primary_source=ind.primary_source,
                fallback_source=None,
                fallback_status="primary-and-fallback",
                comparability_notes=ind.comparability_notes,
                limitations=ind.limitations,
            ),
        )
        assert any("requires a fallback_source" in p for p in validate_catalog())
    finally:
        catalog.CATALOG = original


def test_missing_notes_rejected() -> None:
    original = catalog.CATALOG
    ind = original[0]
    try:
        catalog.CATALOG = (
            Indicator(
                indicator_id=ind.indicator_id, name=ind.name, module=ind.module,
                unit=ind.unit, frequency=ind.frequency,
                seasonal_adjustment=ind.seasonal_adjustment,
                primary_source=ind.primary_source,
                fallback_source=ind.fallback_source,
                fallback_status=ind.fallback_status,
                comparability_notes="",
                limitations=ind.limitations,
            ),
        )
        assert any("comparability, or limitations missing" in p for p in validate_catalog())
    finally:
        catalog.CATALOG = original


# --- Invalid cases -----------------------------------------------------------

def test_unknown_module_rejected() -> None:
    original = catalog.CATALOG
    ind = original[0]
    try:
        catalog.CATALOG = (
            Indicator(
                indicator_id=ind.indicator_id, name=ind.name, module="does-not-exist",
                unit=ind.unit, frequency=ind.frequency,
                seasonal_adjustment=ind.seasonal_adjustment,
                primary_source=ind.primary_source,
                fallback_source=ind.fallback_source,
                fallback_status=ind.fallback_status,
                comparability_notes=ind.comparability_notes,
                limitations=ind.limitations,
            ),
        )
        assert any("unknown module" in p for p in validate_catalog())
    finally:
        catalog.CATALOG = original


@pytest.mark.parametrize("bad_status", ["maybe", "", "CONFIRMED"])
def test_invalid_verification_status_rejected(bad_status: str) -> None:
    original = catalog.CATALOG
    ind = original[0]
    try:
        catalog.CATALOG = (
            Indicator(
                indicator_id=ind.indicator_id, name=ind.name, module=ind.module,
                unit=ind.unit, frequency=ind.frequency,
                seasonal_adjustment=ind.seasonal_adjustment,
                primary_source=SourceRef(
                    system="world_bank", code="X.Y.Z", verified=bad_status,
                    coverage="c",
                ),
                fallback_source=ind.fallback_source,
                fallback_status=ind.fallback_status,
                comparability_notes=ind.comparability_notes,
                limitations=ind.limitations,
            ),
        )
        assert any("invalid verification status" in p for p in validate_catalog())
    finally:
        catalog.CATALOG = original


def test_annotated_source_code_rejected() -> None:
    original = catalog.CATALOG
    ind = original[0]
    try:
        catalog.CATALOG = (
            Indicator(
                indicator_id=ind.indicator_id, name=ind.name, module=ind.module,
                unit=ind.unit, frequency=ind.frequency,
                seasonal_adjustment=ind.seasonal_adjustment,
                primary_source=SourceRef(
                    system="world_bank", code="NY.GDP.MKTP.KD.ZG (note)",
                    verified="confirmed", coverage="c",
                ),
                fallback_source=ind.fallback_source,
                fallback_status=ind.fallback_status,
                comparability_notes=ind.comparability_notes,
                limitations=ind.limitations,
            ),
        )
        assert any("contains whitespace" in p for p in validate_catalog())
    finally:
        catalog.CATALOG = original


def test_duplicate_indicator_ids_rejected() -> None:
    original = catalog.CATALOG
    try:
        catalog.CATALOG = original + (original[0],)
        assert any("duplicate indicator ids" in p for p in validate_catalog())
    finally:
        catalog.CATALOG = original
