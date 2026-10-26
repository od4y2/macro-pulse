"""Briefing endpoint tests: POST /briefing (generate) and GET /briefing/{id}.

The LLM prose source is a scripted fake injected through
``create_app(llm_source_factory=...)`` - no live LLM call, no real
credentials. Seeded observations carry ``evidence_label="real"`` so the
facts contract has something to validate (the conftest defaults are
synthetic, which the briefing layer honestly excludes). All data here is
test fixtures, never observations.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from macropulse.api.deps import get_session
from macropulse.api.main import create_app
from macropulse.briefing import DETERMINISTIC_MODEL, LLMTransportError
from macropulse.db.models import Country, NormalizedObservation

CLEAN_PROSE = (
    "Real GDP growth for USA stood at 2.9 percent_per_year in "
    "2025-01-01, up from 2.8 in 2024-01-01."
)


class FakeSource:
    """A stand-in LlmSource: scripted prose or a scripted failure."""

    def __init__(self, prose: str = CLEAN_PROSE, *, exc: Exception | None = None):
        self._prose = prose
        self._exc = exc
        self.calls = 0

    @property
    def model(self) -> str:
        return "fake-llm"

    @property
    def prompt_version(self) -> str:
        return "llm-v1"

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self._exc is not None:
            raise self._exc
        return self._prose


def _obs(**kwargs: object) -> NormalizedObservation:
    """One REAL-evidence USA gdp_real_growth observation (2025 default)."""
    defaults: dict[str, object] = {
        "indicator_id": "gdp_real_growth",
        "country_iso3": "USA",
        "period": date(2025, 1, 1),
        "value": Decimal("2.9"),
        "unit": "percent_per_year",
        "frequency": "annual",
        "seasonal_adjustment": "varies",
        "release_time": datetime(2026, 1, 25, 13, 30, tzinfo=UTC),
        "retrieval_time": datetime(2026, 1, 25, 14, 0, tzinfo=UTC),
        "vintage": date(2026, 1, 25),
        "evidence_label": "real",
        "quality_grade": "official",
        "missing_reason": None,
    }
    defaults.update(kwargs)
    return NormalizedObservation(**defaults)  # type: ignore[arg-type]


@pytest.fixture()
def seeded_real(session, seeded):
    """USA with two real vintages plus one synthetic row (excluded, counted).

    Also adds ZAF with no observations at all - the honest empty scope.
    """
    session.add(Country(iso3="ZAF", name="South Africa", rationale="test"))
    rows = [
        _obs(
            period=date(2024, 1, 1),
            value=Decimal("2.8"),
            release_time=datetime(2025, 1, 26, 13, 30, tzinfo=UTC),
            retrieval_time=datetime(2025, 1, 26, 14, 0, tzinfo=UTC),
            vintage=date(2025, 1, 26),
        ),
        _obs(),
        _obs(
            period=date(2023, 1, 1),
            value=Decimal("1.9"),
            release_time=datetime(2024, 1, 25, 13, 30, tzinfo=UTC),
            retrieval_time=datetime(2024, 1, 25, 14, 0, tzinfo=UTC),
            vintage=date(2024, 1, 25),
            evidence_label="synthetic",  # excluded, never stated as observed
        ),
    ]
    for row in rows:
        row.source_id = seeded.id
        session.add(row)
    session.commit()


def _client(session, source: FakeSource | None = None) -> TestClient:
    app = create_app(llm_source_factory=(lambda: source) if source else None)

    def _override():
        yield session  # conftest owns closing the shared test session

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


def test_post_briefing_llm_success(session, seeded_real) -> None:
    fake = FakeSource()
    response = _client(session, fake).post(
        "/briefing", json={"country_iso3": "USA"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["used_llm"] is True
    assert body["warning"] is None
    assert body["model"] == "fake-llm"
    assert body["prompt_version"] == "llm-v1"
    assert body["country_iso3"] == "USA"
    assert CLEAN_PROSE in body["prose"]
    assert body["prose"].startswith("MacroPulse structured briefing")
    assert "Limitations" in body["prose"]  # the machine frame is present
    assert fake.calls == 1
    # Audit trail: validated claims with full 6-field evidence refs.
    validated = [c for c in body["claims"] if c["validated"]]
    assert validated
    ref = validated[0]["evidence_refs"][0]
    assert set(ref) == {
        "indicator_id",
        "country_iso3",
        "period",
        "vintage",
        "source_system",
        "source_code",
    }
    assert ref["source_system"] == "world_bank"


def test_post_briefing_llm_failure_falls_back(session, seeded_real) -> None:
    fake = FakeSource(exc=LLMTransportError("connection reset"))
    response = _client(session, fake).post(
        "/briefing", json={"country_iso3": "USA"}
    )
    assert response.status_code == 200  # a fallback is an answer, not an error
    body = response.json()
    assert body["status"] == "fallback"
    assert body["used_llm"] is False
    assert body["model"] == DETERMINISTIC_MODEL
    assert body["prompt_version"] == "s16-v1"
    assert body["warning"].startswith("llm_transport_error:")
    assert body["prose"].startswith("MacroPulse structured briefing")
    assert "2.9" in body["prose"]  # the deterministic document still serves


def test_post_briefing_no_factory_falls_back_unconfigured(
    session, seeded_real, monkeypatch
) -> None:
    # No injected factory and no LLM_* environment -> honest fallback.
    for name in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    response = _client(session).post("/briefing", json={"country_iso3": "USA"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "fallback"
    assert body["warning"].startswith("llm_not_configured:")


def test_post_briefing_empty_scope_never_calls_llm(session, seeded_real) -> None:
    fake = FakeSource()
    response = _client(session, fake).post(
        "/briefing", json={"country_iso3": "ZAF"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "fallback"
    assert body["warning"] == "no_validated_statements"
    assert fake.calls == 0


def test_post_briefing_unknown_country_404(session, seeded_real) -> None:
    response = _client(session).post("/briefing", json={"country_iso3": "XXX"})
    assert response.status_code == 404
    assert "unknown country" in response.json()["detail"]


def test_post_briefing_bad_length_422(session, seeded_real) -> None:
    response = _client(session).post("/briefing", json={"country_iso3": "US"})
    assert response.status_code == 422  # schema-pinned length, automatic


def test_get_briefing_run_round_trip(session, seeded_real) -> None:
    client = _client(session, FakeSource())
    posted = client.post("/briefing", json={"country_iso3": "USA"}).json()
    response = client.get(f"/briefing/{posted['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == posted["id"]
    assert body["model"] == posted["model"]
    assert body["prompt_version"] == posted["prompt_version"]
    assert body["status"] == "completed"
    assert len(body["claims"]) == len(posted["claims"])
    assert body["created_at"] == posted["created_at"]
    # The persisted record is the audit trail, not the document.
    assert "prose" not in body


def test_get_briefing_run_unknown_404(session, seeded_real) -> None:
    response = _client(session).get("/briefing/999999")
    assert response.status_code == 404


def test_two_posts_append_two_runs(session, seeded_real) -> None:
    client = _client(session, FakeSource())
    first = client.post("/briefing", json={"country_iso3": "USA"}).json()
    second = client.post("/briefing", json={"country_iso3": "USA"}).json()
    assert second["id"] > first["id"]  # append-only: no reuse, no update
