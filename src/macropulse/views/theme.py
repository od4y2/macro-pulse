"""Design tokens for MacroPulse charts and dashboard chrome (unit S18).

A muted editorial palette and typography, REFERENCED to the modern
professional look-and-feel of financial-press data journalism (user
directive, 2026-09-18) but not a clone of any publication's trade dress:
the hues below are MacroPulse's own, chosen and validated with the
computed colorblind-safety method (validate_palette.js; output recorded
verbatim in ``evidence/S18/palette-validation.txt``), not eyeballed.

Governance rules carried here:

- **Entity-fixed color.** A country's color never depends on what else
  is selected: ``COUNTRY_COLORS`` is a fixed map over the S01 panel, so
  a filter change can never repaint a surviving series (color follows
  the entity, never its rank).
- **Focus-and-context display.** At most ONE series on a chart renders
  in its entity color (the focus); every other series wears
  ``CONTEXT_GREY``. This is why a 10-economy comparison never puts ten
  hues on screen - the known anti-pattern for categorical color - and
  why two countries may share a hue family (CHN teal / MEX teal-light):
  colored marks are never simultaneous, and identity for context series
  travels by hover provenance and the comparison matrix table, not hue.
- **Relief rule (validator WARNs are honored, not waved off).** The
  palette passes with two floor-band WARNs - MEX green vs BRA amber
  protan DeltaE 7.7 (floor band 6-8), and sub-3:1 surface contrast for
  BRA amber / MEX teal-light. Both are legal ONLY because every chart
  ships secondary encoding: a direct label or legend plus the
  value-matrix table, and only one colored line renders at a time.
- **Text wears ink, not series colors** (labels/legends/ticks stay in
  the ink tokens below; the colored mark carries the identity).

Light mode only, by decision: the dashboard pins Streamlit to a light
theme (``.streamlit/config.toml``), so no dark palette is shipped; a
dark variant would be its own validated token set, not an automatic
flip (documented in decisions.md, revisitable at go-live).
"""

from __future__ import annotations

from typing import Any

from macropulse.scope import COUNTRIES

# --- categorical hues (validated sequence; see module docstring) ---------------
#
# One hue per panel economy in S01 panel order. Hexes are MacroPulse's
# own muted editorial set (claret / teal / ochre / plum / terracotta /
# blue / magenta / green / amber / teal-light), validated in this exact
# sequence (adjacent pairlist, light surface #fdfdfc):
# PASS: lightness band, chroma floor, normal-vision floor, contrast;
# WARN (relief rule, see docstring): protan 7.7 on green<->amber, and
# sub-3:1 contrast on amber / teal-light.
_HUES = (
    "#9d2244",  # claret
    "#0e95a6",  # teal
    "#a5760d",  # ochre
    "#7a4a9e",  # plum
    "#c05a2e",  # terracotta
    "#3a66c4",  # blue
    "#a0447c",  # magenta
    "#4c8a4f",  # green
    "#b8912a",  # amber
    "#17a6b3",  # teal-light
)

COUNTRY_COLORS: dict[str, str] = {
    country.iso3: hue for country, hue in zip(COUNTRIES, _HUES, strict=True)
}

# Context series (the non-focus lines in a comparison chart): the
# reference chrome "muted" grey. Recessive by design; identity for these
# series travels by hover provenance and the matrix table, not hue.
CONTEXT_GREY = "#898781"

# --- chart chrome and ink (light mode; warm paper tones) ------------------------
PAGE = "#fdfdfc"  # page plane (also the Streamlit background)
INK = "#0b0b0b"  # primary text
INK_SECONDARY = "#52514e"  # titles, captions, legend text
INK_MUTED = "#898781"  # axis ticks, de-emphasized labels
GRID = "#e1e0d9"  # hairline gridlines
BASELINE = "#c3c2b7"  # axis lines and the zero line

# Neutral wash for historical-episode bands: a paper-adjacent warm grey
# that carries no status or polarity meaning.
EPISODE_WASH = "#e8e6dd"

# --- typography -----------------------------------------------------------------
#
# Serif display for chart/dashboard titles (editorial reference;
# Spectral is an open font - financial-press faces are proprietary and
# are NOT used), system sans for everything that must stay legible at
# small sizes (ticks, labels, tables). Fallbacks make offline rendering
# honest: without the webfont, Spectral degrades to Georgia, not to a
# fabricated substitution.
FONT_DISPLAY = "Spectral, Georgia, 'Times New Roman', serif"
FONT_SANS = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# --- mark specs -------------------------------------------------------------------
#
# Thin marks (no markers on 60+ point series - the hover layer carries
# point inspection); the focus line is slightly heavier, context lines
# lighter; a hairline zero line matters for growth charts (values cross
# zero and the baseline must not be guessed).
LINE_WIDTH_FOCUS = 2.5
LINE_WIDTH_CONTEXT = 1.75

