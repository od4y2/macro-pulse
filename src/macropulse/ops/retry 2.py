"""Bounded retry boundary for provider fetches (unit S17).

Retries exist so a scheduled refresh survives transient provider failures
(HTTP 5xx, 429 rate limiting, connection resets) without a human. They are
deliberately BOUNDED: a persistent outage must surface as a recorded
failed series in the run log, not be retried until it silently spans the
next schedule slot.

Constants (documented, not magic):
- ``max_attempts = 3``: one initial try plus two retries. Provider
  rate-limits and blips typically clear within seconds; more attempts
  would only delay surfacing a real outage.
- ``base_delay = 1.0`` s with ``backoff_factor = 2.0``: sleeps of 1 s then
  2 s. Total added latency before giving up is 3 s - far below the daily
  schedule's slack, so a bounded retry can never overlap the next run.

What is retryable (closed classification, ``retryable()``):
- ``RetryableFetchError`` (connector raised on HTTP 429/5xx), and
- ``httpx.TransportError`` (connection refused/reset, timeouts) - raised
  by the HTTP client below the connectors' status checks.
Everything else - 4xx client errors, parse failures, normalization and
persistence errors - is permanent for this request and fails immediately.

Deterministic testing: ``sleep`` is injectable; tests pass a recorder and
assert the exact backoff sequence without real waiting.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from macropulse.connectors.base import FetchedSeries, RetryableFetchError

SleepFn = Callable[[float], None]


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0


DEFAULT_RETRY_POLICY = RetryPolicy()


def retryable(exc: BaseException) -> bool:
    """Classify one exception: True = another attempt may help."""
    if isinstance(exc, RetryableFetchError):
        return True
    return isinstance(exc, httpx.TransportError)


@dataclass(frozen=True)
class RetryOutcome:
    series: FetchedSeries
    attempts: int  # total tries including the successful one
    retried_errors: tuple[str, ...]  # one message per retry that happened


def fetch_with_retries(
    fetch: Callable[[], FetchedSeries],
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    sleep: SleepFn = time.sleep,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
) -> RetryOutcome:
    """Run ``fetch`` with the bounded retry policy.

    Non-retryable errors raise immediately. When every attempt fails, the
    LAST exception is re-raised (the caller records its message).
    """
    if policy.max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    retried: list[str] = []
    for attempt in range(1, policy.max_attempts + 1):
        try:
            series = fetch()
        except Exception as exc:
            if attempt == policy.max_attempts or not retryable(exc):
                raise
            delay = policy.base_delay * (policy.backoff_factor ** (attempt - 1))
            retried.append(str(exc))
            if on_retry is not None:
                on_retry(attempt, delay, exc)
            sleep(delay)
            continue
        return RetryOutcome(
            series=series, attempts=attempt, retried_errors=tuple(retried)
        )
    raise AssertionError("unreachable")  # pragma: no cover


__all__ = [
    "DEFAULT_RETRY_POLICY",
    "RetryOutcome",
    "RetryPolicy",
    "fetch_with_retries",
    "retryable",
]
