"""Centrally managed dashboard chrome CSS (first-round UI refinement).

The single place where Streamlit-layer styling lives; every color is read
from the ``views.theme`` tokens (one source of truth shared with the
charts and ``.streamlit/config.toml``), so a palette change never forks
between CSS and Plotly.

Selector policy (user constraints, 2026-11-01):

- Only stable hooks: Streamlit ``data-testid`` attributes (including the
  ``[data-tag]`` chips of the multiselect tags container), ARIA roles and
  states, and plain element selectors scoped inside a stable container.
  No generated CSS class names, no ``nth-child``, no unscoped global
  element selectors.
- Nothing native is hidden (toolbars, download/search buttons, alerts,
  messages all stay visible); this module only re-colors, re-spaces, and
  re-sizes what Streamlit already renders.
- What the Streamlit theme config can do natively (colors, radii,
  borders, heading sizes, sidebar palette, dataframe chrome) is done in
  ``.streamlit/config.toml`` and NOT repeated here.

Pure string builder - no I/O, no clock, safe to import in tests.
"""

from __future__ import annotations

from macropulse.views.theme import (
    ACCENT,
    ACCENT_HOVER,
    BORDER,
    INK,
    INK_SECONDARY,
    SELECTED,
)


def dashboard_css() -> str:
    """Full chrome stylesheet for ``app/dashboard.py`` (one injection)."""
    return f"""
/* --- typography ------------------------------------------------------- */
/* Existing display face, kept for the page title ONLY (no new external
   font dependency; degrades to Georgia offline). */
@import url('https://fonts.googleapis.com/css2?family=Spectral:wght@500;600&display=swap');

h1 {{
  font-family: Spectral, Georgia, 'Times New Roman', serif !important;
  letter-spacing: -0.01em;
  color: {INK};
}}

/* All other headings, body, controls, tables and chart labels stay the
   system sans that Streamlit's theme already applies. */

/* --- page density: tighter top so filters/charts reach the first screen */
.stMainBlockContainer {{
  padding-top: 2rem;
  padding-bottom: 2rem;
}}

h1 {{
  margin-top: 0.25rem;
  margin-bottom: 0.5rem;
}}

/* Uniform 12px rhythm between related elements inside a block; module
   separation comes from the tab structure, headings and dividers - not
   from card frames. */
[data-testid="stVerticalBlock"] {{
  gap: 0.75rem;
}}

/* Helper text (captions): secondary ink, comfortable line height. Size
   scales with the 15px root to ~13px; only color/leading are set here. */
[data-testid="stCaptionContainer"] {{
  color: {INK_SECONDARY};
  line-height: 1.55;
}}

/* --- tabs --------------------------------------------------------------- */
/* Consistent tab sizing and spacing; the active tab wears the ink-blue
   text and the thin ink-blue underline (primaryColor from config.toml).
   Native keyboard navigation and focus rings are untouched. Selectors
   are the stable testid/ARIA hooks of the current Streamlit tablist. */
.stTabs [role="tablist"] {{
  gap: 0.25rem;
  border-bottom: 1px solid {BORDER};
}}

[data-testid="stTab"] {{
  font-size: 0.9375rem;
  padding: 0.5rem 1rem;
  background-color: transparent;
}}

[data-testid="stTab"]:hover {{
  color: {ACCENT_HOVER};
}}

[data-testid="stTab"][aria-selected="true"] {{
  color: {ACCENT};
}}

/* --- multiselect tags ---------------------------------------------------- */
/* Selected countries/indicators: light-blue chip with ink-blue text and a
   clearly visible remove control - never a row of solid dark blocks.
   Chips are the [data-tag] spans of the tags container; the per-chip
   remove button is identified by its "Remove <value>" ARIA label. */
[data-testid="stMultiSelectTagsContainer"] [data-tag] {{
  background-color: {SELECTED} !important;
  color: {ACCENT} !important;
  border-radius: 0.25rem;
}}

[data-testid="stMultiSelectTagsContainer"] [data-tag] span,
[data-testid="stMultiSelectTagsContainer"] [data-tag] svg {{
  color: {ACCENT};
  fill: {ACCENT};
  background-color: transparent;
}}

[data-testid="stMultiSelectTagsContainer"] button[aria-label^="Remove"]:hover {{
  background-color: rgba(36, 87, 167, 0.12);
}}

/* --- sidebar -------------------------------------------------------------- */
/* The service-address code block becomes compact monospace helper text:
   small, wrapping, low visual weight (background/border come from the
   theme config's code tokens). Status caption keeps its full text. */
[data-testid="stSidebar"] pre {{
  font-size: 0.75rem;
  line-height: 1.45;
  padding: 0.5rem 0.625rem;
  white-space: pre-wrap;
  word-break: break-all;
}}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
  color: {INK_SECONDARY};
}}

/* --- charts ---------------------------------------------------------------- */
/* Plotly figures sit directly on the page; give them the surface-white
   plotting area handled in views.theme.layout_update, and keep a little
   breathing room between stacked elements. */
[data-testid="stPlotlyChart"] {{
  margin: 0.25rem 0;
}}

/* --- narrow screens ---------------------------------------------------------- */
/* 390px-class widths: trim container padding and tab padding so nothing
   overlaps or forces horizontal page scroll (wide tables keep scrolling
   inside their own containers, which Streamlit does natively). */
@media (max-width: 480px) {{
  .stMainBlockContainer {{
    padding-top: 1.5rem;
    padding-left: 1rem;
    padding-right: 1rem;
  }}

  [data-testid="stTab"] {{
    font-size: 0.875rem;
    padding: 0.5rem 0.625rem;
  }}
}}
"""


__all__ = ["dashboard_css"]
