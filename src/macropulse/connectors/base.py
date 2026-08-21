"""Shared connector types (unit S04/S05)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


class ConnectorError(RuntimeError):
    """Raised when a source response cannot be trusted or parsed."""


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
