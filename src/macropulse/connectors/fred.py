"""FRED connector vertical slice (unit S04).

One traceable path: FRED series/observations endpoint -> parsed points with
provenance -> raw observation store.

Modes:
- **live** (api key present): real HTTP call to api.stlouisfed.org; every
  point is labelled ``real``.
- **no-key** (deterministic): a canned FRED-shaped JSON fixture is run
  through the exact same parser; every point is labelled ``mocked``. Values
  are obviously-round placeholders, never presented as observed data.

Provenance notes (traceability):
- ``vintage`` is the observation's ``realtime_start`` from FRED.
- FRED's plain observations endpoint does not expose first-release
  timestamps, so ``release_time`` is set equal to ``retrieval_time`` and the
  limitation is recorded here and in the S02 catalog limitations. True
  vintage/release history is available via ALFRED realtime queries, which
  ``fetch_series(realtime_start=..., realtime_end=...)`` enables (S07): the
  same endpoint restricted to a realtime window returns the values as they
  were known in that window, so repeated calls build a vintage chain where
  the same period legitimately appears under multiple vintages.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any

import httpx

from macropulse.connectors.base import (
    ConnectorError,
    FetchedPoint,
    FetchedSeries,
    http_error,
)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# FRED marks missing observations with a literal "." in the value field.
FRED_MISSING_VALUE = "."

# Default country for FRED series: FRED codes in the S02 catalog are
# US series or mirrors. Non-US mirrors must pass country_iso3 explicitly.
FRED_DEFAULT_COUNTRY = "USA"


def parse_fred_observations(payload: str, series_id: str) -> list[FetchedPoint]:
    """Parse a FRED series/observations JSON payload.

    Raises ConnectorError on structural problems; treats FRED's "." values
    as explicit missingness rather than dropping the point (no hidden
    missingness).
    """
    try:
        doc = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"{series_id}: response is not valid JSON") from exc

    if "error_message" in doc:
        raise ConnectorError(f"{series_id}: FRED error: {doc['error_message']}")

    observations = doc.get("observations")
    if not isinstance(observations, list):
        raise ConnectorError(f"{series_id}: response has no observations list")

    points: list[FetchedPoint] = []
    for obs in observations:
        try:
            period = date.fromisoformat(str(obs["date"]))
            vintage = date.fromisoformat(str(obs["realtime_start"]))
            raw_value = str(obs["value"])
        except (KeyError, ValueError) as exc:
            raise ConnectorError(f"{series_id}: malformed observation {obs!r}") from exc
        if raw_value == FRED_MISSING_VALUE:
            points.append(
                FetchedPoint(
                    period=period,
                    value=None,
                    missing_reason="fred_missing_value",
                    vintage=vintage,
                )
            )
        else:
            try:
                value = float(raw_value)
            except ValueError as exc:
                raise ConnectorError(
                    f"{series_id}: non-numeric value {raw_value!r}"
                ) from exc
            points.append(
                FetchedPoint(
                    period=period, value=value, missing_reason=None, vintage=vintage
                )
            )
    return points


# Deterministic no-key fixture. FRED-shaped JSON, obviously-round values,
# one explicit missing value. Never labelled "real".
NO_KEY_FIXTURE: dict[str, Any] = {
    "realtime_start": "2025-01-01",
    "realtime_end": "9999-12-31",
    "observations": [
        {"date": "2024-01-01", "realtime_start": "2024-02-02", "value": "4.0"},
        {"date": "2024-02-01", "realtime_start": "2024-03-02", "value": "4.1"},
        {"date": "2024-03-01", "realtime_start": "2024-04-05", "value": "4.2"},
        {"date": "2024-04-01", "realtime_start": "2024-05-03", "value": "."},
        {"date": "2024-05-01", "realtime_start": "2024-06-07", "value": "4.3"},
    ],
}


class FredConnector:
    """Fetches one FRED series at a time.

    ``api_key``: explicit key, else ``FRED_API_KEY`` env var, else None
    (deterministic no-key mode). ``transport`` allows tests to inject an
    httpx.MockTransport for live-mode tests without network access.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = FRED_BASE_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        import os

        self._api_key = (
            api_key if api_key is not None else os.environ.get("FRED_API_KEY")
        )
        self._base_url = base_url
        self._transport = transport

    @property
    def live(self) -> bool:
        return self._api_key is not None

    def fetch_series(
        self,
        series_id: str,
        country_iso3: str = FRED_DEFAULT_COUNTRY,
        observation_start: date | None = None,
        observation_end: date | None = None,
        realtime_start: date | None = None,
        realtime_end: date | None = None,
    ) -> FetchedSeries:
        """Fetch one FRED series.

        ``realtime_start``/``realtime_end`` restrict the result to the
        ALFRED realtime window: values as known during that window. Without
        them FRED returns current values (realtime window = today..9999).
        Realtime queries are live-only: the no-key fixture has no vintage
        dimension, so requesting one without a key is an error rather than
        a silent mock.
        """
        if not series_id or not series_id.strip():
            raise ConnectorError("series_id must be non-empty")
        if not self.live and (realtime_start is not None or realtime_end is not None):
            raise ConnectorError(
                f"{series_id}: realtime (ALFRED) queries require a live API key"
            )

        retrieval_time = datetime.now(UTC)
        if self.live:
            params: dict[str, str] = {
                "series_id": series_id,
                "api_key": self._api_key or "",
                "file_type": "json",
            }
            if observation_start is not None:
                params["observation_start"] = observation_start.isoformat()
            if observation_end is not None:
                params["observation_end"] = observation_end.isoformat()
            if realtime_start is not None:
                params["realtime_start"] = realtime_start.isoformat()
            if realtime_end is not None:
                params["realtime_end"] = realtime_end.isoformat()
            with httpx.Client(transport=self._transport) as client:
                response = client.get(self._base_url, params=params)
            if response.status_code != 200:
                raise http_error(response.status_code, "FRED", series_id)
            payload = response.text
            label = "real"
        else:
            # Deterministic no-key mode: same parser, canned payload.
            payload = json.dumps(NO_KEY_FIXTURE)
            label = "mocked"

        points = parse_fred_observations(payload, series_id)
        if observation_start is not None:
            points = [p for p in points if p.period >= observation_start]
        if observation_end is not None:
            points = [p for p in points if p.period <= observation_end]

        return FetchedSeries(
            system="fred",
            series_id=series_id,
            country_iso3=country_iso3,
            evidence_label=label,
            retrieval_time=retrieval_time,
            points=tuple(points),
            raw_payload=payload,
        )
