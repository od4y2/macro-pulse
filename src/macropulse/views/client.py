"""Query-service client for the dashboard (unit S14).

A thin typed client over the S13 FastAPI service: one method per endpoint,
transparent pagination (the service caps pages at 500 rows), and explicit
errors - never fabricated rows on failure.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

# Must match the service's MAX_LIMIT (src/macropulse/api/routes.py).
DEFAULT_PAGE_SIZE = 500
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 30.0

# Nested timeout budget (plan D11): the service's LLM call fails at its
# LLM_TIMEOUT_SECONDS (default 240 s) and renders the deterministic
# fallback inside the request, so the client must wait longer than that -
# never abort before the fallback. Kept above the LLM default with margin
# for a deployment that raises LLM_TIMEOUT_SECONDS toward its 600 s cap;
# tests/test_views.py asserts LLM_TIMEOUT_SECONDS < BRIEFING_TIMEOUT.
# On the cloud host this hop is in-process (loopback), so no external
# proxy sits between the dashboard and the service to cut the wait short.
BRIEFING_TIMEOUT = 300.0

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _is_loopback(url: str) -> bool:
    # urlparse().hostname is already lowercase and bracket-free ("::1")
    return (urlparse(url).hostname or "") in _LOOPBACK_HOSTS


class QueryServiceError(RuntimeError):
    """The query service is unreachable or answered with an error."""


class QueryServiceClient:
    """Fetch typed responses from the MacroPulse query service.

    ``base_url`` defaults to the local service and can be redirected via
    the ``MACROPULSE_API_URL`` environment variable (see ``from_env``);
    ``transport`` lets tests inject an ``httpx.MockTransport``.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: float = REQUEST_TIMEOUT,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> None:
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be within the service's [1, 500] limit")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._page_size = page_size
        self._transport = transport

    @property
    def base_url(self) -> str:
        return self._base_url

    @classmethod
    def from_env(cls, **kwargs: Any) -> QueryServiceClient:
        import os

        return cls(os.environ.get("MACROPULSE_API_URL", DEFAULT_BASE_URL), **kwargs)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """One request; transport failures and non-200s become QueryServiceError."""
        # Loopback calls must never be routed through a proxy: with
        # trust_env, httpx picks up OS-level proxy settings (on macOS the
        # system-wide proxy, e.g. a local Clash-style listener), which
        # answers loopback destinations with HTTP 502 - the query service
        # never sees the request. Non-loopback base URLs keep the default
        # environment-driven behavior.
        with httpx.Client(
            transport=self._transport,
            timeout=self._timeout if timeout is None else timeout,
            trust_env=not _is_loopback(self._base_url),
        ) as client:
            try:
                response = client.request(
                    method, f"{self._base_url}{path}", params=params, json=json
                )
            except httpx.HTTPError as exc:
                raise QueryServiceError(
                    f"query service unreachable at {self._base_url}: {exc}"
                ) from exc
        if response.status_code != 200:
            raise QueryServiceError(
                f"{method} {path} -> HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
        return response

    def _get(self, path: str, params: dict[str, str]) -> Any:
        return self._request("GET", path, params=params).json()

    def _get_all(self, path: str, params: dict[str, str]) -> list[dict]:
        """GET every page of a list endpoint.

        Pages follow ``X-Total-Count`` until the announced total is
        collected; a stream longer than announced is an error, not a
        silent partial result.
        """
        rows: list[dict] = []
        offset = 0
        while True:
            response = self._request(
                "GET",
                path,
                params={
                    **params,
                    "limit": str(self._page_size),
                    "offset": str(offset),
                },
            )
            page = response.json()
            rows.extend(page)
            offset += len(page)
            if not page:
                break
            announced = response.headers.get("X-Total-Count")
            if announced is None:
                # No count header (defensive): a full page may have a
                # successor; a short one cannot.
                if len(page) < self._page_size:
                    break
                continue
            if offset > int(announced):
                raise QueryServiceError(
                    f"GET {path}: service returned more rows ({offset}) than "
                    f"announced ({announced})"
                )
            if offset >= int(announced):
                break
        return rows

    def health(self) -> dict:
        return self._get("/health", {})

    def countries(self) -> list[dict]:
        return self._get_all("/countries", {})

    def indicators(self, module: str | None = None) -> list[dict]:
        params = {"module": module} if module else {}
        return self._get_all("/indicators", params)

    def observations(
        self,
        indicator_id: str | None = None,
        country_iso3: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        vintage: str | None = None,
        evidence_label: str | None = None,
        quality_grade: str | None = None,
        missing: bool | None = None,
        latest_vintage: bool = False,
    ) -> list[dict]:
        params: dict[str, str] = {}
        if indicator_id is not None:
            params["indicator_id"] = indicator_id
        if country_iso3 is not None:
            params["country_iso3"] = country_iso3
        if period_start is not None:
            params["period_start"] = period_start
        if period_end is not None:
            params["period_end"] = period_end
        if vintage is not None:
            params["vintage"] = vintage
        if evidence_label is not None:
            params["evidence_label"] = evidence_label
        if quality_grade is not None:
            params["quality_grade"] = quality_grade
        if missing is not None:
            params["missing"] = str(missing).lower()
        if latest_vintage:
            params["latest_vintage"] = "true"
        return self._get_all("/observations", params)

    def metrics(
        self,
        metric_key: str | None = None,
        country_iso3: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        params: dict[str, str] = {}
        if metric_key is not None:
            params["metric_key"] = metric_key
        if country_iso3 is not None:
            params["country_iso3"] = country_iso3
        if period_start is not None:
            params["period_start"] = period_start
        if period_end is not None:
            params["period_end"] = period_end
        return self._get_all("/metrics", params)

    def generate_briefing(self, country_iso3: str) -> dict:
        """POST /briefing: one on-demand generation for one country.

        Never cached by the caller's conventions - every call is one real
        generation and one appended ``briefing_runs`` row. The longer
        timeout spans the service-side LLM call; a service-side LLM
        failure still answers 200 with ``status="fallback"``.
        """
        return self._request(
            "POST",
            "/briefing",
            json={"country_iso3": country_iso3},
            timeout=BRIEFING_TIMEOUT,
        ).json()

    def briefing_run(self, run_id: int) -> dict:
        """GET /briefing/{run_id}: the persisted audit record of one run."""
        return self._get(f"/briefing/{run_id}", {})
