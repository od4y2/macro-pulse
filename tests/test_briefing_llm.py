"""LLM prose source tests: settings resolution, prompt construction,
and the OpenAI-compatible HTTP path.

No test makes a live LLM call - every request goes through an
httpx.MockTransport, and the environment is fully monkeypatched so the
developer's real LLM_* values are never read. All fixtures are
synthetic (test payloads, never observations).
"""

from __future__ import annotations

import json

import httpx
import pytest

from macropulse.briefing import (
    LLM_PROMPT_VERSION,
    LLM_TIMEOUT_MAX,
    LLM_TIMEOUT_MIN,
    LLM_TIMEOUT_SECONDS,
    SUPPORTED_PROVIDERS,
    BriefingFacts,
    HttpLlmSource,
    LLMConfigError,
    LLMResponseError,
    LLMSettings,
    LLMTransportError,
    adjudicate_all,
    build_claims,
    build_prompt,
    build_system_prompt,
)

TEST_KEY = "sk-test-secret-key-do-not-leak"


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


_LLM_ENV_NAMES = (
    "LLM_PROVIDER",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_API_KEY",
    "LLM_EXTRA_BODY",
    "LLM_TIMEOUT_SECONDS",
)


@pytest.fixture()
def llm_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """A complete, synthetic LLM_* environment (call-time reads)."""
    values = {
        "LLM_PROVIDER": "openai-compatible",
        "LLM_BASE_URL": "https://llm.example.test/v1",
        "LLM_MODEL": "test-model-1",
        "LLM_API_KEY": TEST_KEY,
    }
    # A developer's real LLM_EXTRA_BODY / LLM_TIMEOUT_SECONDS must never
    # leak into tests - unset so the code defaults apply deterministically.
    monkeypatch.delenv("LLM_EXTRA_BODY", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return values


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _LLM_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def _source(handler, settings: LLMSettings) -> HttpLlmSource:
    return HttpLlmSource(settings, transport=httpx.MockTransport(handler))


# --- settings ----------------------------------------------------------------


def test_settings_from_env_success(llm_env) -> None:
    settings = LLMSettings.from_env()
    assert settings.provider in SUPPORTED_PROVIDERS
    assert settings.base_url == "https://llm.example.test/v1"
    assert settings.model == "test-model-1"
    assert settings.api_key.get_secret_value() == TEST_KEY
    # Secret hygiene: neither repr nor str carries the key.
    assert TEST_KEY not in repr(settings)
    assert TEST_KEY not in str(settings)


def test_settings_from_env_strips_trailing_slash(monkeypatch, llm_env) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test/v1/")
    assert LLMSettings.from_env().base_url == "https://llm.example.test/v1"


def test_settings_from_env_missing_vars_names_only(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", "test-model-1")  # base_url, key missing
    with pytest.raises(LLMConfigError) as excinfo:
        LLMSettings.from_env()
    message = str(excinfo.value)
    assert "LLM_BASE_URL" in message
    assert "LLM_API_KEY" in message
    assert "LLM_MODEL" not in message  # present vars are not named
    assert "test-model-1" not in message  # never values


def test_settings_from_env_unsupported_provider(monkeypatch, llm_env) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "carrier-pigeon")
    with pytest.raises(LLMConfigError, match="unsupported LLM_PROVIDER"):
        LLMSettings.from_env()


def test_settings_from_env_overlong_model(monkeypatch, llm_env) -> None:
    monkeypatch.setenv("LLM_MODEL", "x" * 129)
    with pytest.raises(LLMConfigError, match="128-char"):
        LLMSettings.from_env()


def test_settings_extra_body_defaults_empty(llm_env) -> None:
    # Unset -> the request body stays the OpenAI-compatible minimum.
    assert LLMSettings.from_env().extra_body == {}


def test_settings_extra_body_parses_json_object(monkeypatch, llm_env) -> None:
    monkeypatch.setenv(
        "LLM_EXTRA_BODY", '{"enable_thinking": false, "top_p": 0.9}'
    )
    assert LLMSettings.from_env().extra_body == {
        "enable_thinking": False,
        "top_p": 0.9,
    }


def test_settings_extra_body_malformed_json_names_var_only(
    monkeypatch, llm_env
) -> None:
    monkeypatch.setenv("LLM_EXTRA_BODY", '{"enable_thinking":')
    with pytest.raises(LLMConfigError) as excinfo:
        LLMSettings.from_env()
    message = str(excinfo.value)
    assert "LLM_EXTRA_BODY" in message
    assert "enable_thinking" not in message  # never values


def test_settings_extra_body_rejects_non_object(monkeypatch, llm_env) -> None:
    monkeypatch.setenv("LLM_EXTRA_BODY", "[1, 2]")
    with pytest.raises(LLMConfigError, match="JSON object"):
        LLMSettings.from_env()


# --- timeout configuration ------------------------------------------------------


def test_settings_timeout_defaults(llm_env) -> None:
    # Unset -> the module default, which the nesting test in test_views
    # pins below BRIEFING_TIMEOUT.
    assert LLMSettings.from_env().timeout_seconds == LLM_TIMEOUT_SECONDS


def test_settings_timeout_from_env(monkeypatch, llm_env) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "30")
    assert LLMSettings.from_env().timeout_seconds == 30.0
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", " 120.5 ")
    assert LLMSettings.from_env().timeout_seconds == 120.5


