"""Tests for the World Bank connector (unit S05). Deterministic: MockTransport only."""

from __future__ import annotations

import json

import httpx
import pytest

from macropulse.connectors.base import ConnectorError
from macropulse.connectors.worldbank import (
    WorldBankConnector,
    parse_worldbank_observations,
)


def _wb_payload(rows: list[dict] | None) -> str:
    return json.dumps([{"page": 1, "pages": 1, "per_page": 5, "total": len(rows or [])}, rows])


def _connector(handler) -> WorldBankConnector:
    return WorldBankConnector(transport=httpx.MockTransport(handler))


# --- Normal cases -----------------------------------------------------------

def test_parse_normal_rows() -> None:
    payload = _wb_payload([
        {"date": "2023", "value": 2.5},
        {"date": "2024", "value": 2.9},
    ])
    points = parse_worldbank_observations(payload, "NY.GDP.MKTP.KD.ZG")
    assert [p.value for p in points] == [2.5, 2.9]
    assert points[0].period.isoformat() == "2023-01-01"
    assert all(p.missing_reason is None for p in points)


def test_live_mode_labels_real_and_passes_params() -> None:
    payload = _wb_payload([{"date": "2024", "value": 4.1}])
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, text=payload)

    series = _connector(handler).fetch_indicator(
        "SL.UEM.TOTL.ZS", "USA", start_year=2024
    )
    assert series.system == "world_bank"
    assert series.evidence_label == "real"
    assert series.country_iso3 == "USA"
    assert "country/USA/indicator/SL.UEM.TOTL.ZS" in captured["url"]
    assert "format=json" in captured["url"]
    assert [p.value for p in series.points] == [4.1]


# --- Boundary cases ----------------------------------------------------------

def test_null_value_is_explicit_missing() -> None:
    payload = _wb_payload([
        {"date": "2023", "value": None},
        {"date": "2024", "value": 1.0},
    ])
    points = parse_worldbank_observations(payload, "FX.OWN.TOTL.ZS")
    assert points[0].value is None
    assert points[0].missing_reason == "wb_missing_value"
    assert points[1].value == 1.0  # missingness does not drop neighbours


def test_null_rows_list_is_empty_result() -> None:
    points = parse_worldbank_observations(_wb_payload(None), "X.Y.Z")
    assert points == []


def test_year_window_filters() -> None:
    payload = _wb_payload([
        {"date": "2022", "value": 1.0}, {"date": "2023", "value": 2.0},
        {"date": "2024", "value": 3.0},
    ])
    points = parse_worldbank_observations(payload, "X")
    assert [p.period.year for p in points] == [2022, 2023, 2024]


# --- Missing cases -----------------------------------------------------------

def test_wb_error_message_raises() -> None:
    payload = json.dumps(
        [{"message": [{"id": "120", "key": "Invalid value", "value": "bad"}]}]
    )
    with pytest.raises(ConnectorError, match="Invalid value"):
        parse_worldbank_observations(payload, "BAD.CODE")


def test_no_rows_key_raises() -> None:
    with pytest.raises(ConnectorError, match="unexpected response"):
        parse_worldbank_observations(json.dumps({"unexpected": True}), "X")


# --- Invalid cases -----------------------------------------------------------

def test_malformed_json_raises() -> None:
    with pytest.raises(ConnectorError, match="not valid JSON"):
        parse_worldbank_observations("nope", "X")


def test_non_numeric_value_raises() -> None:
    payload = _wb_payload([{"date": "2024", "value": "abc"}])
    with pytest.raises(ConnectorError, match="non-numeric"):
        parse_worldbank_observations(payload, "X")


def test_bad_period_raises() -> None:
    payload = _wb_payload([{"date": "20x4", "value": 1.0}])
    with pytest.raises(ConnectorError, match="malformed period"):
        parse_worldbank_observations(payload, "X")


def test_invalid_country_rejected() -> None:
    with pytest.raises(ConnectorError, match="invalid ISO3"):
        WorldBankConnector().fetch_indicator("X.Y.Z", "us")
    with pytest.raises(ConnectorError, match="indicator code must be non-empty"):
        WorldBankConnector().fetch_indicator("  ", "USA")


def test_http_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(ConnectorError, match="HTTP 500"):
        _connector(handler).fetch_indicator("X.Y.Z", "USA")
