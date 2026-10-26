"""Vintage control and revision history (unit S07).

Revision transparency is RQ4's core requirement: for any (indicator,
country, period) the system must be able to show every value ever stored,
labelled with the vintage it was retrieved under. Nothing here mutates
history - older vintages are kept verbatim and merely graded ``revised``
when a newer vintage supersedes them.

Revision semantics:
- A **revision** exists whenever two vintages of the same
  (indicator, country, period) carry different payloads - either different
  values, or value <-> missing transitions.
- The **delta** between consecutive vintages is the absolute and (when both
  values exist and the base is non-zero) the relative change. A zero base
  yields ``relative=None`` rather than a fabricated infinity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from macropulse.db.models import DataQualityFlag, NormalizedObservation
from macropulse.quality.assessment import SeriesAssessment, assess_series


@dataclass(frozen=True)
class RevisionStep:
    """One stored observation of a (indicator, country, period) identity."""

    observation_id: int
    vintage: date
    value: float | None
    missing_reason: str | None
    evidence_label: str
    source_id: int


@dataclass(frozen=True)
class Revision:
    """The change from one vintage to the next for one period."""

    period: date
    from_vintage: date
    to_vintage: date
    from_value: float | None
    to_value: float | None
    absolute: float | None
    relative: float | None  # None when either side is missing or base is 0


def revision_history(
    session, indicator_id: str, country_iso3: str
) -> dict[date, list[RevisionStep]]:
    """All stored vintages per period, oldest first. Read-only."""
    rows = (
        session.query(NormalizedObservation)
        .filter_by(indicator_id=indicator_id, country_iso3=country_iso3)
        .order_by(NormalizedObservation.period, NormalizedObservation.vintage)
        .all()
    )
    history: dict[date, list[RevisionStep]] = {}
    for row in rows:
        history.setdefault(row.period, []).append(
            RevisionStep(
                observation_id=row.id,
                vintage=row.vintage,
                value=float(row.value) if row.value is not None else None,
                missing_reason=row.missing_reason,
                evidence_label=row.evidence_label,
                source_id=row.source_id,
            )
        )
    return history


def revision_deltas(
    history: dict[date, list[RevisionStep]]
) -> list[Revision]:
    """Changes between consecutive vintages of each period, in period order.

    Pure computation over the history mapping; no DB access, so it is
    unit-testable without Postgres.
    """
    revisions: list[Revision] = []
    for period in sorted(history):
        steps = sorted(history[period], key=lambda s: s.vintage)
        for prev, nxt in pairwise(steps):
            if prev.value is not None and nxt.value is not None:
                absolute = nxt.value - prev.value
                relative = absolute / prev.value if prev.value != 0 else None
            else:
                absolute = None
                relative = None
            revisions.append(
                Revision(
                    period=period,
                    from_vintage=prev.vintage,
                    to_vintage=nxt.vintage,
                    from_value=prev.value,
                    to_value=nxt.value,
                    absolute=absolute,
                    relative=relative,
                )
            )
    return revisions


def superseded_identities(
    session, indicator_id: str, country_iso3: str
) -> frozenset[tuple[date, date]]:
    """(period, vintage) identities that a newer vintage has superseded."""
    rows = (
        session.query(NormalizedObservation)
        .filter_by(indicator_id=indicator_id, country_iso3=country_iso3)
        .all()
    )
    latest_by_period: dict[date, date] = {}
    for row in rows:
        latest = latest_by_period.get(row.period)
        if latest is None or row.vintage > latest:
            latest_by_period[row.period] = row.vintage
    return frozenset(
        (row.period, row.vintage)
        for row in rows
        if latest_by_period[row.period] > row.vintage
    )


def apply_assessment(
    session, rows: list[NormalizedObservation], assessment: SeriesAssessment
) -> None:
    """Persist grades and flags for previously stored rows.

    Rows are matched to assessments by (period, vintage). The quality_grade
    column is UPDATED (grading is a judgement, not identity); flags are
    INSERTED (audit trail - re-running adds new rows, history is never
    deleted). Callers should run this once per fetch/grade cycle.
    """
    by_identity = {(r.period, r.vintage): r for r in rows}
    for record in assessment.records:
        row = by_identity.get((record.period, record.vintage))
        if row is None:
            continue
        row.quality_grade = record.grade
        for flag in record.flags:
            session.add(
                DataQualityFlag(
                    normalized_observation_id=row.id,
                    flag_code=flag.flag_code,
                    description=flag.description,
                )
            )
    session.flush()


def assess_and_apply(
    session, indicator_id: str, country_iso3: str
) -> SeriesAssessment:
    """Load a stored series, assess it (with superseded detection), persist
    grades + flags, and return the assessment."""
    rows = (
        session.query(NormalizedObservation)
        .filter_by(indicator_id=indicator_id, country_iso3=country_iso3)
        .order_by(NormalizedObservation.period)
        .all()
    )
    if not rows:
        raise ValueError(f"no stored series for {indicator_id}/{country_iso3}")
    # Frequency is a series-level property; the stored rows all share it.
    frequency = rows[0].frequency
    superseded = superseded_identities(session, indicator_id, country_iso3)
    assessment = assess_series(
        rows, indicator_id, country_iso3, frequency, superseded
    )
    apply_assessment(session, rows, assessment)
    return assessment


__all__ = [
    "Revision",
    "RevisionStep",
    "apply_assessment",
    "assess_and_apply",
    "revision_deltas",
    "revision_history",
    "superseded_identities",
]
