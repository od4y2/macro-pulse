"""Payment-outage episode registry for the RQ3 case study (unit S12).

An **episode** is a documented window during which a payment system used
by healthcare providers was unavailable or degraded. Episodes are NOT
statistical observations: they are government announcements, press
notices, and official documents. Every episode therefore carries the
``external`` evidence label and a MANDATORY citation (source name, verbatim
document title, URL, publication date). An episode without a citation is
a fabrication and fails validation.

Registry contents (all verified live on 2026-08-29, quotes captured in
``evidence/S12/live-verification.md``): four official announcements from
the Yunnan (China) medical-security system - two recurring 48-hour
year-end rollover suspensions of the provincial medical-insurance
information platform, and two shorter upgrade-maintenance windows.

Governance:

- Closed kind vocabulary: ``scheduled_maintenance`` vs ``unplanned_outage``.
  All four registry entries are scheduled (announced in advance) - the
  registry must not blur that distinction, because a SCHEDULED outage is
  a different resilience fact than an unplanned one.
- The blind-spot half of RQ3 is computed, not asserted:
  ``observation_alignment`` derives, per catalog frequency, which
  observation periods an episode window lands in. A 48-hour outage that
  straddles the year boundary is split across two annual observations,
  and occupies ~0.5% of either - invisible in any level series. The
  construct gap (no catalog indicator measures operational continuity
  at all) is stated in docs/PaymentResilienceCaseStudy.md, because it is
  a fact about the indicator list, not arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from macropulse.catalog import FREQUENCIES
from macropulse.scope import EVIDENCE_LABELS

# Closed vocabulary: what kind of event an episode records.
EPISODE_KINDS = ("scheduled_maintenance", "unplanned_outage")

# Episodes come from official documents, not statistical APIs; they are
# labelled external, never real.
EPISODE_EVIDENCE_LABEL = "external"

# Episode windows are stated in the source documents' local time. The
# registry's sources are China's medical-security announcements, which
# use China Standard Time (UTC+8, no DST). Naive datetimes would be
# ambiguous - a window without a timezone is not a window.
CHINA_STANDARD_TIME = timezone(timedelta(hours=8), name="CST")

# Months per observation period, by catalog frequency (catalog.py is the
# single source of truth for the frequency vocabulary).
_FREQUENCY_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}


@dataclass(frozen=True)
class Episode:
    """One documented payment-outage window in a healthcare system.

    Citation fields (source_name, source_title, source_url, published)
    are mandatory: an episode is a claim about a real event, and the
    claim must trace to the document that announced it.
    """

    episode_id: str
    country_iso3: str
    region: str  # e.g. "Yunnan" - episodes are sub-national
    title: str  # English descriptive title (ours)
    kind: str  # EPISODE_KINDS
    start: datetime
    end: datetime
    payment_system: str
    healthcare_scope: str  # what could not be paid/settled during the window
    cause: str
    source_name: str  # publishing organization
    source_title: str  # verbatim document title (original language)
    source_url: str
    published: date
    evidence_label: str = EPISODE_EVIDENCE_LABEL

    def __post_init__(self) -> None:
        if not self.episode_id or not self.episode_id.strip():
            raise ValueError("episode_id must be non-empty")
        if len(self.country_iso3) != 3 or not self.country_iso3.isupper():
            raise ValueError(f"invalid ISO3 country code: {self.country_iso3!r}")
        if self.kind not in EPISODE_KINDS:
            raise ValueError(f"episode kind {self.kind!r} not in {EPISODE_KINDS}")
        if self.end <= self.start:
            raise ValueError(
                f"episode {self.episode_id}: end {self.end} must be after "
                f"start {self.start}"
            )
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError(
                f"episode {self.episode_id}: window datetimes must be "
                "timezone-aware (the source documents state local time; a "
                "naive window is ambiguous)"
            )
        if self.start.utcoffset() != self.end.utcoffset():
            raise ValueError(
                f"episode {self.episode_id}: start and end must share one "
                "timezone (source documents state one local time)"
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
        if self.kind == "scheduled_maintenance" and self.published > self.start.date():
            raise ValueError(
                f"episode {self.episode_id}: a scheduled maintenance must be "
                "announced on or before its window starts - that is what "
                "makes it scheduled"
            )
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

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


# --- verified registry (live, 2026-08-29) ------------------------------------
#
# Yunnan Provincial Medical Insurance Information Platform suspensions.
# Announcements quote-checked verbatim; see evidence/S12/live-verification.md.

YUNNAN_PLATFORM = "Yunnan Provincial Medical Insurance Information Platform"

EPISODES: tuple[Episode, ...] = (
    Episode(
        episode_id="yn-mi-2024-rollover",
        country_iso3="CHN",
        region="Yunnan",
        title="Yunnan medical-insurance platform year-end rollover (48h)",
        kind="scheduled_maintenance",
        start=datetime(2024, 12, 31, 20, 0, tzinfo=CHINA_STANDARD_TIME),
        end=datetime(2025, 1, 2, 20, 0, tzinfo=CHINA_STANDARD_TIME),
        payment_system=YUNNAN_PLATFORM,
        healthcare_scope=(
            "Province-wide: designated hospitals and retail pharmacies "
            "could not process networked medical-insurance settlement; "
            "cross-province and intra-province offsite direct settlement, "
            "the insurance QR code, Yunnan insurance WeChat/Alipay "
            "mini-programs and the online service hall were suspended."
        ),
        cause=(
            "2024 medical-insurance personal-account annual interest "
            "crediting and year-end business rollover"
        ),
        source_name="Kunming Municipal Medical Security Bureau",
        source_title=(
            "昆明市医疗保障局关于2024年医保信息平台计息和业务结转工作停机的通告"
        ),
        source_url="https://ybj.km.gov.cn/c/2024-12-27/4929546.shtml",
        published=date(2024, 12, 26),
    ),
    Episode(
        episode_id="yn-mi-2025-rollover",
        country_iso3="CHN",
        region="Yunnan",
        title="Yunnan medical-insurance platform year-end rollover (48h)",
        kind="scheduled_maintenance",
        start=datetime(2025, 12, 31, 20, 0, tzinfo=CHINA_STANDARD_TIME),
        end=datetime(2026, 1, 2, 20, 0, tzinfo=CHINA_STANDARD_TIME),
        payment_system=YUNNAN_PLATFORM,
        healthcare_scope=(
            "Province-wide: designated hospitals and retail pharmacies "
            "could not process networked medical-insurance settlement; "
            "cross-province and intra-province offsite direct settlement, "
            "the insurance QR code, Yunnan insurance WeChat/Alipay "
            "mini-programs, the online service hall and government-platform "
            "insurance channels were suspended."
        ),
        cause=(
            "2025 medical-insurance personal-account annual interest "
            "crediting and year-end business rollover"
        ),
        source_name="Yunnan Provincial Medical Security Bureau",
        source_title="关于2025年云南省医保信息平台计息和业务结转工作停机的公告",
        source_url="https://ylbz.yn.gov.cn/index.php?c=show&id=5863",
        published=date(2025, 12, 23),
    ),
    Episode(
        episode_id="yn-mi-2026-03-maintenance",
        country_iso3="CHN",
        region="Yunnan",
        title="Yunnan medical-insurance platform upgrade maintenance (8h)",
        kind="scheduled_maintenance",
        start=datetime(2026, 3, 24, 22, 0, tzinfo=CHINA_STANDARD_TIME),
        end=datetime(2026, 3, 25, 6, 0, tzinfo=CHINA_STANDARD_TIME),
        payment_system=YUNNAN_PLATFORM,
        healthcare_scope=(
            "Designated hospitals and retail pharmacies could not process "
            "networked insurance settlement; cross-province and "
            "intra-province offsite direct settlement, the insurance QR "
            "code, Yunnan insurance WeChat/Alipay mini-programs and the "
            "online service hall were suspended."
        ),
        cause="Platform function optimization and service-capacity upgrade",
        source_name="Yunnan Provincial Medical Security Bureau",
        source_title="云南省医疗保障信息平台升级维护公告",
        source_url="https://ylbz.yn.gov.cn/index.php?c=show&id=6072",
        published=date(2026, 3, 20),
    ),
    Episode(
        episode_id="yn-mi-2026-06-maintenance",
        country_iso3="CHN",
        region="Yunnan",
        title="Yunnan medical-insurance platform upgrade maintenance (2h)",
        kind="scheduled_maintenance",
        start=datetime(2026, 6, 12, 23, 0, tzinfo=CHINA_STANDARD_TIME),
        end=datetime(2026, 6, 13, 1, 0, tzinfo=CHINA_STANDARD_TIME),
        payment_system=YUNNAN_PLATFORM,
        healthcare_scope=(
            "Facial-recognition settlement, the medical-insurance "
            "e-wallet and cross-provincial direct settlement were "
            "suspended; in-province offsite direct settlement was "
            "unaffected."
        ),
        cause="Platform function optimization and service-capacity upgrade",
        source_name="Yunnan Provincial Medical Security Bureau",
        source_title="云南省医疗保障信息平台升级维护公告",
        source_url="https://ylbz.yn.gov.cn/index.php?c=show&id=6254",
        published=date(2026, 6, 12),
    ),
)


def validate_registry(episodes: tuple[Episode, ...]) -> list[str]:
    """Registry-level invariants; empty list means valid.

    Episode-level rules are enforced by the ``Episode`` constructor at
    construction time (frozen dataclass - an invalid episode cannot
    exist); the registry adds the uniqueness constraint, because an id
    collision would make episode references ambiguous.
    """
    ids = [e.episode_id for e in episodes]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        return [f"duplicate episode ids: {dupes}"]
    return []


def episodes_in_window(
    episodes: tuple[Episode, ...], start: datetime, end: datetime
) -> list[Episode]:
    """Episodes whose window overlaps [start, end)."""
    if end <= start:
        raise ValueError("window end must be after start")
    return [e for e in episodes if e.start < end and start < e.end]


def outage_hours_by_year(
    episodes: tuple[Episode, ...],
) -> dict[int, float]:
    """Total scheduled outage hours per calendar year (attribution: the
    year the episode STARTS in - a window straddling New Year's Eve is
    attributed to the starting year, matching the rollover's own timing)."""
    hours: dict[int, float] = {}
    for episode in episodes:
        year = episode.start.year
        hours[year] = hours.get(year, 0.0) + episode.duration_hours
    return hours


# --- the computed blind-spot half of RQ3 --------------------------------------


@dataclass(frozen=True)
class ObservationAlignment:
    """How an episode window lands on an indicator's observation grid."""

    frequency: str
    periods_spanned: tuple[str, ...]  # labels of periods the window touches
    boundary_straddled: bool  # True = the window crosses a period boundary
    duration_share_of_period: float  # episode hours / period hours (start's period)

    @property
    def resolvable(self) -> bool:
        """False when the observation grid cannot distinguish the episode
        from noise. Two ways to fail, either alone suffices:

        1. The window straddles a period boundary - the event is then
           split across two observations, each seeing only part of it.
        2. The window occupies under 1% of a period - the documented
           reporting threshold: an event that is <1% of an observation
           period cannot plausibly move a level aggregate beyond its own
           measurement noise.

        The 1% share is a presentation convention, not a statistical
        test; the components above are pure arithmetic."""
        if self.boundary_straddled:
            return False
        return self.duration_share_of_period >= 0.01


def _period_bounds(moment: datetime, frequency: str) -> tuple[datetime, datetime]:
    """Calendar bounds of the observation period containing ``moment``."""
    step = _FREQUENCY_MONTHS[frequency]
    year, month = moment.year, moment.month
    start_month = month
    if frequency == "quarterly":
        start_month = ((month - 1) // 3) * 3 + 1
    elif frequency == "annual":
        start_month = 1
    tz = moment.tzinfo
    start = datetime(year, start_month, 1, tzinfo=tz)
    end_month = start_month + step
    end_year = year + (end_month - 1) // 12
    end_month = (end_month - 1) % 12 + 1
    end = datetime(end_year, end_month, 1, tzinfo=tz)
    return start, end


def _period_label(start: datetime, frequency: str) -> str:
    if frequency == "monthly":
        return start.strftime("%Y-%m")
    if frequency == "quarterly":
        return f"{start.year}-Q{(start.month - 1) // 3 + 1}"
    return str(start.year)


def observation_alignment(episode: Episode, frequency: str) -> ObservationAlignment:
    """Derive how ``episode`` lands on the observation grid of ``frequency``.

    Pure arithmetic on the episode window: which observation periods the
    window touches, whether it straddles a boundary, and what share of a
    period it occupies. This is the machine-checkable half of RQ3's
    blind-spot claim - the construct gap (no catalog indicator measures
    operational continuity at all) is documented, not computed.
    """
    if frequency not in FREQUENCIES:
        raise ValueError(f"frequency must be one of {FREQUENCIES}")

    periods: list[datetime] = []
    cursor, limit = episode.start, episode.end
    while cursor < limit:
        period_start, period_end = _period_bounds(cursor, frequency)
        periods.append(period_start)
        cursor = period_end

    start_period, start_period_end = _period_bounds(episode.start, frequency)
    period_hours = (start_period_end - start_period).total_seconds() / 3600.0

    return ObservationAlignment(
        frequency=frequency,
        periods_spanned=tuple(_period_label(p, frequency) for p in periods),
        boundary_straddled=len(periods) > 1,
        duration_share_of_period=episode.duration_hours / period_hours,
    )


def alignment_report(
    episodes: tuple[Episode, ...],
) -> dict[str, dict[str, ObservationAlignment]]:
    """Alignment of every episode against every catalog frequency."""
    return {
        e.episode_id: {
            frequency: observation_alignment(e, frequency) for frequency in FREQUENCIES
        }
        for e in episodes
    }


__all__ = [
    "CHINA_STANDARD_TIME",
    "EPISODES",
    "EPISODE_EVIDENCE_LABEL",
    "EPISODE_KINDS",
    "Episode",
    "ObservationAlignment",
    "alignment_report",
    "episodes_in_window",
    "observation_alignment",
    "outage_hours_by_year",
    "validate_registry",
]
