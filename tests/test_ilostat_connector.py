"""Tests for the ILOSTAT SDMX connector (unit S05). Deterministic: MockTransport only."""

from __future__ import annotations

import httpx
import pytest

from macropulse.connectors.base import ConnectorError
from macropulse.connectors.ilostat import IlostatConnector, parse_ilostat_csv
from macropulse.connectors.worldbank import WorldBankConnector

CSV_HEADER = (
    "DATAFLOW,REF_AREA,FREQ,MEASURE,SEX,TIME_PERIOD,OBS_VALUE,OBS_STATUS,"
    "UNIT_MEASURE_TYPE,UNIT_MEASURE,UNIT_MULT,SOURCE\n"
)


def _ilo_csv(rows: list[str]) -> str:
    return CSV_HEADER + "".join(row + "\n" for row in rows)


def _connector(handler) -> IlostatConnector:
    return IlostatConnector(transport=httpx.MockTransport(handler))


# --- Normal cases -----------------------------------------------------------

def test_parse_filters_area_and_sex() -> None:
    payload = _ilo_csv([
        "ILO:DF_EIP_NEET_SEX_RT(1.0),USA,A,EIP_NEET_RT,SEX_T,2023,12.3,,RT,PT,0,LFS",
        "ILO:DF_EIP_NEET_SEX_RT(1.0),USA,A,EIP_NEET_RT,SEX_M,2023,13.1,,RT,PT,0,LFS",
        "ILO:DF_EIP_NEET_SEX_RT(1.0),AGO,A,EIP_NEET_RT,SEX_T,2023,20.0,,RT,PT,0,LFS",
    ])
    points = parse_ilostat_csv(payload, "DF_EIP_NEET_SEX_RT", "USA")
    assert len(points) == 1  # only USA + SEX_T
    assert points[0].value == 12.3
    assert points[0].period.isoformat() == "2023-01-01"


def test_live_mode_labels_real_and_builds_url() -> None:
    payload = _ilo_csv([
        "ILO:DF_SDG_0852_SEX_AGE_RT(1.0),USA,A,SDG_0852_RT,SEX_T,2024,8.1,,RT,PT,0,LFS",
    ])
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, text=payload)

    series = _connector(handler).fetch_dataflow(
        "DF_SDG_0852_SEX_AGE_RT", "USA", start_year=2024
    )
    assert series.system == "ilostat"
    assert series.evidence_label == "real"
    assert "data/ILO,DF_SDG_0852_SEX_AGE_RT,all" in captured["url"]
    assert "format=csvfile" in captured["url"]
    assert [p.value for p in series.points] == [8.1]


# --- Boundary cases ----------------------------------------------------------

def test_empty_obs_value_is_explicit_missing() -> None:
    payload = _ilo_csv([
        "ILO:DF_EIP_NEET_SEX_RT(1.0),USA,A,EIP_NEET_RT,SEX_T,2023,,,RT,PT,0,LFS",
        "ILO:DF_EIP_NEET_SEX_RT(1.0),USA,A,EIP_NEET_RT,SEX_T,2024,11.0,,RT,PT,0,LFS",
    ])
    points = parse_ilostat_csv(payload, "DF_EIP_NEET_SEX_RT", "USA")
    assert points[0].value is None
    assert points[0].missing_reason == "ilostat_missing_value"
    assert points[1].value == 11.0


def test_year_window_filters() -> None:
    payload = _ilo_csv([
        f"ILO:DF_EIP_NEET_SEX_RT(1.0),USA,A,EIP_NEET_RT,SEX_T,{y},1.0,,RT,PT,0,LFS"
        for y in (2022, 2023, 2024)
    ])
    points = parse_ilostat_csv(payload, "DF_EIP_NEET_SEX_RT", "USA")
    assert [p.period.year for p in points] == [2022, 2023, 2024]


# --- Missing cases -----------------------------------------------------------

