"""Query-service client for the dashboard (unit S14).

A thin typed client over the S13 FastAPI service: one method per endpoint,
transparent pagination (the service caps pages at 500 rows), and explicit
errors - never fabricated rows on failure.
"""

from __future__ import annotations

from typing import Any

import httpx

# Must match the service's MAX_LIMIT (src/macropulse/api/routes.py).
DEFAULT_PAGE_SIZE = 500
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 30.0


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

    def _request(self, path: str, params: dict[str, str]) -> httpx.Response:
        """One GET; transport failures and non-200s become QueryServiceError."""
        with httpx.Client(transport=self._transport, timeout=self._timeout) as client:
            try:
                response = client.get(f"{self._base_url}{path}", params=params)
            except httpx.HTTPError as exc:
                raise QueryServiceError(
                    f"query service unreachable at {self._base_url}: {exc}"
                ) from exc
        if response.status_code != 200:
            raise QueryServiceError(
                f"GET {path} -> HTTP {response.status_code}: {response.text[:200]}"
            )
        return response

    def _get(self, path: str, params: dict[str, str]) -> Any:
        return self._request(path, params).json()

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
                path, {**params, "limit": str(self._page_size), "offset": str(offset)}
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
