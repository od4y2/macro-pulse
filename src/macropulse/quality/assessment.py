"""Validation flags and quality grading (unit S07).

Deterministic, pure rules that assess a normalized series and assign each
record a quality grade plus zero or more validation flags. Full rule
documentation: docs/QualityGovernance.md.

Flag vocabulary (closed set - never invent new codes ad hoc):
- ``missing_value``        the record's value is NULL (explicit missingness,
                           surfaced rather than hidden; never filled here)
- ``series_gap``           a period expected from the series' frequency is
                           entirely absent; the flag is anchored to the
                           latest record BEFORE the gap so it has a
                           traceable observation to attach to
- ``vintage_precedes_period`` the record's vintage is earlier than its own
                           period - impossible release chronology

Grade assignment (closed vocabulary from the S03 API contract,
``QUALITY_GRADES``):
1. any flag on the record                  -> ``flagged``
2. evidence_label is not ``real``          -> ``ungraded``
3. a newer vintage exists for the period   -> ``revised``
4. otherwise                                -> ``official``

``preliminary`` and ``estimated`` are RESERVED: none of the three source
APIs expose release-stage metadata that would justify them, and assigning
them without such metadata would be fabrication. They appear in the
vocabulary so the API contract is complete, but this module never emits
them; if a future source provides release-stage flags, the rule table in
docs/QualityGovernance.md must be updated first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from macropulse.api.schemas import QUALITY_GRADES
from macropulse.catalog import FREQUENCIES

FLAG_MISSING_VALUE = "missing_value"
FLAG_SERIES_GAP = "series_gap"
FLAG_VINTAGE_PRECEDES_PERIOD = "vintage_precedes_period"

_FLAG_CODES = frozenset(
    {FLAG_MISSING_VALUE, FLAG_SERIES_GAP, FLAG_VINTAGE_PRECEDES_PERIOD}
)

# Months per period for each supported frequency. Used only to enumerate
# expected periods; no other constant participates in grading.
_FREQUENCY_STEP_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}


@dataclass(frozen=True)
class QualityFlag:
    flag_code: str
    description: str

    def __post_init__(self) -> None:
        if self.flag_code not in _FLAG_CODES:
            raise ValueError(f"unknown flag code {self.flag_code!r}")


@dataclass(frozen=True)
class RecordAssessment:
    """Grade + flags for one (period, vintage) record."""

    period: date
    vintage: date
    grade: str
    flags: tuple[QualityFlag, ...]


@dataclass(frozen=True)
class SeriesAssessment:
    indicator_id: str
    country_iso3: str
    frequency: str
    records: tuple[RecordAssessment, ...]
    gap_periods: tuple[date, ...] = field(default=())

    @property
    def n_flagged(self) -> int:
        return sum(1 for r in self.records if r.flags)

    def grades_by_period(self) -> dict[date, str]:
        """Latest-vintage grade per period (superseded vintages hidden)."""
        latest: dict[date, tuple[date, str]] = {}
        for r in self.records:
            if r.period not in latest or r.vintage > latest[r.period][0]:
                latest[r.period] = (r.vintage, r.grade)
        return {p: g for p, (_, g) in latest.items()}


def expected_periods(frequency: str, first: date, last: date) -> list[date]:
    """All periods the frequency requires between ``first`` and ``last``
    inclusive, anchored on ``first`` (the series' own phase)."""
    if frequency not in _FREQUENCY_STEP_MONTHS:
        raise ValueError(f"unknown frequency {frequency!r}")
    step = _FREQUENCY_STEP_MONTHS[frequency]
    periods: list[date] = []
    cursor_year, cursor_month = first.year, first.month
    while (cursor_year, cursor_month) <= (last.year, last.month):
        periods.append(date(cursor_year, cursor_month, 1))
        cursor_month += step
        if cursor_month > 12:
            cursor_month -= 12
            cursor_year += 1
    return periods


def _flag_description(flag_code: str, period: date | None = None) -> str:
    if flag_code == FLAG_MISSING_VALUE:
        return "value is NULL; explicit missingness recorded via missing_reason"
    if flag_code == FLAG_SERIES_GAP:
        return f"expected period {period} is absent from the series"
    return "vintage predates the observation period (impossible chronology)"


def assess_series(
    records,
    indicator_id: str,
    country_iso3: str,
    frequency: str,
    superseded: frozenset[tuple[date, date]] = frozenset(),
) -> SeriesAssessment:
    """Assess one normalized series.

    ``records``: any sequence of objects exposing ``period``, ``vintage``,
    ``value``, ``missing_reason``, ``evidence_label`` (both
    ``NormalizedRecord`` from the pipeline and ``NormalizedObservation``
    rows satisfy this).

    ``superseded``: set of ``(period, vintage)`` identities for which a
    newer vintage exists (see quality.vintage.superseded_identities).
    Records in it that are otherwise clean grade ``revised``.
    """
    if frequency not in FREQUENCIES:
        raise ValueError(f"unknown frequency {frequency!r}")

    # Series-level gap detection: expected periods absent entirely.
    present = {r.period for r in records}
    gaps: tuple[date, ...] = ()
    if present:
        first, last = min(present), max(present)
        gaps = tuple(p for p in expected_periods(frequency, first, last) if p not in present)

    # Anchor each gap to the latest record before it (flag FK needs a row).
    gap_flags: dict[date, list[QualityFlag]] = {}
    for gap in gaps:
        anchors = [r for r in records if r.period < gap]
        if not anchors:
            continue  # gap precedes every record; nothing to anchor to
        anchor_period = max(r.period for r in anchors)
        gap_flags.setdefault(anchor_period, []).append(
            QualityFlag(FLAG_SERIES_GAP, _flag_description(FLAG_SERIES_GAP, gap))
        )

    assessments: list[RecordAssessment] = []
    seen: set[tuple[date, date]] = set()
    for r in records:
        identity = (r.period, r.vintage)
        if identity in seen:
            raise ValueError(
                f"duplicate (period, vintage) {identity}; revision history "
                "requires distinct vintages"
            )
        seen.add(identity)

        flags: list[QualityFlag] = list(gap_flags.get(r.period, ()))
        if r.value is None:
            flags.append(
                QualityFlag(
                    FLAG_MISSING_VALUE, _flag_description(FLAG_MISSING_VALUE)
                )
            )
        if r.vintage < r.period:
            flags.append(
                QualityFlag(
                    FLAG_VINTAGE_PRECEDES_PERIOD,
                    _flag_description(FLAG_VINTAGE_PRECEDES_PERIOD),
                )
            )

        if flags:
            grade = "flagged"
        elif r.evidence_label != "real":
            grade = "ungraded"
        elif identity in superseded:
            grade = "revised"
        else:
            grade = "official"

        assessments.append(
            RecordAssessment(period=r.period, vintage=r.vintage, grade=grade, flags=tuple(flags))
        )

    return SeriesAssessment(
        indicator_id=indicator_id,
        country_iso3=country_iso3,
        frequency=frequency,
        records=tuple(assessments),
        gap_periods=gaps,
    )


def validate_grade(grade: str) -> bool:
    return grade in QUALITY_GRADES


__all__ = [
    "FLAG_MISSING_VALUE",
    "FLAG_SERIES_GAP",
    "FLAG_VINTAGE_PRECEDES_PERIOD",
    "QualityFlag",
    "RecordAssessment",
    "SeriesAssessment",
    "assess_series",
    "expected_periods",
    "validate_grade",
]
