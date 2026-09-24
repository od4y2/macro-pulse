"""Pure chart-annotation builders for documented episodes (unit S18).

Everything here is a deterministic function from registry episodes and
rendered period bounds to Plotly figure overlays and caption strings -
no I/O, no clock reads, so annotation behavior is tested as data
(``app/dashboard.py`` only applies the returned dicts).

Claims discipline:

- The band + callout mark THAT a documented event occupied a calendar
  window (per its mandatory citation). Nothing here states that the
  event produced any data movement: the caption names the source and
  the window, the chart draws the observed values, and the two are
  never connected with causal language (``assert_no_causal_wording``
  is exported so tests and the caption builder share one vocabulary).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from macropulse.case_study.macro_episodes import MacroEpisode
from macropulse.views.theme import EPISODE_WASH, FONT_SANS, INK_SECONDARY

# Closed vocabulary of causal-attribution words banned from caption text.
# The S16 lesson applies: this check gets NO exemption for good
# intentions - captions are worded to pass it from the start.
_CAUSAL_WORDS = ("because", "caused", "cause", "due to", "led to", "drove", "resulted in")


def assert_no_causal_wording(text: str) -> None:
    """Raise if ``text`` asserts attribution. Case-insensitive substring
    match over the closed vocabulary; shared by the caption builder and
    the test suite so the two cannot drift apart."""
    lowered = text.lower()
    for word in _CAUSAL_WORDS:
        if word in lowered:
            raise ValueError(
                f"annotation caption must not contain causal wording "
                f"({word!r}): bands mark documented event windows; the "
                "observed series are drawn as stored, never explained"
            )


def episodes_in_range(
    episodes: tuple[MacroEpisode, ...], first: date, last: date
) -> tuple[MacroEpisode, ...]:
    """Registry episodes whose window overlaps the rendered range,
    in registry order. Pure filter on ``MacroEpisode.overlaps``."""
    if last < first:
        raise ValueError(f"range end {last} must be on or after start {first}")
    return tuple(e for e in episodes if e.overlaps(first, last))


def episode_overlays(
    episodes: tuple[MacroEpisode, ...], first: date, last: date
) -> list[dict[str, Any]]:
    """Plotly shapes + annotations marking each in-range episode.

    Band: a full-height neutral wash (``EPISODE_WASH``) drawn BELOW the
    traces, so lines stay readable; no border. Callout: the episode
    title in secondary ink near the top of the plot area, anchored at
    the band center. Titles are added for bands at least 1% as wide as
    the rendered range - narrower bands get the wash only, because a
    label anchored far outside its band would read as claiming more
    window than the source documents. (1% keeps a one-year band labeled
    on the panel's 1960-2025 annual range, the historical case S18
    presents; text may overflow the band's edges, which is cosmetic,
    not a claim.)
    """
    overlays: list[dict[str, Any]] = []
    in_range = episodes_in_range(episodes, first, last)
    rendered_days = (last - first).days or 1
    for episode in in_range:
        band_start = max(episode.start, first)
        band_end = min(episode.end, last)
        overlays.append(
            {
                "type": "shape",
                "spec": {
                    "type": "rect",
                    "xref": "x",
                    "yref": "paper",
                    "x0": band_start.isoformat(),
                    "x1": band_end.isoformat(),
                    "y0": 0,
                    "y1": 1,
                    "fillcolor": EPISODE_WASH,
                    "line": {"width": 0},
                    "layer": "below",
                },
            }
        )
        band_days = (band_end - band_start).days or 1
        if band_days / rendered_days >= 0.01:
            center = band_start + (band_end - band_start) / 2
            overlays.append(
                {
                    "type": "annotation",
                    "spec": {
                        "x": center.isoformat(),
                        "y": 1,
                        "yref": "paper",
                        "xanchor": "center",
                        "yanchor": "top",
                        "text": episode.title,
                        "showarrow": False,
                        "font": {
                            "family": FONT_SANS,
                            "size": 11,
                            "color": INK_SECONDARY,
                        },
                    },
                }
            )
    return overlays


def episode_captions(episodes: tuple[MacroEpisode, ...]) -> str:
    """Citation caption for the bands shown on a chart: one markdown
    line per episode, naming the window, the source, the verbatim
    document title, the URL, and the publication date. Wording is
    checked by ``assert_no_causal_wording`` before it is returned."""
    if not episodes:
        return ""
    lines = [
        "Shaded band: documented event window - "
        f"{e.title}, {e.start.isoformat()} to {e.end.isoformat()} "
        f"({e.source_name}, *{e.source_title}*, {e.source_url}, "
        f"published {e.published.isoformat()}). "
        "The band marks the published calendar window; values are drawn as observed."
        for e in episodes
    ]
    caption = " ".join(lines)
    assert_no_causal_wording(caption)
    return caption


def apply_overlays(fig: Any, overlays: list[dict[str, Any]]) -> None:
    """Apply ``episode_overlays`` output to a Plotly figure. Kept here so
    the dashboard layer contains no annotation logic; the shape and
    annotation specs themselves are pure data from the builders above."""
    for overlay in overlays:
        if overlay["type"] == "shape":
            fig.add_shape(**overlay["spec"])
        elif overlay["type"] == "annotation":
            fig.add_annotation(**overlay["spec"])
        else:  # pragma: no cover - closed output vocabulary
            raise ValueError(f"unknown overlay type {overlay['type']!r}")


__all__ = [
    "apply_overlays",
    "assert_no_causal_wording",
    "episode_captions",
    "episode_overlays",
    "episodes_in_range",
]
