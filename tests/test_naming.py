"""Tests for the display-naming layer (views.naming, second-round UI
refinement 2026-11-01).

The naming layer is presentation-only: short display names where the
meaning is unambiguous, readable units, and the full served name +
internal code preserved in the widget help. These tests pin (1) the
fallback discipline - an unknown id/token keeps its own words, never a
guessed abbreviation - and (2) catalog coverage - every catalog
indicator and unit token is deliberately curated, so adding one without
a naming decision fails here rather than rendering a raw field name.
"""

from __future__ import annotations

import pytest

from macropulse.catalog import CATALOG
from macropulse.views.naming import (
    SHORT_NAMES,
    TITLE_LINE_CHARS,
    UNIT_DISPLAY,
    display_name,
    indicator_help,
    option_label,
    unit_display,
    wrap_lines,
    wrap_title,
)

FULL_NAME = "Account ownership at a financial institution or mobile-money provider (% of adults)"


# --- unit tier ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("percent", "%"),
        ("percent_per_year", "% per year"),
        ("percent_per_annum", "% per annum"),
        ("percent_gross", "% gross"),
        ("percent_of_adults", "% of adults"),
        ("percent_of_gdp", "% of GDP"),
        ("per_100_people", "per 100 people"),
    ],
)
def test_unit_display_maps_catalog_tokens(token: str, expected: str) -> None:
    assert unit_display(token) == expected


def test_unit_display_unknown_token_falls_back_to_its_own_words() -> None:
    # never invent a unit: the fallback is the token's words, readable
    assert unit_display("widgets_per_capita") == "widgets per capita"


def test_unit_display_covers_every_catalog_unit() -> None:
    assert {entry.unit for entry in CATALOG} <= set(UNIT_DISPLAY)


# --- display-name tier -------------------------------------------------------------


def test_display_name_uses_curated_short_name() -> None:
    assert display_name("account_ownership_pct", FULL_NAME) == (
        "Account ownership (financial or mobile-money)"
    )


def test_display_name_falls_back_to_the_full_served_name() -> None:
    # an indicator without a curated short name keeps its FULL name -
    # a guessed abbreviation would be a claim about the series
    assert display_name("some_new_indicator", FULL_NAME) == FULL_NAME


def test_short_names_cover_every_catalog_indicator() -> None:
    # curated on purpose: adding a catalog indicator without a naming
    # decision must fail here, not silently render a raw field name
    assert {entry.indicator_id for entry in CATALOG} == set(SHORT_NAMES)


def test_short_names_never_contain_the_internal_code() -> None:
    for indicator_id, short in SHORT_NAMES.items():
        assert indicator_id not in short  # the code tier lives in help


# --- selector label ------------------------------------------------------------------


def test_option_label_composes_display_then_unit() -> None:
    assert option_label("account_ownership_pct", FULL_NAME, "percent_of_adults") == (
        "Account ownership (financial or mobile-money) · % of adults"
    )


def test_option_label_unknown_indicator_keeps_full_name_and_readable_unit() -> None:
    assert (
        option_label("x_new", FULL_NAME, "percent_of_gdp") == f"{FULL_NAME} · % of GDP"
    )


# --- help tooltip (tier 3: full name + code) ------------------------------------------


def test_indicator_help_lists_full_names_with_codes() -> None:
    help_text = indicator_help(
        [
            {"indicator_id": "account_ownership_pct", "name": FULL_NAME},
            {
                "indicator_id": "gdp_real_growth",
                "name": "Real GDP growth, annual % change",
            },
        ]
    )
    assert "`account_ownership_pct`" in help_text
    assert FULL_NAME in help_text
    assert "`gdp_real_growth`" in help_text
    assert "Real GDP growth, annual % change" in help_text


def test_indicator_help_empty_list_is_still_titled() -> None:
    assert indicator_help([]) == "**Full indicator names and codes**\n\n"


# --- title wrapping ----------------------------------------------------------------------


def test_wrap_title_short_title_unchanged() -> None:
    assert wrap_title("Real GDP growth") == "Real GDP growth"


def test_wrap_title_long_name_wraps_without_losing_words() -> None:
    wrapped = wrap_title(FULL_NAME)
    lines = wrapped.split("<br>")
    assert len(lines) > 1  # the 99-char full name cannot stay one line
    assert all(len(line) <= TITLE_LINE_CHARS for line in lines)
    assert " ".join(lines) == FULL_NAME  # every word, in order, no truncation


def test_wrap_title_lines_fit_the_narrowest_verified_viewport() -> None:
    # the longest curated display name wraps to two <=40-char lines, so
    # a 16px title line stays inside a 390px-wide plot
    wrapped = wrap_title("Account ownership (financial or mobile-money)")
    lines = wrapped.split("<br>")
    assert len(lines) == 2
    assert all(len(line) <= TITLE_LINE_CHARS for line in lines)


def test_wrap_title_never_breaks_mid_word() -> None:
    wrapped = wrap_title("Supercalifragilistic expialidocious " * 3)
    for line in wrapped.split("<br>"):
        for word in line.split():
            assert word.strip(",. ") in (
                "Supercalifragilistic",
                "expialidocious",
            )


def test_wrap_lines_overlong_word_sits_alone_not_split() -> None:
    # a word longer than the width overflows its line alone - splitting
    # it mid-word would corrupt the name
    assert wrap_lines("a verylongwordthatexceedsthewidth entirely", 10) == [
        "a",
        "verylongwordthatexceedsthewidth",
        "entirely",
    ]


def test_wrap_lines_empty_string_yields_one_empty_line() -> None:
    assert wrap_lines("", 30) == [""]
