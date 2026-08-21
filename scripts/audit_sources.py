"""Reproducible live source audit (unit S05).

Probes every catalog source code against the live APIs and prints a
verification table. World Bank and ILOSTAT need no key; FRED codes are
probed only when FRED_API_KEY is set (otherwise reported as SKIPPED).
Run:

    PYTHONPATH=src python scripts/audit_sources.py

Output is truth-only: each line records what the live API actually
returned. Redirect to a file to capture evidence.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import httpx

from macropulse.catalog import CATALOG
from macropulse.connectors.base import ConnectorError
from macropulse.connectors.fred import FredConnector
from macropulse.connectors.ilostat import IlostatConnector
from macropulse.connectors.worldbank import WorldBankConnector

PROBE_COUNTRY = "USA"


def _load_local_env(path: str = ".env.local") -> None:
    """Load key=value pairs from a local env file without overriding
    already-set environment variables. File is gitignored; keys never
    appear in script output."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    _load_local_env()
    wb = WorldBankConnector()
    ilo = IlostatConnector()
    fred = FredConnector()  # live only when FRED_API_KEY is set
    failures = 0
    print(f"# Source audit {datetime.now(UTC).isoformat()}")
    print(f"probe country: {PROBE_COUNTRY}")
    print(f"fred live mode: {fred.live}")
    for ind in CATALOG:
        for role, ref in (("primary", ind.primary_source), ("fallback", ind.fallback_source)):
            if ref is None:
                continue
            try:
                if ref.system == "world_bank":
                    series = wb.fetch_indicator(ref.code, PROBE_COUNTRY, start_year=2020)
                elif ref.system == "ilostat":
                    series = ilo.fetch_dataflow(ref.code, PROBE_COUNTRY, start_year=2020)
                elif ref.system == "fred":
                    if not fred.live:
                        print(
                            f"SKIP  {ind.indicator_id:28s} {role:8s} fred        "
                            f"{ref.code:24s} no FRED_API_KEY set"
                        )
                        continue
                    series = fred.fetch_series(ref.code)
                else:
                    continue
                non_null = [p for p in series.points if p.value is not None]
                print(
                    f"OK    {ind.indicator_id:28s} {role:8s} {ref.system:11s} "
                    f"{ref.code:24s} points={len(series.points)} "
                    f"non-null={len(non_null)}"
                )
            except (ConnectorError, httpx.HTTPError) as exc:
                failures += 1
                print(
                    f"FAIL  {ind.indicator_id:28s} {role:8s} {ref.system:11s} "
                    f"{ref.code:24s} {exc}"
                )
    print(f"# failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
