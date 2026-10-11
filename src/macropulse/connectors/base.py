"""Shared connector types (unit S04/S05)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


class ConnectorError(RuntimeError):
    """Raised when a source response cannot be trusted or parsed."""


class RetryableFetchError(ConnectorError):
    """A fetch failure that is worth retrying: HTTP 5xx or 429 (server-side
    or rate-limit conditions that typically clear within seconds).

    Subclasses ConnectorError so existing except-clauses keep working; the
    S17 retry boundary distinguishes it to decide whether another attempt
    can help. Client errors (4xx) and parse failures stay plain
    ConnectorError - retrying those would only repeat the same result.
    """


# HTTP statuses the retry boundary treats as transient (S17). 429 is
# rate-limiting; 5xx are provider-side failures. Everything else (4xx,
# parse errors) is a permanent failure for this request.
RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})


def http_error(status_code: int, system: str, code: str) -> ConnectorError:
    """Raise the right error class for a non-200 provider response."""
    if status_code in RETRYABLE_HTTP_STATUSES:
        return RetryableFetchError(f"{code}: HTTP {status_code} from {system}")
    return ConnectorError(f"{code}: HTTP {status_code} from {system}")


@dataclass(frozen=True)
class FetchedPoint:
    period: date
    value: float | None
    missing_reason: str | None
    vintage: date


@dataclass(frozen=True)
class FetchedSeries:
    system: str  # "fred" | "world_bank" | "ilostat"
    series_id: str
    country_iso3: str
    evidence_label: str  # "real" (live) or "mocked" (deterministic fixture)
    retrieval_time: datetime
    points: tuple[FetchedPoint, ...]
    raw_payload: str  # exact provider response, preserved for raw store