# Isolated observed points (both grid neighbours missing - the survey-
# wave shape, e.g. Findex account ownership) render as explicit markers:
# a line-only trace with unconnected gaps would make a REAL observation
# invisible. The page-colored outline keeps the mark legible over grid-
# lines and episode bands; dense series never grow markers (the mark
# spec above still holds - this only rescues points a line cannot reach).
MARKER_SIZE_ISOLATED = 8
MARKER_OUTLINE_WIDTH = 1.25

TITLE_SIZE = 17
TICK_SIZE = 11


def country_color(iso3: str) -> str:
    """Entity-fixed color for a panel economy.

    The panel is closed (S01): a country without a token is a token-level
    decision (add it to the map, with the palette re-validated), not a
    runtime fallback - a silent default hue would fabricate identity.
    """
    try:
        return COUNTRY_COLORS[iso3]
    except KeyError:
        raise ValueError(
            f"no color token for {iso3!r}: the panel and its palette are "
            "closed; add the country to views.theme.COUNTRY_COLORS "
            "(re-validate the palette) before charting it"
        ) from None


def series_style(iso3: str, focus: bool) -> dict[str, Any]:
    """Trace styling for one series: entity color when in focus, context
    grey otherwise. ``focus`` is the display role, not a judgment about
    importance: on a single-series chart the series is always the focus
    (it wears its own entity color and the title names it)."""
    return {
        "color": country_color(iso3) if focus else CONTEXT_GREY,
        "width": LINE_WIDTH_FOCUS if focus else LINE_WIDTH_CONTEXT,
        "showlegend": focus,  # legend names colored series; greys are
        # context, identified by hover and the matrix table
    }


def focus_label_point(xs: list, ys: list) -> tuple | None:
    """Position for the focus line's direct label: the LAST OBSERVED
    point of the series - never a gap (a label on a missing point would
    fabricate a data position). ``None`` when the series has no observed
    point at all, in which case no label is drawn."""
    for x, y in zip(reversed(xs), reversed(ys), strict=True):
        if y is not None:
            return x, y
    return None


def layout_update(title: str, yaxis_title: str) -> dict[str, Any]:
    """The shared editorial layout: serif left-aligned title, hairline
    grid, recessive axes, transparent plot area blending into the page.

    Applied via ``fig.update_layout(**layout_update(...))``; one axis
    only (a second y-scale is banned by method, not preference).
    """
    return {
        "title": {
            "text": title,
            "font": {"family": FONT_DISPLAY, "size": TITLE_SIZE, "color": INK},
            "x": 0.01,  # left-aligned, editorial
            "xanchor": "left",
        },
        "yaxis": {
            "title": {"text": yaxis_title, "font": {"size": 12}},
            "gridcolor": GRID,
            "gridwidth": 1,
            "zerolinecolor": BASELINE,
            "zerolinewidth": 1,
            "linecolor": BASELINE,
            "tickfont": {"family": FONT_SANS, "size": TICK_SIZE, "color": INK_MUTED},
        },
        "xaxis": {
            "gridcolor": GRID,
            "linecolor": BASELINE,
            "tickfont": {"family": FONT_SANS, "size": TICK_SIZE, "color": INK_MUTED},
        },
        "font": {"family": FONT_SANS, "color": INK_SECONDARY},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 56, "r": 24, "t": 48, "b": 40},
        "hoverlabel": {
            "font": {"family": FONT_SANS, "size": 12, "color": INK},
            "bgcolor": "white",
            "bordercolor": GRID,
        },
    }


__all__ = [
    "BASELINE",
    "CONTEXT_GREY",
    "COUNTRY_COLORS",
    "EPISODE_WASH",
    "FONT_DISPLAY",
    "FONT_SANS",
    "GRID",
    "INK",
    "INK_MUTED",
    "INK_SECONDARY",
    "LINE_WIDTH_CONTEXT",
    "LINE_WIDTH_FOCUS",
    "MARKER_OUTLINE_WIDTH",
    "MARKER_SIZE_ISOLATED",
    "PAGE",
    "country_color",
    "focus_label_point",
    "layout_update",
    "series_style",
]
