"""Cloud-runtime secrets-bridge tests (the pure helper level).

``_bridge_key`` is the per-secret primitive behind ``_bridge_secrets``:
env-explicit wins, a missing secret is a silent skip, values land
verbatim, and nothing is ever logged. ``st.secrets`` itself is only
available on a secrets-configured host, so the bridge is tested through
the helper with fake mappings - no Streamlit runtime, no real values.
"""

from __future__ import annotations

import pytest

from macropulse.cloud_runtime import (
    BRIDGED_LLM_KEYS,
    _bridge_key,
    _normalize_scheme,
)


class _RaisingSecrets:
    """A secrets source whose every lookup fails (host without a file)."""

    def __getitem__(self, key: str) -> str:
        raise RuntimeError("StreamlitSecretNotFoundError stand-in")


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (*BRIDGED_LLM_KEYS, "DATABASE_URL", "NEON_DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)


def test_bridge_key_lands_verbatim(monkeypatch, clean_env) -> None:
    import os

    assert _bridge_key({"LLM_API_KEY": "sk-secret"}, "LLM_API_KEY") is True
    assert os.environ["LLM_API_KEY"] == "sk-secret"


def test_bridge_key_env_explicit_wins(monkeypatch, clean_env) -> None:
    monkeypatch.setenv("LLM_MODEL", "local-model")
    assert _bridge_key({"LLM_MODEL": "cloud-model"}, "LLM_MODEL") is False
    import os

    assert os.environ["LLM_MODEL"] == "local-model"


def test_bridge_key_missing_secret_is_silent_skip(monkeypatch, clean_env) -> None:
    import os

    assert _bridge_key({}, "LLM_BASE_URL") is False
    assert "LLM_BASE_URL" not in os.environ


def test_bridge_key_survives_raising_secrets(monkeypatch, clean_env) -> None:
    import os

    assert _bridge_key(_RaisingSecrets(), "LLM_PROVIDER") is False
    assert "LLM_PROVIDER" not in os.environ


def test_bridge_key_stringifies_non_str(monkeypatch, clean_env) -> None:
    import os

    assert _bridge_key({"LLM_MODEL": 42}, "LLM_MODEL") is True
    assert os.environ["LLM_MODEL"] == "42"


def test_bridged_llm_keys_vocabulary() -> None:
    # The names the briefing layer reads at call time - and only those;
    # the bridge never invents new configuration surface.
    assert BRIDGED_LLM_KEYS == (
        "LLM_PROVIDER",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_EXTRA_BODY",
    )


def test_normalize_scheme_only_touches_bare_postgresql() -> None:
    assert (
        _normalize_scheme("postgresql://u:p@host/db?sslmode=require")
        == "postgresql+psycopg://u:p@host/db?sslmode=require"
    )
    assert (
        _normalize_scheme("postgresql+psycopg://u:p@host/db")
        == "postgresql+psycopg://u:p@host/db"
    )
    assert _normalize_scheme("sqlite:///local.db") == "sqlite:///local.db"
