"""Stdlib daily scheduler for the refresh layer (unit S17).

The Architecture baseline allows "APScheduler or platform cron"; this unit
implements the third, zero-dependency option: a small loop over the
stdlib clock. Rationale (recorded in docs/decisions.md): pip transfers
on this network have failed on large wheels before (S14), APScheduler
would add a dependency for what is one date computation plus ``sleep``,
and a platform cron alone would leave nothing testable in the repository.
The loop is fully deterministic under test via injected ``now_fn`` and
``sleep_fn``.

**The cadence is a polling convention, NOT a release-schedule claim.**
Daily at 06:00 UTC means "the job checks providers once a day, early UTC
morning" - it asserts nothing about when providers publish, because the
release calendar is unpopulated by the S07 decision (no fabricated
expected-release dates). Providers that publish mid-day are picked up at
the next cycle; freshness is computed from observation dates (S15), not
from this schedule.

Convention: a cycle runs immediately when the daemon starts (freshness
ASAP), then at each daily slot. ``next_run_at`` returns the slot STRICTLY
AFTER ``now`` - a run at exactly 06:00:00 schedules the next for the
following day.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

# (hour, minute) UTC - see module docstring for the convention.
DAILY_REFRESH_UTC = (6, 0)


def next_run_at(now: datetime) -> datetime:
    """The next daily slot strictly after ``now`` (result in UTC)."""
    now = now.astimezone(UTC)
    hour, minute = DAILY_REFRESH_UTC
    slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if slot <= now:
        slot += timedelta(days=1)
    return slot


def run_forever(
    job: Callable[[], object],
    logger=None,
    now_fn: Callable[[], datetime] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    stop_after: int | None = None,
) -> int:
    """Run ``job`` immediately, then once per daily slot, forever.

    ``stop_after`` bounds the number of job executions (tests only).
    Returns the number of job executions performed. With no ``logger``,
    no log events are emitted (the pure loop stays silent).
    """
    from macropulse.ops.logging_setup import log_event

    if now_fn is None:
        now_fn = lambda: datetime.now(UTC)
    iterations = 0
    if logger is not None:
        log_event(
            logger,
            "info",
            "daemon_started",
            daily_at=f"{DAILY_REFRESH_UTC[0]:02d}:{DAILY_REFRESH_UTC[1]:02d} UTC",
            note="polling convention, not a release-schedule claim",
        )
    while stop_after is None or iterations < stop_after:
        job()
        iterations += 1
        if stop_after is not None and iterations >= stop_after:
            break
        now = now_fn()
        upcoming = next_run_at(now)
        delay = (upcoming - now).total_seconds()
        if logger is not None:
            log_event(
                logger,
                "info",
                "daemon_sleep",
                until=upcoming.isoformat(),
                seconds=delay,
            )
        sleep_fn(delay)
    return iterations


__all__ = ["DAILY_REFRESH_UTC", "next_run_at", "run_forever"]
