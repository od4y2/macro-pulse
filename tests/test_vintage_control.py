"""Tests for S07 vintage control and ALFRED realtime queries."""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest

from macropulse.connectors.base import ConnectorError, FetchedPoint, FetchedSeries
from macropulse.connectors.fred import FredConnector
from macropulse.db.models import DataQualityFlag, NormalizedObservation
from macropulse.pipeline.normalize import normalize_series, persist_normalized
from macropulse.quality.vintage import (
    apply_assessment,
    assess_and_apply,
    revision_deltas,
    revision_history,
    superseded_identities,
)

RETRIEVAL = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def make_series(points, system="world_bank", series_id="NY.GDP.MKTP.KD.ZG",
                country_iso3="USA", evidence_label="real"):
    return FetchedSeries(
        system=system,
        series_id=series_id,
        country_iso3=country_iso3,
        evidence_label=evidence_label,
        retrieval_time=RETRIEVAL,
        points=tuple(points),
        raw_payload="[]",
    )


def annual_points(values_by_year):
    return [
        FetchedPoint(
            period=date(y, 1, 1),
            value=v,
            missing_reason=None if v is not None else "not_available",
            vintage=RETRIEVAL.date(),
        )
        for y, v in values_by_year.items()
    ]


# --- pure revision math ----------------------------------------------------


def _step(vintage, value, oid=0, reason=None):
    from macropulse.quality.vintage import RevisionStep

    return RevisionStep(
        observation_id=oid,
        vintage=vintage,
        value=value,
        missing_reason=reason,
        evidence_label="real",
        source_id=1,
    )


def test_revision_deltas_value_change():
    history = {
        date(2023, 1, 1): [
            _step(date(2023, 6, 1), 2.0, oid=1),
            _step(date(2024, 6, 1), 2.5, oid=2),
        ]
    }
    deltas = revision_deltas(history)
    assert len(deltas) == 1
    d = deltas[0]
    assert d.period == date(2023, 1, 1)
    assert d.from_vintage == date(2023, 6, 1)
    assert d.to_vintage == date(2024, 6, 1)
    assert d.absolute == pytest.approx(0.5)
    assert d.relative == pytest.approx(0.25)


def test_revision_deltas_three_vintage_chain():
    history = {
        date(2023, 1, 1): [
            _step(date(2023, 6, 1), 2.0),
            _step(date(2024, 6, 1), 2.5),
            _step(date(2025, 6, 1), 2.2),
        ]
    }
    deltas = revision_deltas(history)
    assert len(deltas) == 2
    assert deltas[0].absolute == pytest.approx(0.5)
    assert deltas[1].absolute == pytest.approx(-0.3)


def test_revision_deltas_unsorted_history_is_sorted():
    history = {
        date(2023, 1, 1): [
            _step(date(2024, 6, 1), 2.5),
            _step(date(2023, 6, 1), 2.0),
        ]
    }
    deltas = revision_deltas(history)
    assert deltas[0].from_vintage == date(2023, 6, 1)
    assert deltas[0].to_vintage == date(2024, 6, 1)


def test_revision_deltas_value_to_missing():
    history = {
        date(2023, 1, 1): [
            _step(date(2023, 6, 1), 2.0),
            _step(date(2024, 6, 1), None, reason="withdrawn"),
        ]
    }
    deltas = revision_deltas(history)
    assert deltas[0].to_value is None
    assert deltas[0].absolute is None  # never fabricated
    assert deltas[0].relative is None


def test_revision_deltas_zero_base_relative_is_none():
    history = {
        date(2023, 1, 1): [
            _step(date(2023, 6, 1), 0.0),
            _step(date(2024, 6, 1), 1.0),
        ]
    }
    deltas = revision_deltas(history)
    assert deltas[0].absolute == pytest.approx(1.0)
    assert deltas[0].relative is None  # 1/0 is not fabricated as infinity


