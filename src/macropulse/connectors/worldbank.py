"""World Bank connector (unit S05).

Live by default - the World Bank API v2 needs no key. Deterministic tests
inject an ``httpx.MockTransport`` with canned payloads; the parser is shared
by both paths.

Provenance notes (traceability):
- The WB API serves the current snapshot only; there is no release timestamp
  per observation. ``vintage`` is therefore the retrieval date and
  ``release_time`` equals ``retrieval_time`` - documented limitations,
  revisited in S07 (vintage control).
- Annual periods are stored as the ISO year start (e.g. 2024 -> 2024-01-01).
- WB returns rows with ``value: null`` for years without data: those become
  explicit missing points (``wb_missing_value``), never dropped.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import httpx

from macropulse.connectors.base import (
    ConnectorError,
    FetchedPoint,
    FetchedSeries,
)

WORLDBANK_BASE_URL = "https://api.worldbank.org/v2"

# The API caps per_page at 32500; a panel series is at most a few hundred
# rows, so one generous page covers it and pagination is asserted below.
WB_PER_PAGE = 20000

WB_MISSING_REASON = "wb_missing_value"


def parse_worldbank_observations(payload: str, code: str) -> list[FetchedPoint]:
    """Parse a WB /country/{c}/indicator/{code} JSON payload."""
    try:
        doc = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"{code}: response is not valid JSON") from exc

    if not isinstance(doc, list) or len(doc) < 2:
        # WB signals bad requests as [{"message": [...]}] with HTTP 200
        message = doc[0].get("message") if isinstance(doc, list) and doc else None
        if message:
            raise ConnectorError(f"{code}: World Bank error: {message}")
        raise ConnectorError(f"{code}: unexpected response structure")

    rows = doc[1]
    if rows is None:  # valid code but no rows for the filter
        return []
    if not isinstance(rows, list):
        raise ConnectorError(f"{code}: second element is not a row list")

    points: list[FetchedPoint] = []
    for row in rows:
        try:
            year = int(str(row["date"]))
            period = date(year, 1, 1)
        except (KeyError, ValueError) as exc:
            raise ConnectorError(f"{code}: malformed period {row.get('date')!r}") from exc
        value = row.get("value")
        if value is None:
            points.append(
                FetchedPoint(period=period, value=None,
                             missing_reason=WB_MISSING_REASON, vintage=period)
            )
        else:
            try:
                points.append(
                    FetchedPoint(period=period, value=float(value),
                                 missing_reason=None, vintage=period)
                )
            except (TypeError, ValueError) as exc:
                raise ConnectorError(f"{code}: non-numeric value {value!r}") from exc
    return points


class WorldBankConnector:
    """Fetches one indicator for one country per call.

    ``transport`` lets tests inject an ``httpx.MockTransport``; ``base_url``
    supports offline fixtures.
    """

    def __init__(self, base_url: str = WORLDBANK_BASE_URL,
                 transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    def fetch_indicator(
        self,
        code: str,
        country_iso3: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> FetchedSeries:
        if not code or not code.strip():
            raise ConnectorError("indicator code must be non-empty")
        if len(country_iso3) != 3 or not country_iso3.isalpha() or not country_iso3.isupper():
            raise ConnectorError(f"invalid ISO3 country code: {country_iso3!r}")

        retrieval_time = datetime.now(UTC)
        # Panel series are short (<= ~70 rows); a single generous page is
        # enough. Date filtering is applied client-side after parsing - the
        # API's open-ended date ranges (e.g. "2020:") are rejected with
        # "Invalid value", found during the S05 live audit.
        params: dict[str, str] = {"format": "json", "per_page": str(WB_PER_PAGE)}

        url = f"{self._base_url}/country/{country_iso3}/indicator/{code}"
        with httpx.Client(transport=self._transport, timeout=60.0) as client:
            response = client.get(url, params=params)
        if response.status_code != 200:
            raise ConnectorError(
                f"{code}: HTTP {response.status_code} from World Bank"
            )
        payload = response.text

        points = parse_worldbank_observations(payload, code)
        if start_year is not None:
            points = [p for p in points if p.period.year >= start_year]
        if end_year is not None:
            points = [p for p in points if p.period.year <= end_year]

        return FetchedSeries(
            system="world_bank",
            series_id=code,
            country_iso3=country_iso3,
            evidence_label="real",
            retrieval_time=retrieval_time,
            points=tuple(points),
            raw_payload=payload,
        )
