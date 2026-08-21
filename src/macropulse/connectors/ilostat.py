"""ILOSTAT SDMX connector (unit S05).

Uses the ILOSTAT SDMX 3.0 REST API (no key) with CSV format, which returns
rich per-observation metadata (REF_AREA, SEX, OBS_STATUS, SOURCE,
UNIT_MEASURE, dataflow version) that we preserve verbatim in the raw payload.

Verified dataflow codes (live audit 2026-08-19, see evidence/S05):
- ``DF_SDG_0852_SEX_AGE_RT`` - unemployment rate by sex and age (SDG 8.5.2)
- ``DF_EIP_NEET_SEX_RT``     - NEET rate by sex (EIP)

Provenance notes:
- Only annual TIME_PERIODs are accepted; other frequencies raise rather
  than being silently coerced.
- Empty OBS_VALUE becomes explicit missingness (``ilostat_missing_value``).
- ``vintage`` is the retrieval date (SDMX CSV carries no release timestamp);
  ``release_time`` equals ``retrieval_time`` - documented limitation for S07.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime

import httpx

from macropulse.connectors.base import (
    ConnectorError,
    FetchedPoint,
    FetchedSeries,
)

ILOSTAT_BASE_URL = "https://sdmx.ilo.org/rest"

ILO_MISSING_REASON = "ilostat_missing_value"

# Sex code for totals (ILOSTAT classification SEX_T).
SEX_TOTAL = "SEX_T"


def parse_ilostat_csv(
    payload: str, dataflow: str, ref_area: str, sex: str = SEX_TOTAL
) -> list[FetchedPoint]:
    """Parse an ILOSTAT SDMX CSV data response, filtered to one area and sex.

    Only annual rows (``FREQ == "A"``) are in scope; dataflows mixing
    frequencies (e.g. DF_EIP_NEET_SEX_RT carries quarterly rows) are filtered
    by their own FREQ dimension rather than raising. This is frequency-scope
    filtering, not hidden missingness: skipped rows are other frequencies,
    not absent values.
    """
    reader = csv.DictReader(io.StringIO(payload))
    if reader.fieldnames is None or "OBS_VALUE" not in reader.fieldnames:
        raise ConnectorError(f"{dataflow}: response is not ILOSTAT CSV data")

    points: list[FetchedPoint] = []
    for row in reader:
        if row.get("REF_AREA") != ref_area or row.get("SEX") != sex:
            continue
        if row.get("FREQ") != "A":
            continue
        time_period = str(row.get("TIME_PERIOD") or "")
        try:
            year = int(time_period)
            period = date(year, 1, 1)
        except ValueError as exc:
            raise ConnectorError(
                f"{dataflow}: non-annual TIME_PERIOD {time_period!r} "
                "in an annual (FREQ=A) row"
            ) from exc
        raw_value = (row.get("OBS_VALUE") or "").strip()
        if raw_value == "":
            points.append(
                FetchedPoint(period=period, value=None,
                             missing_reason=ILO_MISSING_REASON, vintage=period)
            )
        else:
            try:
                value = float(raw_value)
            except ValueError as exc:
                raise ConnectorError(
                    f"{dataflow}: non-numeric OBS_VALUE {raw_value!r}"
                ) from exc
            points.append(
                FetchedPoint(period=period, value=value,
                             missing_reason=None, vintage=period)
            )

    if not points:
        raise ConnectorError(
            f"{dataflow}: no rows for ref_area={ref_area} sex={sex} - "
            "check the dataflow code or filters"
        )
    return points


class IlostatConnector:
    """Fetches one ILOSTAT dataflow, filtered to one country (and sex).

    ``transport`` lets tests inject an ``httpx.MockTransport``; ``base_url``
    supports offline fixtures.
    """

    def __init__(self, base_url: str = ILOSTAT_BASE_URL,
                 transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    def fetch_dataflow(
        self,
        dataflow: str,
        country_iso3: str,
        sex: str = SEX_TOTAL,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> FetchedSeries:
        if not dataflow or not dataflow.strip():
            raise ConnectorError("dataflow must be non-empty")
        if len(country_iso3) != 3 or not country_iso3.isalpha() or not country_iso3.isupper():
            raise ConnectorError(f"invalid ISO3 country code: {country_iso3!r}")

        retrieval_time = datetime.now(UTC)
        params: dict[str, str] = {"format": "csvfile"}
        if start_year is not None:
            params["startPeriod"] = str(start_year)
        if end_year is not None:
            params["endPeriod"] = str(end_year)

        url = f"{self._base_url}/data/ILO,{dataflow},all"
        # Full-dataflow CSVs are large (all countries x all dimensions);
        # a long read timeout is required (S05 live audit finding).
        with httpx.Client(transport=self._transport, timeout=180.0) as client:
            response = client.get(url, params=params)
        if response.status_code != 200:
            raise ConnectorError(
                f"{dataflow}: HTTP {response.status_code} from ILOSTAT"
            )
        payload = response.text

        points = parse_ilostat_csv(payload, dataflow, country_iso3, sex)
        if start_year is not None:
            points = [p for p in points if p.period.year >= start_year]
        if end_year is not None:
            points = [p for p in points if p.period.year <= end_year]

        return FetchedSeries(
            system="ilostat",
            series_id=dataflow,
            country_iso3=country_iso3,
            evidence_label="real",
            retrieval_time=retrieval_time,
            points=tuple(points),
            raw_payload=payload,
        )