def test_settings_timeout_accepts_bounds(monkeypatch, llm_env) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", str(LLM_TIMEOUT_MIN))
    assert LLMSettings.from_env().timeout_seconds == LLM_TIMEOUT_MIN
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", str(LLM_TIMEOUT_MAX))
    assert LLMSettings.from_env().timeout_seconds == LLM_TIMEOUT_MAX


@pytest.mark.parametrize("raw", ["abc", "12s", "1,5"])
def test_settings_timeout_malformed_names_var_only(
    monkeypatch, llm_env, raw: str
) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", raw)
    with pytest.raises(LLMConfigError) as excinfo:
        LLMSettings.from_env()
    message = str(excinfo.value)
    assert "LLM_TIMEOUT_SECONDS" in message
    assert raw.strip() not in message  # never values


@pytest.mark.parametrize("raw", ["0", "-5", "601", "nan", "inf"])
def test_settings_timeout_out_of_range(monkeypatch, llm_env, raw: str) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", raw)
    with pytest.raises(LLMConfigError, match="out of range"):
        LLMSettings.from_env()


def test_http_source_uses_settings_timeout(monkeypatch, llm_env) -> None:
    # The configured value must reach the wire, not just the settings.
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "33")
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_ok_body("Growth stood at 2.9."))

    source = _source(handler, LLMSettings.from_env())
    source.generate("the prompt")
    assert captured[0].extensions["timeout"]["read"] == 33.0


def test_http_source_explicit_timeout_wins(monkeypatch, llm_env) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "33")
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_ok_body("Growth stood at 2.9."))

    settings = LLMSettings.from_env()
    source = HttpLlmSource(
        settings, transport=httpx.MockTransport(handler), timeout=12.0
    )
    source.generate("the prompt")
    assert captured[0].extensions["timeout"]["read"] == 12.0


# --- prompts -------------------------------------------------------------------


def test_system_prompt_states_the_four_bans() -> None:
    system = build_system_prompt()
    for fragment in ("causal", "advice", "forecast", "rankings", "exactly"):
        assert fragment in system


def test_prompt_carries_validated_claims_only() -> None:
    facts = BriefingFacts.from_observations(
        [obs(period="2024-01-01", value=2.8), obs()]
    )
    adjudicated = adjudicate_all(build_claims(facts), facts)
    validated = [c for c, a in adjudicated if a.validated]
    rejected = [c for c, a in adjudicated if not a.validated]
    prompt = build_prompt(facts, validated)
    for claim in validated:
        assert claim.text in prompt
    for claim in rejected:
        assert claim.text not in prompt
    assert TEST_KEY not in prompt  # no secret may reach the wire
    assert str(len(facts.facts)) in prompt  # partition counts are present


def test_prompt_mentions_missingness_rule() -> None:
    facts = BriefingFacts.from_observations(
        [
            obs(),
            obs(period="2024-01-01", value=None, missing_reason="series_gap"),
        ]
    )
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    prompt = build_prompt(facts, validated)
    assert "missing" in prompt