def test_revision_deltas_multiple_periods_ordered():
    history = {
        date(2024, 1, 1): [_step(date(2024, 6, 1), 1.0), _step(date(2025, 6, 1), 1.5)],
        date(2023, 1, 1): [_step(date(2023, 6, 1), 2.0), _step(date(2024, 6, 1), 2.4)],
    }
    deltas = revision_deltas(history)
    assert [d.period for d in deltas] == [date(2023, 1, 1), date(2024, 1, 1)]


def test_revision_deltas_empty_history():
    assert revision_deltas({}) == []


# --- ALFRED realtime queries (connector) ------------------------------------


ALFRED_PAYLOAD = """
{
  "realtime_start": "2023-04-02",
  "realtime_end": "2023-12-31",
  "observations": [
    {"date": "2023-01-01", "realtime_start": "2023-04-02", "value": "5.2"},
    {"date": "2022-12-01", "realtime_start": "2023-01-06", "value": "5.1"}
  ]
}
"""


def _alfred_transport() -> httpx.MockTransport:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, text=ALFRED_PAYLOAD)

    transport = httpx.MockTransport(handler)
    transport.captured = captured  # type: ignore[attr-defined]
    return transport


def test_fred_realtime_params_sent():
    connector = FredConnector(api_key="test-key", transport=_alfred_transport())
    series = connector.fetch_series(
        "UNRATE",
        observation_start=date(2022, 12, 1),
        observation_end=date(2023, 12, 31),
        realtime_start=date(2023, 4, 2),
        realtime_end=date(2023, 12, 31),
    )
    url = connector._transport.captured["url"]  # type: ignore[attr-defined]
    assert "realtime_start=2023-04-02" in url
    assert "realtime_end=2023-12-31" in url
    assert "observation_start=2022-12-01" in url
    assert "observation_end=2023-12-31" in url
    assert series.evidence_label == "real"
    # The ALFRED response's own realtime_start stamps each point's vintage.
    assert series.points[0].vintage == date(2023, 4, 2)
    assert series.points[0].value == pytest.approx(5.2)


def test_fred_realtime_without_key_is_rejected():
    # No silent mocks: realtime queries require the live API.
    connector = FredConnector(api_key=None)
    with pytest.raises(ConnectorError, match="realtime"):
        connector.fetch_series("UNRATE", realtime_start=date(2023, 4, 2))


