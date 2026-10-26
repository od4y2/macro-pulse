"""Documented macro-episode registry for historical-case annotation (unit S18).

An **episode** here is a documented calendar window around a published
real-world event - NOT a statistical observation. Episodes therefore
carry the ``external`` evidence label and a MANDATORY citation (source
name, verbatim document title, URL, publication date), exactly like the
S12 payment-outage registry: an uncited episode is a fabrication and
fails construction.

How this differs from ``episodes.py`` (S12): those are intraday payment
system outage windows (timezone-aware datetimes, scheduled/unscheduled
kinds); these are calendar-scale macro events (``date`` bounds - no
intraday claim is made, so no timezone is needed) shown as bands on
time-series charts.

Claims discipline (enforced here and in the annotation layer):

- An episode states THAT a documented event occupied a calendar window,
  per its citation. It never asserts that the event caused anything
  observed in the data: the chart draws the band and the data; the
  reader looks. Caption text is checked against a causal-vocabulary
  filter in tests (the S16 lesson: a disclaimer that uses banned
  literals is indistinguishable, to a mechanical check, from a
  violation - so captions use neutral wording from the start).

Registry citation verified live 2026-09-18; the verbatim quote and
fetch timestamp are captured in ``evidence/S18/live-verification.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macropulse.scope import EVIDENCE_LABELS

# Closed vocabulary: what kind of calendar-scale event an episode records.
EPISODE_KINDS = ("global_event", "policy_event")

# Episodes are documents about real events, not API observations: they
# are labelled external, never real.
EPISODE_EVIDENCE_LABEL = "external"


@dataclass(frozen=True)
class MacroEpisode:
    """One documented calendar window around a published macro event.

    Citation fields (source_name, source_title, source_url, published)
    are mandatory: an episode is a claim about a real event, and the
    claim must trace to the document that stated it - same rule as the
    S12 registry.
    """

    episode_id: str
    title: str  # short English title (ours) for chart callouts
    kind: str  # EPISODE_KINDS
    start: date
    end: date
    applies_to: tuple[str, ...] | None  # ISO3 codes; None = whole panel
    description: str  # factual, cited to the source; no causal language
    source_name: str  # publishing organization
    source_title: str  # verbatim document title
    source_url: str
    published: date
    evidence_label: str = EPISODE_EVIDENCE_LABEL

    def __post_init__(self) -> None:
        if not self.episode_id or not self.episode_id.strip():
            raise ValueError("episode_id must be non-empty")
        if self.kind not in EPISODE_KINDS:
            raise ValueError(f"episode kind {self.kind!r} not in {EPISODE_KINDS}")
        if self.end < self.start:
            raise ValueError(
                f"episode {self.episode_id}: end {self.end} must be on or "
                f"after start {self.start}"
            )
        if self.applies_to is not None and not self.applies_to:
            raise ValueError(
                f"episode {self.episode_id}: applies_to must be panel ISO3 "
                "codes or None (whole panel) - an empty tuple is ambiguous"
            )
        for field_name in ("source_name", "source_title", "source_url"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(
                    f"episode {self.episode_id}: {field_name} citation is "
                    "mandatory - an uncited episode is a fabrication"
                )
        if self.source_url and not self.source_url.startswith(("http://", "https://")):
            raise ValueError(f"episode {self.episode_id}: source_url must be http(s)")
        if self.evidence_label not in EVIDENCE_LABELS:
            raise ValueError(
                f"episode {self.episode_id}: evidence_label "
                f"{self.evidence_label!r} not in the S01 vocabulary"
            )
        if self.evidence_label != EPISODE_EVIDENCE_LABEL:
            raise ValueError(
                f"episode {self.episode_id}: episodes are external documents, "
                f"not API observations - label must be "
                f"{EPISODE_EVIDENCE_LABEL!r}"
            )

    def overlaps(self, first: date, last: date) -> bool:
        """Does the episode window overlap [first, last]?

        Pure date arithmetic; used to decide whether a chart band is
        relevant to the rendered period range.
        """
        return self.start <= last and first <= self.end


# --- verified registry (citation live-verified 2026-09-18) ----------------------
#
# The 2020 episode marks the calendar year in which WHO characterized
# COVID-19 as a pandemic. The band marks a documented event window on
# annual data; the observed series are drawn as stored, and no causal
# statement is made anywhere in the annotation layer.

MACRO_EPISODES: tuple[MacroEpisode, ...] = (
    MacroEpisode(
        episode_id="who-covid-2020",
        title="WHO characterizes COVID-19 as a pandemic (11 March 2020)",
        kind="global_event",
        start=date(2020, 1, 1),
        end=date(2020, 12, 31),
        applies_to=None,  # whole panel
        description=(
            "The World Health Organization's assessment that COVID-19 can "
            "be characterized as a pandemic was announced 11 March 2020; "
            "the band marks the calendar year containing the announcement."
        ),
        source_name="World Health Organization",
        source_title="Archived: WHO Timeline - COVID-19",
        source_url="https://www.who.int/news/item/27-04-2020-who-timeline---covid-19",
        published=date(2020, 4, 27),
    ),
)


def validate_macro_registry(episodes: tuple[MacroEpisode, ...]) -> list[str]:
    """Registry-level invariants; empty list means valid. Episode-level
    rules are enforced at construction (frozen dataclass - an invalid
    episode cannot exist); the registry adds id uniqueness, because a
    duplicate id would make callout references ambiguous."""
    ids = [e.episode_id for e in episodes]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        return [f"duplicate episode ids: {dupes}"]
    return []


__all__ = [
    "EPISODE_EVIDENCE_LABEL",
    "EPISODE_KINDS",
    "MACRO_EPISODES",
    "MacroEpisode",
    "validate_macro_registry",
]
