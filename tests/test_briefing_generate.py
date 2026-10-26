"""generate_briefing orchestration tests: the LLM path, every fallback
gate, and the append-only audit rows.

No live LLM call - a FakeSource stands in for the prose source, and the
LLM_* environment is monkeypatched so real credentials are never read.
DB-backed tests use the conftest ``session`` fixture (skipped when the
test Postgres is down). All inputs are synthetic fixtures.
"""

from __future__ import annotations

import pytest

from macropulse.briefing import (
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROMPT_VERSION,
    FALLBACK_WARNINGS,
    LLM_PROMPT_VERSION,
    BriefingOutcome,
    LLMResponseError,
    LLMTransportError,
    compose_document,
    generate_briefing,
)
from macropulse.db.models import BriefingRun

# Prose that survives every gate: only claim-backed numbers, no banned
# phrases ("2.9", "2.8", and the ISO periods all appear in the claims).
CLEAN_PROSE = (
    "Real GDP growth for BRA stood at 2.9 percent_per_year in "
    "2025-01-01, up from 2.8 in 2024-01-01."
)


def obs(**overrides: object) -> dict:
    """One observation record shaped like the service's ObservationOut."""
    base: dict[str, object] = {
        "indicator_id": "gdp_real_growth",
        "country_iso3": "BRA",
        "period": "2025-01-01",
        "value": 2.9,
        "unit": "percent_per_year",
        "frequency": "annual",
        "seasonal_adjustment": "varies",
        "source": {
            "system": "world_bank",
            "code": "NY.GDP.MKTP.KD.ZG",
            "role": "primary",
            "verified": "confirmed",
            "coverage": "test",
        },
        "release_time": "2026-01-25T13:30:00Z",
        "retrieval_time": "2026-01-25T14:00:00Z",
        "vintage": "2026-01-25",
        "evidence_label": "real",
        "quality_grade": "official",
        "missing_reason": None,
    }
    base.update(overrides)
    return base


def obs_2y() -> list[dict]:
    return [obs(period="2024-01-01", value=2.8), obs()]


class FakeSource:
    """A stand-in LlmSource: scripted prose or a scripted failure."""

    def __init__(
        self,
        prose: str = CLEAN_PROSE,
        *,
        exc: Exception | None = None,
        model: str = "fake-llm",
    ) -> None:
        self._prose = prose
        self._exc = exc
        self._model = model
        self.calls = 0
        self.prompts: list[str] = []

    @property
    def model(self) -> str:
        return self._model

    @property
    def prompt_version(self) -> str:
        return LLM_PROMPT_VERSION

    def generate(self, prompt: str) -> str:
        self.calls += 1
        self.prompts.append(prompt)
        if self._exc is not None:
            raise self._exc
        return self._prose


