"""Tests for the S18 episode-annotation layer (pure overlay builders).

Grouped as:

1. The causal-wording filter shared by captions and tests.
2. Range filtering - which registry episodes are relevant to a chart.
3. Overlays - band + callout specs, the narrow-band rule, clipping to
   the rendered range, and application to a real Plotly figure.
4. Captions - full citation content, wording that passes the filter.
"""

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
import pytest

from macropulse.case_study.macro_episodes import MACRO_EPISODES, MacroEpisode
from macropulse.views.annotations import (
    apply_overlays,
    assert_no_causal_wording,
    episode_captions,
    episode_overlays,
    episodes_in_range,
)
from macropulse.views.theme import EPISODE_WASH


def synthetic_episode(**overrides: object) -> MacroEpisode:
    """A valid synthetic global-event episode."""
    params: dict[str, object] = {
        "episode_id": "test-episode",
        "title": "Synthetic test episode",
        "kind": "global_event",
        "start": date(2020, 1, 1),
        "end": date(2020, 12, 31),
        "applies_to": None,
        "description": "A synthetic window for tests; no real claim.",
        "source_name": "Test Bureau",
        "source_title": "Test Bulletin",
        "source_url": "https://example.org/bulletin/1",
        "published": date(2021, 1, 1),
    }
    params.update(overrides)
    return MacroEpisode(**params)  # type: ignore[arg-type]


# --- the causal-wording filter ------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "the band appears because growth fell",
        "the episode caused a contraction",
        "the series moved due to the event",
        "the event led to a decline",
        "the event drove the decline",
        "the policy resulted in slower growth",
        "The Event CAUSED a decline",  # case-insensitive
    ],
)
def test_causal_wording_raises(text: str) -> None:
    with pytest.raises(ValueError, match="causal wording"):
        assert_no_causal_wording(text)


def test_neutral_wording_passes() -> None:
    assert_no_causal_wording("The band marks the documented calendar window.")
    assert_no_causal_wording("")


# --- range filtering -----------------------------------------------------------------


def test_episodes_in_range_filters_by_overlap() -> None:
    episodes = (synthetic_episode(),)
    inside = episodes_in_range(episodes, date(2020, 6, 1), date(2020, 6, 30))
    outside = episodes_in_range(episodes, date(2021, 1, 1), date(2022, 12, 31))
    assert inside == episodes
    assert outside == ()


def test_episodes_in_range_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="on or after start"):
        episodes_in_range(MACRO_EPISODES, date(2021, 1, 1), date(2020, 1, 1))


# --- overlays ---------------------------------------------------------------------------


def test_real_2020_episode_yields_band_and_callout_on_panel_range() -> None:
    overlays = episode_overlays(MACRO_EPISODES, date(1960, 1, 1), date(2025, 12, 31))
    assert [o["type"] for o in overlays] == ["shape", "annotation"]
    (shape, callout) = overlays
    assert shape["spec"]["x0"] == "2020-01-01"
    assert shape["spec"]["x1"] == "2020-12-31"
    assert shape["spec"]["yref"] == "paper"
    assert (shape["spec"]["y0"], shape["spec"]["y1"]) == (0, 1)
    assert shape["spec"]["fillcolor"] == EPISODE_WASH
    assert shape["spec"]["layer"] == "below"  # lines stay readable over the wash
    assert shape["spec"]["line"]["width"] == 0
    # callout anchored at the band center, inside the band
    assert callout["spec"]["xanchor"] == "center"
    assert "2020-01-01" <= callout["spec"]["x"] <= "2020-12-31"
    assert callout["spec"]["text"] == MACRO_EPISODES[0].title


def test_narrow_band_gets_wash_but_no_callout() -> None:
    # a 30-day window inside a 66-year range is <1% wide: labeling it
    # would claim more window than the source documents
    narrow = (
        synthetic_episode(
            episode_id="narrow",
            start=date(2020, 3, 1),
            end=date(2020, 3, 30),
        ),
    )
    overlays = episode_overlays(narrow, date(1960, 1, 1), date(2025, 12, 31))
    assert [o["type"] for o in overlays] == ["shape"]
    assert overlays[0]["spec"]["x0"] == "2020-03-01"
    assert overlays[0]["spec"]["x1"] == "2020-03-30"


def test_band_is_clipped_to_the_rendered_range() -> None:
    straddling = (
        synthetic_episode(
            episode_id="straddle",
            start=date(2019, 6, 1),
            end=date(2020, 6, 30),
        ),
    )
    overlays = episode_overlays(straddling, date(2020, 1, 1), date(2020, 12, 31))
    (shape, callout) = overlays
    assert shape["spec"]["x0"] == "2020-01-01"  # clipped, not drawn outside
    assert shape["spec"]["x1"] == "2020-06-30"
    assert "2020-01-01" <= callout["spec"]["x"] <= "2020-06-30"


def test_episode_outside_range_yields_no_overlays() -> None:
    assert episode_overlays(MACRO_EPISODES, date(2010, 1, 1), date(2015, 12, 31)) == []


def test_apply_overlays_on_a_real_figure() -> None:
    fig = go.Figure()
    fig.add_scatter(x=["2020", "2021"], y=[1.0, 2.0])
    overlays = episode_overlays(MACRO_EPISODES, date(1960, 1, 1), date(2025, 12, 31))
    apply_overlays(fig, overlays)
    assert len(fig.layout.shapes) == 1
    assert len(fig.layout.annotations) == 1
    assert fig.layout.shapes[0].fillcolor == EPISODE_WASH


def test_apply_overlays_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="unknown overlay type"):
        apply_overlays(go.Figure(), [{"type": "cat", "spec": {}}])


# --- captions ------------------------------------------------------------------------------


def test_captions_carry_the_full_citation() -> None:
    caption = episode_captions(MACRO_EPISODES)
    (episode,) = MACRO_EPISODES
    assert "Shaded band: documented event window" in caption
    assert episode.title in caption
    assert "2020-01-01 to 2020-12-31" in caption
    assert episode.source_name in caption
    assert episode.source_title in caption
    assert episode.source_url in caption
    assert f"published {episode.published.isoformat()}" in caption
    assert "drawn as observed" in caption


def test_captions_pass_the_causal_filter_by_construction() -> None:
    # the builder runs assert_no_causal_wording before returning; a
    # wording regression in the template raises here, not in production
    for episodes in ((synthetic_episode(),), (synthetic_episode(), synthetic_episode(episode_id="two"))):
        episode_captions(episodes)


def test_empty_episodes_render_empty_caption() -> None:
    assert episode_captions(()) == ""
