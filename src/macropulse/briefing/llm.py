"""LLM prose source for the briefing layer (the S16 extension point).

docs/AIBriefing.md: an LLM plugs in as *another prose source* - whatever
it produces must survive the same claim adjudication and banned-phrase
check, and its identifier replaces ``deterministic-template`` in
``briefing_runs.model``. This module implements the caller side of that
contract:

- Configuration is read from the environment **at call time**
  (``LLMSettings.from_env``), never at import: the FastAPI app object is
  created at module import, and the cloud runtime bridges secrets into
  ``os.environ`` before boot - call-time reads work with both.
- Wire format: OpenAI-compatible ``POST {LLM_BASE_URL}/chat/completions``
  over raw httpx (the house HTTP style - no SDK dependency).
  ``LLM_PROVIDER`` accepts ``openai-compatible`` (the default); anything
  else is a typed configuration error, never a silent guess.
- Provider interop: the optional ``LLM_EXTRA_BODY`` environment variable
  carries a JSON object merged UNDER the fixed request keys (model,
  messages, temperature always win) - e.g. ``{"enable_thinking": false}``
  for reasoning models whose thinking pass over a panel-scale prompt
  exceeds the timeout budget. Unset, the body is exactly the
  OpenAI-compatible minimum.
- The prompt is built ONLY from validated claim texts and partition
  counts (``build_prompt``) - the LLM never sees raw database rows, and
  its output is gated downstream by ``check_prose`` and
  ``check_numeric_fidelity`` before it may render.
- Timeout: the read timeout defaults to ``LLM_TIMEOUT_SECONDS`` and is
  overridable per deployment via the ``LLM_TIMEOUT_SECONDS`` environment
  variable (read at call time, validated against ``LLM_TIMEOUT_MIN`` /
  ``LLM_TIMEOUT_MAX``). It is nested inside the dashboard client's
  ``BRIEFING_TIMEOUT`` so the deterministic fallback renders in-request.
- Secret hygiene: the API key lives in a ``SecretStr``; error messages
  carry the HTTP status and a truncated body only, never the key.
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, SecretStr

from macropulse.briefing.claims import Claim
from macropulse.briefing.facts import BriefingFacts

# Nested timeout budget (see plan D11): the LLM call must fail before the
# dashboard-side client timeout (views/client.py BRIEFING_TIMEOUT, 120 s)
# so the deterministic fallback still renders inside the API request.
# Default sized against the real panel-scale prompt (~20 K tokens,
# 19-32 s generations measured from the best-case network 2026-10-29;
# the cross-border cloud path needs headroom past that). Per-deployment
# override: the LLM_TIMEOUT_SECONDS environment variable, read at call
# time like every other LLM_* key.
LLM_TIMEOUT_SECONDS = 90.0

# Sanity bounds for the environment override, in seconds.
LLM_TIMEOUT_MIN = 1.0
LLM_TIMEOUT_MAX = 600.0

# Recorded in briefing_runs.prompt_version (String(32)).
LLM_PROMPT_VERSION = "llm-v1"

# Closed vocabulary of supported wire formats.
SUPPORTED_PROVIDERS = ("openai-compatible",)

# Same rationale as views/client.py: loopback destinations must bypass
# OS-level proxies (the macOS system proxy answers loopback with 502);
# non-loopback URLs keep environment-driven proxy behavior.
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _is_loopback(url: str) -> bool:
    return (urlparse(url).hostname or "") in _LOOPBACK_HOSTS


class LLMError(RuntimeError):
    """Base class for LLM prose-source failures (always fallback-safe)."""


class LLMConfigError(LLMError):
    """LLM_* environment configuration is missing or unsupported."""


class LLMTransportError(LLMError):
    """The LLM endpoint could not be reached."""


class LLMResponseError(LLMError):
    """The LLM endpoint answered, but not with usable prose."""


class LLMSettings(BaseModel):
    """Resolved LLM configuration. ``api_key`` never appears in reprs."""

    provider: str = "openai-compatible"
    base_url: str
    model: str
    api_key: SecretStr
    # Provider-interop knobs merged UNDER the fixed request keys (the
    # client never lets this override model/messages/temperature).
    extra_body: dict[str, Any] = Field(default_factory=dict)
    # Read timeout for the /chat/completions call; env-overridable
    # (LLM_TIMEOUT_SECONDS), validated at parse time.
    timeout_seconds: float = LLM_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> LLMSettings:
        """Read ``LLM_*`` from the environment at call time.

        Raises ``LLMConfigError`` naming the missing VARIABLES (names
        only, never values), an unsupported provider, an over-long
        model identifier (``briefing_runs.model`` is String(128)), or a
        malformed ``LLM_EXTRA_BODY``.
        """
        provider = os.environ.get("LLM_PROVIDER", "openai-compatible").strip()
        base_url = os.environ.get("LLM_BASE_URL", "").strip()
        model = os.environ.get("LLM_MODEL", "").strip()
        api_key = os.environ.get("LLM_API_KEY", "").strip()

        missing = [
            name
            for name, value in (
                ("LLM_BASE_URL", base_url),
                ("LLM_MODEL", model),
                ("LLM_API_KEY", api_key),
            )
            if not value
        ]
        if missing:
            raise LLMConfigError(
                f"LLM configuration incomplete: missing {', '.join(missing)}"
            )
        if provider not in SUPPORTED_PROVIDERS:
            raise LLMConfigError(
                f"unsupported LLM_PROVIDER {provider!r}; "
                f"supported: {', '.join(SUPPORTED_PROVIDERS)}"
            )
        if len(model) > 128:
            raise LLMConfigError(
                "LLM_MODEL exceeds the 128-char briefing_runs.model column"
            )
        extra_body = _parse_extra_body(os.environ.get("LLM_EXTRA_BODY", ""))
        timeout_seconds = _parse_timeout(
            os.environ.get("LLM_TIMEOUT_SECONDS", "")
        )
        return cls(
            provider=provider,
            base_url=base_url.rstrip("/"),
            model=model,
            api_key=SecretStr(api_key),
            extra_body=extra_body,
            timeout_seconds=timeout_seconds,
        )


def _parse_extra_body(raw: str) -> dict[str, Any]:
    """Parse ``LLM_EXTRA_BODY`` (a JSON object) for provider interop.

    Empty means no extra keys - the request body stays the
    OpenAI-compatible minimum. Anything malformed is a typed
    configuration error naming the variable (never its value), so the
    fallback path reports it honestly.
    """
    raw = raw.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise LLMConfigError("LLM_EXTRA_BODY is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise LLMConfigError("LLM_EXTRA_BODY must be a JSON object")
    return parsed


def _parse_timeout(raw: str) -> float:
    """Parse the ``LLM_TIMEOUT_SECONDS`` read-timeout override.

    Empty means the default (``LLM_TIMEOUT_SECONDS``). A non-numeric or
    out-of-bounds value is a typed configuration error naming the
    variable (never its value), so the fallback path reports it honestly
    rather than silently clamping.
    """
    raw = raw.strip()
    if not raw:
        return LLM_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError as exc:
        raise LLMConfigError("LLM_TIMEOUT_SECONDS is not a number") from exc
    if not LLM_TIMEOUT_MIN <= value <= LLM_TIMEOUT_MAX:
        raise LLMConfigError(
            f"LLM_TIMEOUT_SECONDS out of range "
            f"[{LLM_TIMEOUT_MIN:g}, {LLM_TIMEOUT_MAX:g}]"
        )
    return value


def build_system_prompt() -> str:
    """Standing instructions for the LLM prose source."""
    return (
        "You write the statements section of a structured macroeconomic "
        "briefing. Rules, enforced mechanically on your output:\n"
        "- State ONLY what the provided validated claims state. Copy every "
        "number, unit, period, and source exactly as given - never "
        "round, convert, compute, or introduce any other number (writing "
        "counts as words is safest).\n"
        "- No causal phrasing (because, due to, driven by, leads to).\n"
        "- No investment advice or recommendations.\n"
        "- No forecasts or forward-looking statements (will rise, expected "
        "to, outlook).\n"
        "- No merit rankings (best, worst, strongest, outperforms).\n"
        "- Name missing observations as missing; never imply a value.\n"
        "- Do not state scope counts or totals; a machine-composed footer "
        "carries them.\n"
        "- Plain markdown prose, no links, no headings, no tables. "
        "Short paragraphs or bullet lists only."
    )


def build_prompt(facts: BriefingFacts, validated_claims: list[Claim]) -> str:
    """The user message: validated claim texts verbatim, nothing else.

    The LLM sees only what a statement may be derived from - the
    validated claims (exact values, units, periods, citations) plus the
    partition counts it must not contradict. Raw rows, excluded
    observations' values, and anything unvalidated never appear.
    """
    lines: list[str] = []
    lines.append(
        "Draft the statements section for a single-country briefing from "
        "these validated claims only:"
    )
    lines.append("")
    for claim in validated_claims:
        lines.append(f"[{claim.kind}] {claim.text}")
    lines.append("")
    lines.append(
        f"Partition context (do not restate as counts): "
        f"{len(facts.facts)} validated observation(s), "
        f"{len(facts.missing)} recorded missing, "
        f"{len(facts.excluded)} excluded (not real evidence - never state "
        "them as observed)."
    )
    if facts.missing:
        lines.append(
            "Missing observations are covered by the availability claims "
            "above; name the missingness, never a value."
        )
    return "\n".join(lines)


class LlmSource(Protocol):
    """A prose source with its recorded identity (D5).

    ``record_briefing_run`` persists the generator identity beside the
    claims, so identity and caller travel together.
    """

    @property
    def model(self) -> str: ...

    @property
    def prompt_version(self) -> str: ...

    def generate(self, prompt: str) -> str:
        """Return prose for ``prompt``; raise an ``LLMError`` subclass."""
        ...


class HttpLlmSource:
    """OpenAI-compatible ``/chat/completions`` source over raw httpx."""

    def __init__(
        self,
        settings: LLMSettings,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport
        # An explicit timeout wins (tests); otherwise the configured
        # per-deployment value from settings, which from_env resolves
        # from LLM_TIMEOUT_SECONDS with the module default behind it.
        self._timeout = (
            timeout if timeout is not None else settings.timeout_seconds
        )

    @classmethod
    def from_env(cls) -> HttpLlmSource:
        return cls(LLMSettings.from_env())

    @property
    def model(self) -> str:
        return self._settings.model

    @property
    def prompt_version(self) -> str:
        return LLM_PROMPT_VERSION

    def generate(self, prompt: str) -> str:
        url = f"{self._settings.base_url}/chat/completions"
        # extra_body merged UNDER the fixed keys: provider knobs (e.g.
        # enable_thinking) travel along, but model/messages/temperature
        # are never overridden by configuration.
        payload = {
            **self._settings.extra_body,
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        with httpx.Client(
            transport=self._transport,
            timeout=self._timeout,
            trust_env=not _is_loopback(url),
        ) as client:
            try:
                response = client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                # str(exc) may carry the URL, never the Authorization header.
                raise LLMTransportError(
                    f"LLM endpoint unreachable at {url}: {exc}"
                ) from exc
        if response.status_code != 200:
            raise LLMResponseError(
                f"LLM endpoint returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise LLMResponseError(
                f"LLM endpoint returned malformed JSON: {response.text[:200]}"
            ) from exc
        content = _extract_content(body)
        if not content:
            raise LLMResponseError("LLM endpoint returned empty prose")
        return content


def _extract_content(body: object) -> str | None:
    """``choices[0].message.content`` from an OpenAI-compatible body.

    Returns None for any shape deviation - a malformed answer is a
    response error, never a guess at where prose might hide.
    """
    if not isinstance(body, dict):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    return content.strip() or None
