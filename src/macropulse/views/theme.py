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
- **Entity color on every series.** Every series on a multi-series chart
  wears its entity hue and appears in the legend, so a comparison reads
  country-by-country on the chart itself. (Second-round comparison fix,
  2026-11-01: the earlier focus-and-context display - one hue, every
  other series in a uniform grey - left non-focus countries
  indistinguishable on the chart, which defeated the comparison view.)
  Focus is now EMPHASIS, not exclusive color: a heavier line plus a
  direct label on the focus series' last observed point.
- **Relief rule (validator WARNs are honored, not waved off).** The
  recorded validation (``evidence/S18/palette-validation.txt``) passes
  with two floor-band WARNs - KOR green vs ZAF amber protan DeltaE 7.7
  (floor band 6-8), and sub-3:1 surface contrast for ZAF amber / MEX
  teal-light - and the panel deliberately carries one hue family (CHN
  teal / MEX teal-light). Now that hues render simultaneously, each
  flagged country ALSO carries a hue-independent channel: ``RELIEF_DASH``
  on its line and ``RELIEF_SYMBOL`` on its isolated-point markers, on
  top of the secondary encoding every chart ships (full legend, hover
  provenance, value-matrix table). The validator script itself is no
  longer in the repo, so this governance change is recorded here rather
  than re-validated.
- **Text wears ink, not series colors** (labels/legends/ticks stay in
  the ink tokens below; the colored mark carries the identity).

Light mode only, by decision: the dashboard pins Streamlit to a light
theme (``.streamlit/config.toml``), so no dark palette is shipped; a
dark variant would be its own validated token set, not an automatic
flip (documented in decisions.md, revisitable at go-live).

First-round UI refinement (user directive, 2026-11-01): the chrome
layer moved from the S18 warm-paper/claret scheme to an ink-blue +
cool-white scheme (ACCENT / PAGE / SURFACE / BORDER / INK tokens below,
mirrored in ``.streamlit/config.toml``). ``COUNTRY_COLORS`` is UNCHANGED
- the entity hues still carry identity exactly as validated in
``evidence/S18/palette-validation.txt``. The chrome tokens are new
hexes, so that validation's chrome rows are stale for them; a re-run of
the palette validator is a noted follow-up, and the relief rule above
now ships per-country texture as well as legend, hover and table.
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

# Hue-independent texture for the countries the recorded validation
# flagged (relief rule, module docstring): ZAF amber sits in the protan
# floor band against KOR green and below 3:1 surface contrast, and MEX
# teal-light shares CHN's hue family at sub-3:1 contrast. The dash
# carries on lines; the symbol carries on isolated-point markers, where
# no line segment renders at all. Everyone else: solid line, circle.
RELIEF_DASH: dict[str, str] = {"ZAF": "dash", "MEX": "dot"}
RELIEF_SYMBOL: dict[str, str] = {"ZAF": "diamond", "MEX": "square"}

# --- brand accent (ink blue) ------------------------------------------------------
ACCENT = "#2457A7"  # primary actions, active tab, single-series focus line
ACCENT_HOVER = "#1D4687"  # hover/pressed state for accent surfaces
SELECTED = "#EAF0FA"  # selected_background (multiselect tags, selected rows)

# --- chart chrome and ink (light mode; cool-white tones) --------------------------
PAGE = "#F8FAFC"  # page plane (also the Streamlit background)
SURFACE = "#FFFFFF"  # card/plot plane (chart plotting area is white)
BORDER = "#DCE2EA"  # hairline borders on chrome elements
INK = "#17212F"  # primary text
INK_SECONDARY = "#526174"  # titles, captions, legend text
GRID = "#E7EBF0"  # hairline gridlines (chart_grid)
BASELINE = "#DCE2EA"  # axis lines and the zero line

# Neutral wash for historical-episode bands: a low-opacity cool grey
# (chart_context at 18%) that carries no status or polarity meaning and
# never obscures observations (bands are drawn below the traces).
EPISODE_WASH = "rgba(154, 166, 181, 0.18)"

