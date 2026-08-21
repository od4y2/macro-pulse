"""Tests for the FRED connector vertical slice (unit S04).

All tests are deterministic: live-mode behavior is exercised through an
httpx.MockTransport, never the network. No API key is required.
"""

from __future__ import annotations

import json

import httpx
import pytest

from macropulse.connectors.fred import (
    FRED_MISSING_VALUE,
    FetchedPoint,
    FredConnector,
    parse_fred_observations,
)
from macropulse.connectors.persist import PersistError, persist_raw_series


def _fred_payload(observations: list[dict]) -> str:
    return json.dumps(
        {"realtime_start": "2025-01-01", "realtime_end": "9999-12-31",
         "observations": observations}
    )


# --- Normal cases -----------------------------------------------------------

def test_parse_normal_observations() -> None:
    payload = _fred_payload([
        {"date": "2024-01-01", "realtime_start": "2024-02-02", "value": "4.1"},
        {"date": "2024-02-01", "realtime_start": "2024-03-02", "value": "4.2"},
    ])
    points = parse_fred_observations(payload, "UNRATE")
    assert [p.value for p in points] == [4.1, 4.2]
    assert all(p.missing_reason is None for p in points)
    assert points[0].vintage.isoformat() == "2024-02-02"


def test_no_key_mode_is_deterministic_and_labelled_mocked() -> None:
    conn = FredConnector(api_key=None)
    assert conn.live is False
    first = conn.fetch_series("UNRATE")
    second = conn.fetch_series("UNRATE")
    assert first.evidence_label == "mocked"
    assert first.points == second.points  # determinism
    assert first.raw_payload == second.raw_payload
    assert len(first.points) == 5


def test_no_key_mode_preserves_missingness() -> None:
    conn = FredConnector(api_key=None)
    series = conn.fetch_series("UNRATE")
    missing = [p for p in series.points if p.value is None]
    assert len(missing) == 1
    assert missing[0].missing_reason == "fred_missing_value"


def test_live_mode_via_mock_transport() -> None:
    payload = _fred_payload([
        {"date": "2024-01-01", "realtime_start": "2024-02-02", "value": "3.7"},
    ])
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = dict(request.url.params)["api_key"]
        return httpx.Response(200, text=payload)

    conn = FredConnector(
        api_key="test-key-123", transport=httpx.MockTransport(handler)
    )
    assert conn.live is True
    series = conn.fetch_series("UNRATE")
    assert series.evidence_label == "real"
    assert [p.value for p in series.points] == [3.7]
    assert captured["api_key"] == "test-key-123"
    assert "series_id=UNRATE" in captured["url"]
    assert "file_type=json" in captured["url"]


# --- Boundary cases ----------------------------------------------------------

def test_date_window_filters_points() -> None:
    conn = FredConnector(api_key=None)
    from datetime import date

    series = conn.fetch_series(
        "UNRATE",
        observation_start=date(2024, 2, 1),
        observation_end=date(2024, 4, 1),
    )
    assert [p.period.isoformat() for p in series.points] == [
        "2024-02-01", "2024-03-01", "2024-04-01",
    ]


def test_fred_missing_marker_parsed_as_explicit_missing() -> None:
    payload = _fred_payload([
        {"date": "2024-01-01", "realtime_start": "2024-02-02", "value": FRED_MISSING_VALUE},
    ])
    points = parse_fred_observations(payload, "UNRATE")
    assert points[0].value is None
    assert points[0].missing_reason == "fred_missing_value"


def test_empty_observations_list_is_valid() -> None:
    points = parse_fred_observations(_fred_payload([]), "UNRATE")
    assert points == []


# --- Missing cases -----------------------------------------------------------

def test_error_message_payload_raises() -> None:
    payload = json.dumps({"error_message": "The series does not exist."})
    with pytest.raises(Exception, match="does not exist"):
        parse_fred_observations(payload, "BADID")


def test_missing_observations_key_raises() -> None:
    with pytest.raises(Exception, match="no observations list"):
        parse_fred_observations("{}", "UNRATE")


# --- Invalid cases -----------------------------------------------------------

def test_malformed_json_raises() -> None:
    with pytest.raises(Exception, match="not valid JSON"):
        parse_fred_observations("<html>oops</html>", "UNRATE")


def test_non_numeric_value_raises() -> None:
    payload = _fred_payload([
        {"date": "2024-01-01", "realtime_start": "2024-02-02", "value": "abc"},
    ])
    with pytest.raises(Exception, match="non-numeric"):
        parse_fred_observations(payload, "UNRATE")


def test_bad_date_raises() -> None:
    payload = _fred_payload([
        {"date": "not-a-date", "realtime_start": "2024-02-02", "value": "1.0"},
    ])
    with pytest.raises(Exception, match="malformed observation"):
        parse_fred_observations(payload, "UNRATE")


def test_empty_series_id_rejected() -> None:
    conn = FredConnector(api_key=None)
    with pytest.raises(Exception, match="series_id must be non-empty"):
        conn.fetch_series("  ")


def test_http_error_status_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    conn = FredConnector(
        api_key="test-key-123", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(Exception, match="HTTP 503"):
        conn.fetch_series("UNRATE")


# --- Persistence (live DB via shared conftest fixture; auto-skips) -----------


def _seed(session, indicator_id="unemployment_rate"):
    from macropulse.db.models import Country, Indicator

    session.merge(Country(iso3="USA", name="United States", rationale="benchmark"))
    session.merge(
        Indicator(
            indicator_id=indicator_id, name="Unemployment rate",
            module="traditional-indicators", unit="percent", frequency="annual",
            seasonal_adjustment="varies", fallback_status="primary-and-fallback",
            comparability_notes="n/a", limitations="n/a",
        )
    )
    session.commit()


def test_persist_raw_series_writes_immutable_payloads(session) -> None:
    from macropulse.db.models import RawObservation

    _seed(session)
    conn = FredConnector(api_key=None)
    series = conn.fetch_series("UNRATE")
    rows = persist_raw_series(session, series, "unemployment_rate")
    session.commit()

    assert len(rows) == 5
    stored = session.query(RawObservation).filter_by(indicator_id="unemployment_rate").all()
    assert len(stored) == 5
    payloads = [r.payload for r in stored]
    assert all(p["evidence_label"] == "mocked" for p in payloads)
    assert all("raw_payload" in p for p in payloads)
    missing_rows = [r for r in stored if r.value is None]
    assert len(missing_rows) == 1
    assert missing_rows[0].payload["missing_reason"] == "fred_missing_value"


def test_persist_rejects_unknown_country(session) -> None:
    _seed(session)
    conn = FredConnector(api_key=None)
    series = conn.fetch_series("UNRATE", country_iso3="ZZZ")
    with pytest.raises(PersistError, match="not registered"):
        persist_raw_series(session, series, "unemployment_rate")
    session.rollback()


def test_persist_rejects_unknown_indicator(session) -> None:
    _seed(session)
    conn = FredConnector(api_key=None)
    series = conn.fetch_series("UNRATE")
    with pytest.raises(PersistError, match="not registered"):
        persist_raw_series(session, series, "does-not-exist")
    session.rollback()


def test_fetched_point_is_missing_helper() -> None:
    from macropulse.connectors.persist import point_is_missing

    assert point_is_missing(FetchedPoint(
        period=__import__("datetime").date(2024, 1, 1), value=None,
        missing_reason="x", vintage=__import__("datetime").date(2024, 1, 1),
    ))
