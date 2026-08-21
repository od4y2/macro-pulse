"""Raw-store persistence for fetched connector series (unit S04).

Connectors write raw observations only (data flow locked in S03);
normalization is S06's job.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from macropulse.connectors.fred import FetchedPoint, FetchedSeries
from macropulse.db.models import Country, Indicator, RawObservation, SourceCatalogEntry


class PersistError(RuntimeError):
    """Raised when reference data needed for the raw write is missing."""


def _resolve_source(
    session: Session, series: FetchedSeries, indicator_id: str
) -> SourceCatalogEntry:
    """Find or create the source_catalog row for this fetch."""
    entry = (
        session.query(SourceCatalogEntry)
        .filter_by(system="fred", code=series.series_id, role="primary")
        .one_or_none()
    )
    if entry is not None:
        return entry
    indicator = session.get(Indicator, indicator_id)
    if indicator is None:
        raise PersistError(f"indicator {indicator_id!r} not registered")
    entry = SourceCatalogEntry(
        system="fred",
        code=series.series_id,
        role="primary",
        # live fetches verify the code exists; mocked fetches do not
        verified="confirmed" if series.evidence_label == "real" else "unverified",
        coverage="per-fetch; see raw payloads for actual coverage",
        indicator_id=indicator_id,
    )
    session.add(entry)
    session.flush()
    return entry


def persist_raw_series(
    session: Session, series: FetchedSeries, indicator_id: str
) -> list[RawObservation]:
    """Write one fetched series into raw_observations.

    Requires the country and indicator to already exist (reference data is
    seeded deliberately, never silently invented). Raises PersistError if
    they are missing.
    """
    country = session.get(Country, series.country_iso3)
    if country is None:
        raise PersistError(f"country {series.country_iso3!r} not registered")
    source = _resolve_source(session, series, indicator_id)

    rows: list[RawObservation] = []
    for point in series.points:
        rows.append(
            RawObservation(
                source_id=source.id,
                country_iso3=series.country_iso3,
                indicator_id=indicator_id,
                period=point.period,
                value=point.value,
                retrieved_at=series.retrieval_time,
                payload={
                    "series_id": series.series_id,
                    "evidence_label": series.evidence_label,
                    "vintage": point.vintage.isoformat(),
                    "missing_reason": point.missing_reason,
                    "raw_payload": series.raw_payload,
                },
            )
        )
    session.add_all(rows)
    session.flush()
    return rows


def point_is_missing(point: FetchedPoint) -> bool:
    return point.value is None
