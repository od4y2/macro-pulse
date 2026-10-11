"""Smoke check: the query service assembles and its health endpoint answers.

Requires the configured database to be reachable - the S13 service is
database-backed, so an unreachable database is a truthful failure, not a
condition to paper over.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from macropulse.api.main import create_app


def main() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")
    payload = response.json()
    if response.status_code != 200 or payload.get("status") != "ok":
        raise SystemExit(f"smoke test failed: {payload}")
    print(f"MacroPulse query service smoke test passed: {payload}")


if __name__ == "__main__":
    main()
