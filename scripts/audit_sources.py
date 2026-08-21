"""Reproducible live source audit (unit S05).

Probes every world_bank and ilostat code in the S02 catalog against the
live APIs (no key required) and prints a verification table. Run:

    PYTHONPATH=src python scripts/audit_sources.py

Output is truth-only: each line records what the live API actually
returned. Redirect to a file to capture evidence.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

import httpx

from macropulse.catalog import CATALOG
from macropulse.connectors.base import ConnectorError
from macropulse.connectors.ilostat import IlostatConnector
from macropulse.connectors.worldbank import WorldBankConnector

PROBE_COUNTRY = "USA"


def main() -> int:
    wb = WorldBankConnector()
    ilo = IlostatConnector()
    failures = 0
    print(f"# Source audit {datetime.now(UTC).isoformat()}")
    print(f"probe country: {PROBE_COUNTRY}")
    for ind in CATALOG:
        for role, ref in (("primary", ind.primary_source), ("fallback", ind.fallback_source)):
            if ref is None or ref.system not in ("world_bank", "ilostat"):
                continue
            try:
                if ref.system == "world_bank":
                    series = wb.fetch_indicator(ref.code, PROBE_COUNTRY, start_year=2020)
                else:
                    series = ilo.fetch_dataflow(ref.code, PROBE_COUNTRY, start_year=2020)
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
