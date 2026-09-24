"""Tests for the S18 documented macro-episode registry.

Two groups (same discipline as the S12 case-study tests):

1. The registry itself - the real WHO 2020 episode must satisfy every
   governance rule (a real event is not exempt from validation).
2. The machinery on synthetic episodes - normal, boundary, and invalid
   cases: citation-mandatory construction, closed kinds, window
   arithmetic, and registry-level uniqueness.
"""

from __future__ import annotations

from datetime import date

import pytest

from macropulse.case_study.macro_episodes import (
    EPISODE_KINDS,
    MACRO_EPISODES,
    MacroEpisode,
    validate_macro_registry,
)


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


# --- the real registry ------------------------------------------------------------


def test_registry_is_valid_and_unique() -> None:
    assert validate_macro_registry(MACRO_EPISODES) == []
    assert len(MACRO_EPISODES) >= 1


def test_real_episode_is_external_cited_and_calendar_scale() -> None:
    (episode,) = MACRO_EPISODES
    assert episode.evidence_label == "external"
    assert episode.kind == "global_event"
    assert episode.start == date(2020, 1, 1)
    assert episode.end == date(2020, 12, 31)
    assert episode.applies_to is None  # whole panel
    assert episode.source_url.startswith("https://")
    assert episode.source_title  # verbatim title present
    # the timeline page postdates the 11 March 2020 announcement it documents
    # (the band's year-end is a display convention, not a publication bound)
    assert episode.published >= date(2020, 3, 11)


# --- construction rules (an invalid episode cannot exist) ---------------------------


@pytest.mark.parametrize(
    "field", ["source_name", "source_title", "source_url"]
)
def test_missing_citation_raises(field: str) -> None:
    with pytest.raises(ValueError, match="citation is mandatory"):
        synthetic_episode(**{field: ""})


def test_non_http_url_raises() -> None:
    with pytest.raises(ValueError, match="http"):
        synthetic_episode(source_url="ftp://example.org/x")


def test_unknown_kind_raises() -> None:
    with pytest.raises(ValueError, match="not in"):
        synthetic_episode(kind="market_crash")


def test_end_before_start_raises() -> None:
    with pytest.raises(ValueError, match="on or after start"):
        synthetic_episode(start=date(2021, 1, 1), end=date(2020, 1, 1))


def test_empty_applies_to_raises() -> None:
    with pytest.raises(ValueError, match="empty tuple is ambiguous"):
        synthetic_episode(applies_to=())


def test_non_external_evidence_label_raises() -> None:
    # episodes are documents about events, never API observations
    with pytest.raises(ValueError, match="external"):
        synthetic_episode(evidence_label="real")


def test_empty_episode_id_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        synthetic_episode(episode_id=" ")


# --- window arithmetic ---------------------------------------------------------------


def test_overlaps_touching_ranges_are_true() -> None:
    episode = synthetic_episode()  # window [2020-01-01, 2020-12-31]
    assert episode.overlaps(date(2020, 1, 1), date(2020, 6, 30))  # starts at window start
    assert episode.overlaps(date(2020, 12, 31), date(2021, 6, 30))  # ends at window end
    assert episode.overlaps(date(2019, 1, 1), date(2022, 1, 1))  # strictly contains
    assert episode.overlaps(date(2018, 1, 1), date(2020, 3, 1))  # overlaps head


def test_overlaps_disjoint_ranges_are_false() -> None:
    episode = synthetic_episode()  # window [2020-01-01, 2020-12-31]
    assert not episode.overlaps(date(2018, 1, 1), date(2019, 12, 31))
    assert not episode.overlaps(date(2021, 1, 1), date(2022, 12, 31))


# --- registry-level rules --------------------------------------------------------------


def test_duplicate_ids_are_reported() -> None:
    two = (synthetic_episode(), synthetic_episode())
    problems = validate_macro_registry(two)
    assert problems == ["duplicate episode ids: ['test-episode']"]


def test_kind_vocabulary_is_closed() -> None:
    assert EPISODE_KINDS == ("global_event", "policy_event")