def test_prompt_v2_compresses_availability_to_indicator_summary() -> None:
    # The llm-v2 trim: per-observation availability claims (91-93% of a
    # panel-scale prompt, measured 2026-10-29) never travel verbatim;
    # the summary names the distinct indicators instead, and the
    # statement material stays exact.
    facts = BriefingFacts.from_observations(
        [
            obs(),
            obs(period="2024-01-01", value=None, missing_reason="series_gap"),
            obs(period="2023-01-01", value=None, missing_reason="series_gap"),
        ]
    )
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    availability = [c for c in validated if c.kind == "availability"]
    assert len(availability) == 2  # the fixture really exercises the trim

    prompt = build_prompt(facts, validated)
    for claim in availability:
        assert claim.text not in prompt  # no per-period wall
    assert "gdp_real_growth" in prompt  # the summary names the indicator
    for claim in validated:
        if claim.kind in ("level", "change"):
            assert claim.text in prompt  # statement material verbatim


def test_prompt_v2_summary_does_not_grow_per_observation() -> None:
    # Sixty missing periods across one indicator: the summary is
    # per-indicator, so the prompt stays far smaller than the claims it
    # compresses - the property that makes the cross-border LLM call fit
    # inside its timeout.
    many_missing = [
        obs(period=f"{year}-01-01", value=None, missing_reason="series_gap")
        for year in range(1960, 2020)
    ]
    facts = BriefingFacts.from_observations([obs(), *many_missing])
    validated = [
        c
        for c, a in adjudicate_all(build_claims(facts), facts)
        if a.validated
    ]
    prompt = build_prompt(facts, validated)
    total_claim_chars = sum(len(c.text) for c in validated)
    assert total_claim_chars > 4000  # the fixture really is panel-scale
    assert len(prompt) < total_claim_chars // 4


# --- HTTP path ------------------------------------------------------------------


def _ok_body(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def test_generate_request_shape_and_happy_path(llm_env) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_ok_body("Growth stood at 2.9."))

    source = _source(handler, LLMSettings.from_env())
    prose = source.generate("the prompt")

    request = captured[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {TEST_KEY}"
    assert request.headers["Content-Type"] == "application/json"
    body = json.loads(request.content)
    assert body["model"] == "test-model-1"
    assert body["temperature"] == 0.2
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["system", "user"]
    assert body["messages"][1]["content"] == "the prompt"
    assert prose == "Growth stood at 2.9."
    assert source.model == "test-model-1"
    assert source.prompt_version == LLM_PROMPT_VERSION


def test_generate_merges_extra_body_under_fixed_keys(
    monkeypatch, llm_env
) -> None:
    # Provider knobs travel along; the fixed keys are never overridden
    # by configuration.
    monkeypatch.setenv(
        "LLM_EXTRA_BODY",
        '{"enable_thinking": false, "model": "evil-override", '
        '"temperature": 9.9}',
    )
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_ok_body("Growth stood at 2.9."))

    source = _source(handler, LLMSettings.from_env())
    source.generate("the prompt")
    body = json.loads(captured[0].content)
    assert body["enable_thinking"] is False
    assert body["model"] == "test-model-1"
    assert body["temperature"] == 0.2


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_generate_http_error_status(llm_env, status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="upstream said no")

    source = _source(handler, LLMSettings.from_env())
    with pytest.raises(LLMResponseError) as excinfo:
        source.generate("the prompt")
    message = str(excinfo.value)
    assert f"HTTP {status}" in message
    assert TEST_KEY not in message  # secret hygiene


def test_generate_malformed_json(llm_env) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="this is not json at all")

    source = _source(handler, LLMSettings.from_env())
    with pytest.raises(LLMResponseError, match="malformed JSON"):
        source.generate("the prompt")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": 42}}]},
        _ok_body("   "),  # blank prose is not prose
    ],
)
def test_generate_bad_response_shape(llm_env, body) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    source = _source(handler, LLMSettings.from_env())
    with pytest.raises(LLMResponseError, match="empty prose"):
        source.generate("the prompt")


def test_generate_transport_error(llm_env) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    source = _source(handler, LLMSettings.from_env())
    with pytest.raises(LLMTransportError) as excinfo:
        source.generate("the prompt")
    assert "unreachable" in str(excinfo.value)
    assert TEST_KEY not in str(excinfo.value)


def test_from_env_resolves_at_call_time(monkeypatch) -> None:
    # D3: no import-time capture - clearing the env AFTER import must
    # still surface as a configuration error.
    _clear_llm_env(monkeypatch)
    with pytest.raises(LLMConfigError):
        HttpLlmSource.from_env()