def test_alfred_chain_normalizes_and_persists(session, seeded):
    # Two realtime fetches of the same period build a vintage chain; the
    # normalized store keeps both rows (revision history, RQ4).
    from macropulse.db.models import NormalizedObservation

    def chain_transport():
        payloads = [
            '{"observations": [{"date": "2023-01-01", "realtime_start": "2023-04-02", "value": "5.2"}]}',
            '{"observations": [{"date": "2023-01-01", "realtime_start": "2024-04-03", "value": "5.4"}]}',
        ]
        state = {"i": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            i = state["i"]
            state["i"] += 1
            return httpx.Response(200, text=payloads[i])

        return httpx.MockTransport(handler)

    connector = FredConnector(
        api_key="test-key", transport=chain_transport()
    )
    first = connector.fetch_series("UNRATE", realtime_start=date(2023, 4, 2))
    second = connector.fetch_series("UNRATE", realtime_start=date(2024, 4, 3))

    source_id = seeded.id
    for fetched in (first, second):
        records = normalize_series(fetched, "gdp_real_growth", frequency="annual")
        persist_normalized(session, records, source_id)
    session.commit()

    rows = session.query(NormalizedObservation).all()
    assert len(rows) == 2
    assert {r.vintage for r in rows} == {date(2023, 4, 2), date(2024, 4, 3)}
    values = {r.vintage: float(r.value) for r in rows}
    assert values[date(2023, 4, 2)] == pytest.approx(5.2)
    assert values[date(2024, 4, 3)] == pytest.approx(5.4)

    # Vintage control: the older vintage is superseded and graded revised.
    assessment = assess_and_apply(session, "gdp_real_growth", "USA")
    grades = {(r.period, r.vintage): r.grade for r in assessment.records}
    assert grades[(date(2023, 1, 1), date(2023, 4, 2))] == "revised"
    assert grades[(date(2023, 1, 1), date(2024, 4, 3))] == "official"

    deltas = revision_deltas(revision_history(session, "gdp_real_growth", "USA"))
    assert len(deltas) == 1
    assert deltas[0].absolute == pytest.approx(0.2)


# --- persistence of grades and flags ----------------------------------------


def test_apply_assessment_writes_flags_and_grades(session, seeded):
    from macropulse.db.models import NormalizedObservation

    series = make_series(
        annual_points({2022: 1.0, 2023: None, 2024: 2.0}),
        system="world_bank",
    )
    records = normalize_series(series, "gdp_real_growth")
    rows = persist_normalized(session, records, seeded.id)
    session.commit()

    superseded = frozenset()  # single fetch, nothing superseded
    from macropulse.quality.assessment import assess_series

    assessment = assess_series(
        rows, "gdp_real_growth", "USA", "annual", superseded
    )
    apply_assessment(session, rows, assessment)
    session.commit()

    by_period = {r.period: r for r in session.query(NormalizedObservation).all()}
    assert by_period[date(2022, 1, 1)].quality_grade == "official"
    assert by_period[date(2023, 1, 1)].quality_grade == "flagged"
    assert by_period[date(2024, 1, 1)].quality_grade == "official"

    flags = session.query(DataQualityFlag).all()
    assert len(flags) == 1
    assert flags[0].flag_code == "missing_value"
    assert flags[0].normalized_observation_id == by_period[date(2023, 1, 1)].id


def test_apply_assessment_flags_are_append_only(session, seeded):
    # Re-running the assessment appends new flag rows; history is never
    # deleted (audit trail semantics).
    series = make_series(annual_points({2023: None}), system="world_bank")
    records = normalize_series(series, "gdp_real_growth", frequency="annual")
    rows = persist_normalized(session, records, seeded.id)
    session.commit()

    from macropulse.quality.assessment import assess_series

    assessment = assess_series(rows, "gdp_real_growth", "USA", "annual")
    apply_assessment(session, rows, assessment)
    session.commit()
    apply_assessment(session, rows, assessment)
    session.commit()

    assert session.query(DataQualityFlag).count() == 2


def test_assess_and_apply_unknown_series_raises(session, seeded):
    with pytest.raises(ValueError, match="no stored series"):
        assess_and_apply(session, "gdp_real_growth", "USA")


def test_superseded_identities(session, seeded):
    # A vintage chain persisted under one series: (2023 period) has two
    # vintages, (2024 period) has one.
    from macropulse.connectors.base import FetchedPoint, FetchedSeries

    chain = FetchedSeries(
        system="world_bank",
        series_id="NY.GDP.MKTP.KD.ZG",
        country_iso3="USA",
        evidence_label="real",
        retrieval_time=RETRIEVAL,
        points=(
            FetchedPoint(date(2023, 1, 1), 2.1, None, date(2023, 6, 1)),
            FetchedPoint(date(2023, 1, 1), 2.4, None, date(2024, 6, 1)),
            FetchedPoint(date(2024, 1, 1), 2.9, None, date(2024, 6, 1)),
        ),
        raw_payload="[]",
    )
    records = normalize_series(chain, "gdp_real_growth", frequency="annual")
    persist_normalized(session, records, seeded.id)
    session.commit()

    superseded = superseded_identities(session, "gdp_real_growth", "USA")
    assert superseded == frozenset({(date(2023, 1, 1), date(2023, 6, 1))})

    history = revision_history(session, "gdp_real_growth", "USA")
    assert [s.vintage for s in history[date(2023, 1, 1)]] == [
        date(2023, 6, 1), date(2024, 6, 1)
    ]
    assert session.query(NormalizedObservation).count() == 3