def test_no_matching_rows_raises() -> None:
    payload = _ilo_csv([
        "ILO:DF_EIP_NEET_SEX_RT(1.0),AGO,A,EIP_NEET_RT,SEX_T,2023,20.0,,RT,PT,0,LFS",
    ])
    with pytest.raises(ConnectorError, match="no rows for ref_area=USA"):
        parse_ilostat_csv(payload, "DF_EIP_NEET_SEX_RT", "USA")


# --- Invalid cases -----------------------------------------------------------

def test_non_csv_payload_raises() -> None:
    with pytest.raises(ConnectorError, match="not ILOSTAT CSV"):
        parse_ilostat_csv("<html>error</html>", "DF_X", "USA")


def test_non_annual_rows_filtered_by_freq() -> None:
    # dataflows mixing frequencies: quarterly rows are out of scope, not hidden
    payload = _ilo_csv([
        "ILO:DF_X(1.0),USA,A,X,SEX_T,2023,5.0,,RT,PT,0,LFS",
        "ILO:DF_X(1.0),USA,Q,X,SEX_T,2023-Q1,5.1,,RT,PT,0,LFS",
        "ILO:DF_X(1.0),USA,M,X,SEX_T,2023-01,5.2,,RT,PT,0,LFS",
    ])
    points = parse_ilostat_csv(payload, "DF_X", "USA")
    assert len(points) == 1
    assert points[0].period.year == 2023


def test_annual_row_with_bad_period_still_raises() -> None:
    payload = _ilo_csv([
        "ILO:DF_X(1.0),USA,A,X,SEX_T,20x3,5.0,,RT,PT,0,LFS",
    ])
    with pytest.raises(ConnectorError, match="non-annual"):
        parse_ilostat_csv(payload, "DF_X", "USA")


def test_non_numeric_value_raises() -> None:
    payload = _ilo_csv([
        "ILO:DF_X(1.0),USA,A,X,SEX_T,2023,abc,,RT,PT,0,LFS",
    ])
    with pytest.raises(ConnectorError, match="non-numeric"):
        parse_ilostat_csv(payload, "DF_X", "USA")


def test_invalid_inputs_rejected() -> None:
    with pytest.raises(ConnectorError, match="dataflow must be non-empty"):
        IlostatConnector().fetch_dataflow("  ", "USA")
    with pytest.raises(ConnectorError, match="invalid ISO3"):
        IlostatConnector().fetch_dataflow("DF_X", "usa")


def test_http_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    with pytest.raises(ConnectorError, match="HTTP 404"):
        _connector(handler).fetch_dataflow("DF_X", "USA")


# --- Persistence (live DB via shared conftest fixture; auto-skips) -----------

def _seed(session, indicator_id="neet_rate"):
    from macropulse.db.models import Country, Indicator

    session.merge(Country(iso3="USA", name="United States", rationale="benchmark"))
    session.merge(
        Indicator(
            indicator_id=indicator_id, name="NEET rate",
            module="labor-slack-youth", unit="percent", frequency="annual",
            seasonal_adjustment="not_seasonally_adjusted",
            fallback_status="primary-and-fallback",
            comparability_notes="n/a", limitations="n/a",
        )
    )
    session.commit()


def test_persist_worldbank_series(session) -> None:
    from macropulse.db.models import RawObservation, SourceCatalogEntry

    _seed(session)
    payload = '[{"page":1},[{"date":"2023","value":12.3}]]'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payload)

    series = WorldBankConnector(
        transport=httpx.MockTransport(handler)
    ).fetch_indicator("SL.UEM.NEET.ZS", "USA")
    from macropulse.connectors.persist import persist_raw_series

    rows = persist_raw_series(session, series, "neet_rate")
    session.commit()

    assert len(rows) == 1
    src = session.query(SourceCatalogEntry).filter_by(system="world_bank").one()
    assert src.verified == "confirmed"  # live-labelled fetch
    stored = session.query(RawObservation).one()
    assert stored.payload["evidence_label"] == "real"
    assert stored.payload["raw_payload"] == payload
