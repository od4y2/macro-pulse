"""Refresh-run lifecycle and vocabularies (unit S17).

A run row is the durable operational audit. It is inserted as ``running``
the moment a cycle starts (so a crash leaves visible evidence), updated
per series (progress survives a mid-run crash), and finished with a
terminal status. A ``running`` row that exists when the next run starts
means the previous process died mid-run: it is marked ``interrupted``
rather than deleted - the audit trail keeps failures, it does not
launder them.

Closed vocabularies (drift fails tests):

- triggers: ``manual`` (a human ran the CLI), ``scheduled`` (the daemon
  or cron fired), ``recovery`` (an explicit re-run after a failure).
- statuses: ``running`` -> one of ``succeeded`` (every series ok),
  ``partial`` (some series failed), ``failed`` (every series failed, or
  nothing was planned), or ``interrupted`` (process died mid-run).
- series statuses: ``ok`` / ``failed``.
- failure reasons: ``no_api_key`` (FRED series without a key - the
  refresh layer never falls back to the mocked fixture),
  ``fetch_failed`` (retries exhausted or permanent fetch error),
  ``normalization_error`` (the S06 rules rejected the series),
  ``persist_error`` (the store rejected the write), ``unknown``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from macropulse.db.models import RefreshRun

RUN_TRIGGERS: tuple[str, ...] = ("manual", "scheduled", "recovery")
RUN_STATUSES: tuple[str, ...] = (
    "running",
    "succeeded",
    "partial",
    "failed",
    "interrupted",
)
SERIES_STATUSES: tuple[str, ...] = ("ok", "failed")
FAILURE_REASONS: tuple[str, ...] = (
    "no_api_key",
    "fetch_failed",
    "normalization_error",
    "persist_error",
    "unknown",
)


def start_run(session: Session, trigger: str, series_total: int = 0) -> RefreshRun:
    """Insert the run row in ``running`` state and commit it immediately."""
    if trigger not in RUN_TRIGGERS:
        raise ValueError(f"unknown trigger {trigger!r}; legal: {RUN_TRIGGERS}")
    run = RefreshRun(
        trigger=trigger,
        status="running",
        started_at=datetime.now(UTC),
        series_total=series_total,
        series_failed=0,
        outcomes=[],
    )
    session.add(run)
    session.commit()
    return run


def mark_interrupted_runs(session: Session) -> list[int]:
    """Flip stale ``running`` rows to ``interrupted``; return their ids.

    Called at the start of every run: a ``running`` row still present can
    only be a leftover from a process that died without finishing.
    """
    stale = session.query(RefreshRun).filter(RefreshRun.status == "running").all()
    ids = [r.id for r in stale]
    for run in stale:
        run.status = "interrupted"
        run.finished_at = datetime.now(UTC)
        run.error = (run.error or "") + "marked interrupted: process died mid-run"
    if stale:
        session.commit()
    return ids


def finish_run(
    session: Session,
    run: RefreshRun,
    status: str,
    outcomes: list[dict],
    error: str | None = None,
) -> RefreshRun:
    """Record the terminal state of a run and commit."""
    if status not in RUN_STATUSES or status == "running":
        raise ValueError(f"terminal status required; legal: {RUN_STATUSES[1:]}")
    failed = sum(1 for o in outcomes if o.get("status") == "failed")
    run.status = status
    run.finished_at = datetime.now(UTC)
    run.series_total = len(outcomes)
    run.series_failed = failed
    run.outcomes = outcomes
    run.error = error
    session.commit()
    return run


def classify_run_status(outcomes: list[dict]) -> tuple[str, str | None]:
    """Derive the terminal status from per-series outcomes.

    Returns (status, error) - error is set only when nothing ran at all.
    """
    if not outcomes:
        return "failed", "no series planned (empty plan or all filtered out)"
    failed = sum(1 for o in outcomes if o.get("status") == "failed")
    if failed == 0:
        return "succeeded", None
    if failed == len(outcomes):
        return "failed", f"all {failed} series failed"
    return "partial", f"{failed} of {len(outcomes)} series failed"


__all__ = [
    "FAILURE_REASONS",
    "RUN_STATUSES",
    "RUN_TRIGGERS",
    "SERIES_STATUSES",
    "classify_run_status",
    "finish_run",
    "mark_interrupted_runs",
    "start_run",
]