@pytest.fixture()
def no_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee the call-time env read finds no LLM configuration."""
    for name in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)


# --- the LLM path ----------------------------------------------------------------


def test_llm_success_records_completed_run(session) -> None:
    fake = FakeSource()
    outcome = generate_briefing(
        session, "BRA", obs_2y(), llm_source=fake
    )
    assert isinstance(outcome, BriefingOutcome)
    assert outcome.status == "completed"
    assert outcome.used_llm is True
    assert outcome.warning is None
    assert outcome.model == "fake-llm"
    assert outcome.prompt_version == LLM_PROMPT_VERSION
    assert CLEAN_PROSE in outcome.prose
    # The machine-composed frame carries the deterministic parts.
    assert outcome.prose.startswith("MacroPulse structured briefing")
    assert "Scope:" in outcome.prose
    assert "Limitations" in outcome.prose
    assert fake.calls == 1
    assert "2.9" in fake.prompts[0]  # prompt built from validated claims

    run = session.get(BriefingRun, outcome.run_id)
    assert run is not None
    assert run.status == "completed"
    assert run.model == "fake-llm"
    assert run.prompt_version == LLM_PROMPT_VERSION


def test_compose_document_frames_statements() -> None:
    from macropulse.briefing import BriefingFacts, adjudicate_all, build_claims

    facts = BriefingFacts.from_observations(obs_2y())
    adjudicated = adjudicate_all(build_claims(facts), facts)
    document = compose_document("One statement.", facts, adjudicated)
    statements_at = document.index("Statements")
    limitations_at = document.index("Limitations")
    assert statements_at < document.index("One statement.") < limitations_at
    assert "Scope: 1 economies" in document


# --- the fallback matrix ----------------------------------------------------------


def test_banned_phrase_falls_back(session) -> None:
    fake = FakeSource("Growth reached 2.9 because of strong exports.")
    outcome = generate_briefing(session, "BRA", obs_2y(), llm_source=fake)
    assert outcome.status == "fallback"
    assert outcome.used_llm is False
    assert outcome.model == DETERMINISTIC_MODEL
    assert outcome.prompt_version == DETERMINISTIC_PROMPT_VERSION
    assert outcome.warning is not None
    assert outcome.warning.startswith("banned_phrase:")
    assert "causal_phrase" in outcome.warning
    assert "because" not in outcome.prose  # rejected prose never renders
    assert session.get(BriefingRun, outcome.run_id).status == "fallback"


def test_fabricated_number_falls_back(session) -> None:
    fake = FakeSource("Growth reached 2.9 and inflation hit 3.5 percent.")
    outcome = generate_briefing(session, "BRA", obs_2y(), llm_source=fake)
    assert outcome.status == "fallback"
    assert outcome.warning == "fabricated_number: 3.5"
    assert "3.5" not in outcome.prose
    assert "2.9" in outcome.prose  # the deterministic document still states it


def test_transport_error_falls_back(session) -> None:
    fake = FakeSource(exc=LLMTransportError("connection reset by peer"))
    outcome = generate_briefing(session, "BRA", obs_2y(), llm_source=fake)
    assert outcome.status == "fallback"
    assert outcome.warning is not None
    assert outcome.warning.startswith("llm_transport_error:")
    assert "connection reset" in outcome.warning


def test_response_error_falls_back(session) -> None:
    fake = FakeSource(exc=LLMResponseError("LLM endpoint returned HTTP 503"))
    outcome = generate_briefing(session, "BRA", obs_2y(), llm_source=fake)
    assert outcome.status == "fallback"
    assert outcome.warning is not None
    assert outcome.warning.startswith("llm_response_error:")


def test_empty_llm_prose_falls_back(session) -> None:
    fake = FakeSource("   \n  ")
    outcome = generate_briefing(session, "BRA", obs_2y(), llm_source=fake)
    assert outcome.status == "fallback"
    assert outcome.warning == "empty_llm_prose"


def test_unconfigured_env_falls_back(session, no_llm_env) -> None:
    # llm_source=None -> the real from_env() resolves at call time and
    # finds nothing: honest warning, deterministic document, no crash.
    outcome = generate_briefing(session, "BRA", obs_2y())
    assert outcome.status == "fallback"
    assert outcome.used_llm is False
    assert outcome.warning is not None
    assert outcome.warning.startswith("llm_not_configured:")
    assert outcome.prose.startswith("MacroPulse structured briefing")


def test_no_validated_claims_never_calls_the_llm(session) -> None:
    # Synthetic-label rows are excluded -> no validated claims exist.
    fake = FakeSource()
    observations = [
        obs(evidence_label="synthetic"),
        obs(period="2024-01-01", value=2.8, evidence_label="mocked"),
    ]
    outcome = generate_briefing(session, "BRA", observations, llm_source=fake)
    assert fake.calls == 0
    assert outcome.status == "fallback"
    assert outcome.warning == "no_validated_statements"
    assert outcome.model == DETERMINISTIC_MODEL


# --- contract and audit ------------------------------------------------------------


def test_foreign_country_row_is_rejected(session) -> None:
    fake = FakeSource()
    with pytest.raises(ValueError, match="one country per run"):
        generate_briefing(
            session,
            "BRA",
            [obs(), obs(country_iso3="USA", period="2024-01-01", value=1.5)],
            llm_source=fake,
        )
    assert fake.calls == 0


def test_two_generations_append_two_runs(session) -> None:
    first = generate_briefing(session, "BRA", obs_2y(), llm_source=FakeSource())
    second = generate_briefing(
        session,
        "BRA",
        obs_2y(),
        llm_source=FakeSource(exc=LLMTransportError("down")),
    )
    assert first.run_id is not None and second.run_id is not None
    assert second.run_id > first.run_id
    assert session.get(BriefingRun, first.run_id).status == "completed"
    assert session.get(BriefingRun, second.run_id).status == "fallback"


def test_record_run_false_persists_nothing(session) -> None:
    before = session.query(BriefingRun).count()
    outcome = generate_briefing(
        session, "BRA", obs_2y(), llm_source=FakeSource(), record_run=False
    )
    assert outcome.run_id is None
    assert session.query(BriefingRun).count() == before


def test_warning_detail_is_truncated(session) -> None:
    # A pathological upstream message must not flood the API response:
    # the quoted detail is capped and the reason stays in the closed
    # vocabulary. (That the key itself never reaches an exception
    # message is enforced one layer down, in test_briefing_llm.py.)
    long_detail = "auth failed: " + "x" * 500
    fake = FakeSource(exc=LLMResponseError(long_detail))
    outcome = generate_briefing(session, "BRA", obs_2y(), llm_source=fake)
    assert outcome.warning is not None
    assert outcome.warning.endswith("...")
    assert len(outcome.warning) < 260
    assert outcome.warning.split(":")[0] in FALLBACK_WARNINGS


def test_config_warning_names_variables_not_values(session, monkeypatch) -> None:
    # A partial configuration surfaces the missing variable NAMES only.
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model-1")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    outcome = generate_briefing(session, "BRA", obs_2y())
    assert outcome.warning is not None
    assert outcome.warning.startswith("llm_not_configured:")
    assert "LLM_API_KEY" in outcome.warning
    assert "test-model-1" not in outcome.warning


def test_every_fallback_warning_in_closed_vocabulary() -> None:
    # Guard the docs contract: the seven reasons, exactly.
    assert FALLBACK_WARNINGS == (
        "llm_not_configured",
        "llm_transport_error",
        "llm_response_error",
        "banned_phrase",
        "fabricated_number",
        "empty_llm_prose",
        "no_validated_statements",
    )
