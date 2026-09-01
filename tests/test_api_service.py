"""S13 query-service tests: typed, paginated, filterable data + methodology.

The service is exercised through a TestClient bound (via dependency
override) to the dedicated test database. Seed rows are labelled
``synthetic`` - they are test fixtures, not observations, and the label
must say so.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from macropulse.api.deps import get_session
from macropulse.api.main import create_app
from macropulse.api.schemas import ObservationOut
from macropulse.db.models import (
    Country,
    DerivedMetric,
    MetricVersion,
    NormalizedObservation,
)
from macropulse.metrics.transforms import FORMULAS

OBSERVATION_FIELDS = set(ObservationOut.model_fields)
SOURCE_FIELDS = {"system", "code", "role", "verified", "coverage"}
METRIC_FIELDS = {
    "metric_key",
    "country_iso3",
    "period",
    "value",
    "formula_ref",
    "version",
}


def _obs(**kwargs: object) -> NormalizedObservation:
    """One synthetic USA gdp_real_growth observation; overrides replace defaults."""
    defaults: dict[str, object] = {
        "indicator_id": "gdp_real_growth",
        "country_iso3": "USA",
        "period": date(2022, 1, 1),
        "value": Decimal("1.9"),
        "unit": "percent_per_year",
        "frequency": "annual",
        "seasonal_adjustment": "varies",
        "release_time": datetime(2023, 1, 26, 13, 30, tzinfo=UTC),
        "retrieval_time": datetime(2023, 1, 26, 14, 0, tzinfo=UTC),
        "vintage": date(2023, 1, 26),
        "evidence_label": "synthetic",
        "quality_grade": "official",
        "missing_reason": None,
    }
    defaults.update(kwargs)
    return NormalizedObservation(**defaults)  # type: ignore[arg-type]


@pytest.fixture()
def client(session, seeded):
    """TestClient over a seeded store: a revision chain, a missing row, a
    second country, and one derived metric with two recorded versions."""
    session.add(Country(iso3="ZAF", name="South Africa", rationale="test"))
    session.flush()
    observations = [
        _obs(
            period=date(2021, 1, 1),
            value=None,
            missing_reason="not_observed_at_period",
            release_time=datetime(2022, 1, 27, 14, 30, tzinfo=UTC),
            retrieval_time=datetime(2022, 1, 27, 14, 30, tzinfo=UTC),
            vintage=date(2022, 1, 27),
            quality_grade="ungraded",
        ),
        _obs(),  # USA 2022, value 1.9, vintage 2023-01-26
        _obs(
            period=date(2023, 1, 1),
            value=Decimal("2.5"),
            release_time=datetime(2024, 1, 25, 13, 30, tzinfo=UTC),
            retrieval_time=datetime(2024, 1, 25, 14, 0, tzinfo=UTC),
            vintage=date(2024, 1, 25),
            quality_grade="preliminary",
        ),
        _obs(
            period=date(2023, 1, 1),
            value=Decimal("2.9"),
            release_time=datetime(2024, 6, 15, 13, 30, tzinfo=UTC),
            retrieval_time=datetime(2024, 6, 15, 14, 0, tzinfo=UTC),
            vintage=date(2024, 6, 15),
            quality_grade="revised",
        ),
        _obs(
            country_iso3="ZAF",
            period=date(2023, 1, 1),
            value=Decimal("0.7"),
            release_time=datetime(2024, 2, 1, 10, 0, tzinfo=UTC),
            retrieval_time=datetime(2024, 2, 1, 11, 0, tzinfo=UTC),
            vintage=date(2024, 2, 1),
        ),
    ]
    for o in observations:
        o.source_id = seeded.id
        session.add(o)
    session.flush()

    metric = DerivedMetric(
        metric_key="gdp_real_growth.robust_z",
        country_iso3="USA",
        period=date(2023, 1, 1),
        value=Decimal("0.42"),
        formula_ref="robust_z",
        inputs={"observation_ids": [o.id for o in observations]},
    )
    session.add(metric)
    session.flush()
    session.add_all(
        [
            MetricVersion(
                metric_id=metric.id,
                version="v1",
                definition=FORMULAS["robust_z"],
                created_at=datetime(2024, 6, 15, 15, 0, tzinfo=UTC),
            ),
            MetricVersion(
                metric_id=metric.id,
                version="v2",
                definition=FORMULAS["robust_z"],
                created_at=datetime(2024, 7, 1, 9, 0, tzinfo=UTC),
            ),
        ]
    )
    session.commit()

    app = create_app()

    def _override():
        yield session  # conftest owns closing the shared test session

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


# --- health -----------------------------------------------------------------


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "data_mode": "database"}


def test_health_degraded_when_database_unreachable() -> None:
    engine = create_engine(
        "postgresql+psycopg://macropulse:macropulse@localhost:1/unreachable",
        future=True,
    )
    app = create_app(session_factory=sessionmaker(bind=engine, future=True))
    with TestClient(app) as test_client:
        response = test_client.get("/health")
    engine.dispose()
    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "data_mode": "database-unreachable",
    }


# --- countries / indicators ---------------------------------------------------


def test_countries_listed_with_total_count(client: TestClient) -> None:
    response = client.get("/countries")
    assert response.status_code == 200
    body = response.json()
    assert [c["iso3"] for c in body] == ["USA", "ZAF"]
    assert body[0]["name"] == "United States"
    assert body[0]["rationale"] == "test"
    assert response.headers["X-Total-Count"] == "2"


def test_countries_pagination(client: TestClient) -> None:
    first = client.get("/countries", params={"limit": 1})
    assert [c["iso3"] for c in first.json()] == ["USA"]
    assert first.headers["X-Total-Count"] == "2"
    second = client.get("/countries", params={"limit": 1, "offset": 1})
    assert [c["iso3"] for c in second.json()] == ["ZAF"]


def test_indicators_listed_matches_catalog_row(client: TestClient, session) -> None:
    response = client.get("/indicators")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    row = body[0]
    assert row["indicator_id"] == "gdp_real_growth"
    assert row["name"] == "Real GDP growth (annual %)"
    assert row["module"] == "traditional-indicators"
    assert row["unit"] == "percent_per_year"
    assert row["frequency"] == "annual"
    assert row["seasonal_adjustment"] == "varies"
    assert row["fallback_status"] == "primary-and-fallback"


def test_indicators_module_filter(client: TestClient) -> None:
    traditional = client.get("/indicators", params={"module": "traditional-indicators"})
    assert len(traditional.json()) == 1
    empty = client.get("/indicators", params={"module": "labor-slack-youth"})
    assert empty.json() == []
    assert empty.headers["X-Total-Count"] == "0"


def test_indicators_invalid_module_rejected(client: TestClient) -> None:
    response = client.get("/indicators", params={"module": "not-a-module"})
    assert response.status_code == 422


# --- observations ---------------------------------------------------------------


def test_observation_serves_the_pinned_provenance_contract(client: TestClient) -> None:
    response = client.get(
        "/observations",
        params={"country_iso3": "USA", "vintage": "2024-01-25"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    row = body[0]
    assert set(row.keys()) == OBSERVATION_FIELDS  # pinned shape, nothing extra
    assert set(row["source"].keys()) == SOURCE_FIELDS
    assert row["indicator_id"] == "gdp_real_growth"
    assert row["country_iso3"] == "USA"
    assert row["period"] == "2023-01-01"
    assert row["value"] == 2.5
    assert row["unit"] == "percent_per_year"
    assert row["frequency"] == "annual"
    assert row["seasonal_adjustment"] == "varies"
    assert row["source"] == {
        "system": "world_bank",
        "code": "NY.GDP.MKTP.KD.ZG",
        "role": "primary",
        "verified": "confirmed",
        "coverage": "test",
    }
    assert datetime.fromisoformat(row["release_time"]) == datetime(
        2024, 1, 25, 13, 30, tzinfo=UTC
    )
    assert datetime.fromisoformat(row["retrieval_time"]) == datetime(
        2024, 1, 25, 14, 0, tzinfo=UTC
    )
    assert row["vintage"] == "2024-01-25"
    assert row["evidence_label"] == "synthetic"
    assert row["quality_grade"] == "preliminary"
    assert row["missing_reason"] is None


def test_observations_revision_chain_and_latest_vintage(client: TestClient) -> None:
    both = client.get(
        "/observations", params={"country_iso3": "USA", "period_start": "2023-01-01"}
    )
    assert [r["vintage"] for r in both.json()] == ["2024-01-25", "2024-06-15"]

    latest = client.get(
        "/observations",
        params={
            "country_iso3": "USA",
            "period_start": "2023-01-01",
            "latest_vintage": True,
        },
    )
    body = latest.json()
    assert len(body) == 1
    assert body[0]["vintage"] == "2024-06-15"
    assert body[0]["value"] == 2.9
    assert body[0]["quality_grade"] == "revised"


def test_observations_period_range_is_inclusive(client: TestClient) -> None:
    response = client.get(
        "/observations",
        params={
            "country_iso3": "USA",
            "period_start": "2022-01-01",
            "period_end": "2023-01-01",
        },
    )
    periods = [r["period"] for r in response.json()]
    assert periods == ["2022-01-01", "2023-01-01", "2023-01-01"]  # end bound included


def test_observations_missing_rows_are_visible_never_imputed(
    client: TestClient,
) -> None:
    missing = client.get("/observations", params={"missing": True})
    body = missing.json()
    assert len(body) == 1
    assert body[0]["value"] is None
    assert body[0]["missing_reason"] == "not_observed_at_period"

    present = client.get("/observations", params={"missing": False})
    assert len(present.json()) == 4
    assert all(r["value"] is not None for r in present.json())


def test_observations_country_and_indicator_filters(client: TestClient) -> None:
    zaf = client.get("/observations", params={"country_iso3": "ZAF"})
    assert len(zaf.json()) == 1
    assert zaf.json()[0]["value"] == 0.7

    unknown = client.get("/observations", params={"indicator_id": "does_not_exist"})
    assert unknown.json() == []
    assert unknown.headers["X-Total-Count"] == "0"


def test_observations_evidence_label_filter(client: TestClient) -> None:
    synthetic = client.get("/observations", params={"evidence_label": "synthetic"})
    assert len(synthetic.json()) == 5
    real = client.get("/observations", params={"evidence_label": "real"})
    assert real.json() == []


def test_observations_invalid_closed_vocab_values_rejected(client: TestClient) -> None:
    assert (
        client.get("/observations", params={"evidence_label": "guesswork"}).status_code
        == 422
    )
    assert (
        client.get("/observations", params={"quality_grade": "excellent"}).status_code
        == 422
    )


def test_observations_quality_grade_filter(client: TestClient) -> None:
    revised = client.get("/observations", params={"quality_grade": "revised"})
    assert len(revised.json()) == 1
    assert revised.json()[0]["value"] == 2.9


def test_observations_deterministic_order_and_pagination(client: TestClient) -> None:
    full = client.get("/observations")
    assert [(r["country_iso3"], r["period"], r["vintage"]) for r in full.json()] == [
        ("USA", "2021-01-01", "2022-01-27"),
        ("USA", "2022-01-01", "2023-01-26"),
        ("USA", "2023-01-01", "2024-01-25"),
        ("USA", "2023-01-01", "2024-06-15"),
        ("ZAF", "2023-01-01", "2024-02-01"),
    ]
    assert full.headers["X-Total-Count"] == "5"

    page = client.get("/observations", params={"limit": 2, "offset": 2})
    assert [r["vintage"] for r in page.json()] == ["2024-01-25", "2024-06-15"]
    assert page.headers["X-Total-Count"] == "5"


def test_observations_invalid_pagination_rejected(client: TestClient) -> None:
    assert client.get("/observations", params={"limit": 0}).status_code == 422
    assert client.get("/observations", params={"limit": 501}).status_code == 422
    assert client.get("/observations", params={"offset": -1}).status_code == 422


# --- metrics ---------------------------------------------------------------------


def test_metrics_serve_latest_recorded_version(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    row = body[0]
    assert set(row.keys()) == METRIC_FIELDS
    assert row["metric_key"] == "gdp_real_growth.robust_z"
    assert row["country_iso3"] == "USA"
    assert row["period"] == "2023-01-01"
    assert row["value"] == pytest.approx(0.42)
    assert row["formula_ref"] == "robust_z"
    assert row["version"] == "v2"  # newest recorded definition wins
    assert response.headers["X-Total-Count"] == "1"


def test_metrics_filters(client: TestClient) -> None:
    assert client.get("/metrics", params={"country_iso3": "ZAF"}).json() == []
    assert client.get("/metrics", params={"metric_key": "nope"}).json() == []

    in_range = client.get(
        "/metrics", params={"period_start": "2023-01-01", "period_end": "2023-12-31"}
    )
    assert len(in_range.json()) == 1
    out_of_range = client.get(
        "/metrics", params={"period_start": "2024-01-01", "period_end": "2024-12-31"}
    )
    assert out_of_range.json() == []


# --- methodology -----------------------------------------------------------------


def test_methodology_formulas_serve_the_registry(client: TestClient) -> None:
    response = client.get("/methodology/formulas")
    assert response.status_code == 200
    body = response.json()
    assert [f["name"] for f in body] == sorted(FORMULAS)
    for entry in body:
        assert entry["definition"] == FORMULAS[entry["name"]]


def test_methodology_formulas_name_filter(client: TestClient) -> None:
    known = client.get("/methodology/formulas", params={"name": "robust_z"})
    assert [f["name"] for f in known.json()] == ["robust_z"]
    unknown = client.get("/methodology/formulas", params={"name": "not_a_formula"})
    assert unknown.json() == []


def test_methodology_metric_definitions_newest_first(client: TestClient) -> None:
    response = client.get("/methodology/metrics/gdp_real_growth.robust_z")
    assert response.status_code == 200
    body = response.json()
    assert [d["version"] for d in body] == ["v2", "v1"]
    for entry in body:
        assert entry["metric_key"] == "gdp_real_growth.robust_z"
        assert entry["definition"] == FORMULAS["robust_z"]
        assert datetime.fromisoformat(entry["recorded_at"]) is not None


def test_methodology_unknown_metric_404(client: TestClient) -> None:
    response = client.get("/methodology/metrics/never_computed")
    assert response.status_code == 404
    assert "unknown metric_key" in response.json()["detail"]