# --- typography -----------------------------------------------------------------
#
# Serif display is reserved for the MacroPulse page title (editorial
# reference; Spectral is an open font - financial-press faces are
# proprietary and are NOT used). Everything else - body, controls,
# tables, chart titles, ticks, labels - wears the system sans for
# legibility at small sizes (user directive, 2026-11-01). Fallbacks make
# offline rendering honest: without the webfont, Spectral degrades to
# Georgia, not to a fabricated substitution.
FONT_DISPLAY = "Spectral, Georgia, 'Times New Roman', serif"  # page h1 only
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

TITLE_SIZE = 16
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
    """Trace styling for one series: its entity color ALWAYS, plus the
    relief dash for flagged countries (``RELIEF_DASH``), so a comparison
    chart reads country-by-country on the chart itself.

    ``focus`` is emphasis, not exclusive color: a heavier line here, and
    a direct end label in the renderer. On a single-series chart the
    dashboard swaps in the brand accent and clears the texture - an
    entity hue and its relief carry no information when nothing is
    being compared."""
    return {
        "color": country_color(iso3),
        "width": LINE_WIDTH_FOCUS if focus else LINE_WIDTH_CONTEXT,
        "showlegend": True,  # every series is named: identity is the point
        "dash": RELIEF_DASH.get(iso3, "solid"),
    }


def marker_symbol(iso3: str) -> str:
    """Isolated-point marker symbol: the relief shape for flagged
    countries (``RELIEF_SYMBOL``), a plain circle everywhere else."""
    return RELIEF_SYMBOL.get(iso3, "circle")


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
    """The shared layout: sans left-aligned title in primary ink, hairline
    cool grid, recessive axes, white plotting area on the cool-white page.

    Applied via ``fig.update_layout(**layout_update(...))``; one axis
    only (a second y-scale is banned by method, not preference).
    """
    return {
        "title": {
            "text": title,
            "font": {
                "family": FONT_SANS,
                "size": TITLE_SIZE,
                "color": INK,
                "weight": 600,
            },
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
            # ticks are text: secondary ink keeps them >=4.5:1 on the white
            # plot area (the chart_context grey is for series, not labels)
            "tickfont": {
                "family": FONT_SANS,
                "size": TICK_SIZE,
                "color": INK_SECONDARY,
            },
        },
        "xaxis": {
            "gridcolor": GRID,
            "linecolor": BASELINE,
            "tickfont": {
                "family": FONT_SANS,
                "size": TICK_SIZE,
                "color": INK_SECONDARY,
            },
        },
        "font": {"family": FONT_SANS, "color": INK_SECONDARY},
        "paper_bgcolor": "rgba(0,0,0,0)",  # margins blend into the page
        "plot_bgcolor": SURFACE,  # plotting area is white (surface token)
        # Top margin headroom (second-round refinement): fits a wrapped
        # two-line title (16px) AND the episode callout strip that now
        # renders above the plot area (annotations.CALLOUT_Y), so
        # neither crosses the data or each other.
        "margin": {"l": 56, "r": 24, "t": 88, "b": 40},
        "hoverlabel": {
            "font": {"family": FONT_SANS, "size": 12, "color": INK},
            "bgcolor": SURFACE,
            "bordercolor": BORDER,
        },
    }


__all__ = [
    "ACCENT",
    "ACCENT_HOVER",
    "BASELINE",
    "BORDER",
    "COUNTRY_COLORS",
    "EPISODE_WASH",
    "FONT_DISPLAY",
    "FONT_SANS",
    "GRID",
    "INK",
    "INK_SECONDARY",
    "LINE_WIDTH_CONTEXT",
    "LINE_WIDTH_FOCUS",
    "MARKER_OUTLINE_WIDTH",
    "MARKER_SIZE_ISOLATED",
    "PAGE",
    "RELIEF_DASH",
    "RELIEF_SYMBOL",
    "SELECTED",
    "SURFACE",
    "country_color",
    "focus_label_point",
    "layout_update",
    "marker_symbol",
    "series_style",
]
