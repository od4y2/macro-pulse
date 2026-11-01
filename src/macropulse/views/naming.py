"""Display naming for indicators (second-round UI refinement, 2026-11-01).

The served indicator records carry a long human name and an internal
code (``Account ownership at a financial institution or mobile-money
provider (% of adults) [account_ownership_pct]``). Repeating that whole
string in the selector AND the chart title made both hard to scan, so
the display layer now keeps three tiers:

1. **Display name** - a short human name, used ONLY where the meaning
   is unambiguous without the qualifier (``SHORT_NAMES`` below). An
   indicator without a curated short name keeps its FULL served name,
   wrapped rather than truncated - a guessed abbreviation would be a
   claim about the series, not a label.
2. **Unit** - the served unit token rendered as readable text
   (``percent_of_adults`` -> ``% of adults``), shown next to the display
   name in selectors and as the chart's y-axis title.
3. **Full name + internal code** - unchanged in the data, and still
   reachable where it always was: the widget's native ``help`` tooltip
   (``indicator_help``), the methodology expander, and every table that
   carries ``indicator_id``.

Nothing here touches queries, widget keys, exported rows or source
identifiers: these are presentation strings only, pure functions of the
served indicator records (no I/O, no clock), so they test as data.
"""

from __future__ import annotations

# Readable unit text per served unit token. A token absent from this map
# renders as its underscores-to-spaces form - readable, and never a
# invented unit: the words are the token's own.
UNIT_DISPLAY = {
    "percent": "%",
    "percent_per_year": "% per year",
    "percent_per_annum": "% per annum",
    "percent_gross": "% gross",
    "percent_of_adults": "% of adults",
    "percent_of_gdp": "% of GDP",
    "per_100_people": "per 100 people",
}

# Curated short display names, one per indicator whose meaning stays
# unambiguous without the full qualifier. Population/scope words that
# change what the series counts (adults, past year, gross) are kept;
# words the unit tier already states (% of adults, % of GDP) are not
# repeated. Anything absent keeps its full served name.
SHORT_NAMES = {
    "gdp_real_growth": "Real GDP growth",
    "cpi_inflation": "Consumer price inflation",
    "unemployment_rate": "Unemployment rate",
    "youth_unemployment_rate": "Youth unemployment rate",
    "neet_rate": "NEET rate (youth)",
    "tertiary_enrollment": "Tertiary enrollment (gross)",
    "internet_users_pct": "Internet users",
    "mobile_subscriptions_per100": "Mobile subscriptions",
    "account_ownership_pct": "Account ownership (financial or mobile-money)",
    "digital_payments_made_pct": "Digital payments (past year)",
    "health_expenditure_pct_gdp": "Current health expenditure",
    "policy_rate": "Short-term policy rate",
}


def unit_display(unit: str) -> str:
    """Readable unit text: mapped token, else the token's own words."""
    return UNIT_DISPLAY.get(unit, unit.replace("_", " "))


def display_name(indicator_id: str, full_name: str) -> str:
    """Short display name when curated, else the full served name."""
    return SHORT_NAMES.get(indicator_id, full_name)


def option_label(indicator_id: str, full_name: str, unit: str) -> str:
    """Selector label: display name tier, then the unit tier."""
    return f"{display_name(indicator_id, full_name)} · {unit_display(unit)}"


def indicator_help(indicators: list[dict]) -> str:
    """Native widget help: every full name with its internal code.

    The selector shows tiers 1-2; this tooltip is where tier 3 lives,
    alongside the methodology expander and the ``indicator_id`` columns.
    """
    lines = [f"- `{i['indicator_id']}` — {i['name']}" for i in indicators]
    return "**Full indicator names and codes**\n\n" + "\n".join(lines)


# Line widths in CHARACTERS for the two in-chart text blocks Plotly will
# not wrap for us. 40 keeps a 16px semibold title line inside the ~330px
# plot of a 390px viewport (the narrowest verified width); 30 keeps an
# 11px callout line inside ~170px so a band-centered callout box stays
# within the plot horizontally (verified by CDP bounding-box probe,
# 2026-11-01: an unwrapped 57-char callout rendered 324px wide and
# clipped on a 990px plot).
TITLE_LINE_CHARS = 40
CALLOUT_LINE_CHARS = 30


def wrap_lines(text: str, width: int) -> list[str]:
    """Greedy word-wrap onto lines of at most ``width`` characters.

    Every word survives, in order - never truncated, never broken mid-
    word (a word longer than ``width`` sits alone on its line). Plotly
    renders ``<br>``-joined output of this as real lines; it does NOT
    wrap long single lines, and its annotation ``width`` property was
    observed not to wrap either, so the wrapping is done here, where it
    is deterministic and testable.
    """
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def wrap_title(text: str, width: int = TITLE_LINE_CHARS) -> str:
    """Word-wrap a chart title into Plotly ``<br>`` lines (see wrap_lines)."""
    return "<br>".join(wrap_lines(text, width))


__all__ = [
    "CALLOUT_LINE_CHARS",
    "SHORT_NAMES",
    "TITLE_LINE_CHARS",
    "UNIT_DISPLAY",
    "display_name",
    "indicator_help",
    "option_label",
    "unit_display",
    "wrap_lines",
    "wrap_title",
]
