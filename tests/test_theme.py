"""S18 theme tests: the design-token layer for the editorial visual language.

Grouped as:

1. The palette itself - entity-fixed colors over exactly the S01 panel,
   with unknown countries rejected rather than defaulted.
2. Trace styling - focus vs context roles (color, width, legend).
3. Layout tokens - serif left-aligned title, transparent plot area,
   one axis.
4. Direct labels - last OBSERVED point only (gaps never labeled).
"""

from __future__ import annotations

import pytest

from macropulse.scope import COUNTRIES
from macropulse.views.theme import (
    CONTEXT_GREY,
    COUNTRY_COLORS,
    LINE_WIDTH_CONTEXT,
    LINE_WIDTH_FOCUS,
    country_color,
    focus_label_point,
    layout_update,
    series_style,
)

# --- the palette -----------------------------------------------------------------


def test_country_colors_cover_exactly_the_s01_panel() -> None:
    assert set(COUNTRY_COLORS) == {c.iso3 for c in COUNTRIES}
    assert len(COUNTRY_COLORS) == 10


def test_palette_has_ten_distinct_hues() -> None:
    # entity-fixed identity requires distinct tokens; a duplicate would
    # silently collide two economies
    assert len(set(COUNTRY_COLORS.values())) == 10


def test_color_is_entity_fixed_not_ranked() -> None:
    # The map is the single source of identity: the same country must
    # resolve to the same hue regardless of any selection context, and
    # the mapping follows the declared panel order (USA first).
    assert country_color("USA") == COUNTRY_COLORS["USA"]
    assert country_color("CHN") == COUNTRY_COLORS["CHN"]
    assert country_color("USA") != country_color("CHN")


@pytest.mark.parametrize("iso3", ["XYZ", "", "usa", "ZZ"])
def test_unknown_country_raises_rather_than_defaulting(iso3: str) -> None:
    # A silent default hue would fabricate identity for a non-panel series
    with pytest.raises(ValueError, match="no color token"):
        country_color(iso3)


# --- trace styling ----------------------------------------------------------------


def test_focus_series_wears_entity_color() -> None:
    style = series_style("JPN", focus=True)
    assert style["color"] == COUNTRY_COLORS["JPN"]
    assert style["width"] == LINE_WIDTH_FOCUS
    assert style["showlegend"] is True


def test_context_series_wears_grey_and_lighter_line() -> None:
    style = series_style("JPN", focus=False)
    assert style["color"] == CONTEXT_GREY != COUNTRY_COLORS["JPN"]
    assert style["width"] == LINE_WIDTH_CONTEXT
    assert style["width"] < LINE_WIDTH_FOCUS
    assert style["showlegend"] is False


# --- layout tokens -----------------------------------------------------------------


def test_layout_uses_serif_left_aligned_title_and_transparent_area() -> None:
    layout = layout_update("Real GDP growth", "percent")
    title = layout["title"]
    assert title["x"] == 0.01
    assert title["xanchor"] == "left"
    assert "Spectral" in title["font"]["family"]
    assert layout["paper_bgcolor"] == "rgba(0,0,0,0)"
    assert layout["plot_bgcolor"] == "rgba(0,0,0,0)"


def test_layout_has_exactly_one_axis() -> None:
    # one y-scale is a method rule, not a preference: the layout update
    # must never introduce a second axis
    layout = layout_update("t", "u")
    assert "yaxis" in layout and "xaxis" in layout
    assert not any(key.startswith("yaxis2") for key in layout)
    assert "overlaying" not in layout["yaxis"]


# --- direct labels -------------------------------------------------------------------


def test_focus_label_point_uses_last_observed_point() -> None:
    # a gap at the tail must not be labeled (a label on a missing point
    # would fabricate a data position)
    xs = ["2020", "2021", "2022"]
    ys: list[float | None] = [1.0, None, 3.0]
    assert focus_label_point(xs, ys) == ("2022", 3.0)


def test_focus_label_point_all_missing_returns_none() -> None:
    assert focus_label_point(["2020"], [None]) is None
    assert focus_label_point([], []) is None


def test_focus_label_point_rejects_mismatched_lengths() -> None:
    # strict zip only fires when the loop exhausts its inputs, so the
    # mismatch must not be maskable by an early observed point
    with pytest.raises(ValueError):
        focus_label_point([], [1.0])
    with pytest.raises(ValueError):
        focus_label_point(["2020"], [None, None])
