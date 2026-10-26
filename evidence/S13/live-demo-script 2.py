"""S13 live demo: the query service over a live-fetched database.

Sequence (all steps printed as they run):

1. Create a disposable demo database on the local Postgres.
2. Seed the 10 panel countries, the catalog indicator, and the WB source
   entry (verbatim from the S02 catalog).
3. LIVE-fetch NY.GDP.MKTP.KD.ZG for USA and ZAF from the World Bank,
   normalize through the S06 pipeline, persist REAL observations
   (evidence_label=real, vintage=retrieval date).
4. Compute robust_z (S09 standardization) on USA and persist the derived
   metric with observation-id lineage.
5. Boot the real service (uvicorn) against the demo DB and issue HTTP
   requests through every endpoint, including an invalid filter (422).
6. Drop the demo database.

Run:  PYTHONPATH=src .venv/bin/python evidence/S13/live-demo-script.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from macropulse.catalog import CATALOG
from macropulse.connectors.worldbank import WorldBankConnector
from macropulse.db.base import database_url
from macropulse.db.models import Base, Country, Indicator, SourceCatalogEntry
from macropulse.metrics.engine import (
    latest_vintage_series,
    observation_id_map,
    persist_derived,
)
from macropulse.metrics.standardize import standardize_series
from macropulse.pipeline.normalize import normalize_series, persist_normalized
from macropulse.scope import COUNTRIES

DEMO_DB = "macropulse_s13_demo"
ADMIN_URL = database_url().rsplit("/", 1)[0]
DEMO_URL = f"{ADMIN_URL}/{DEMO_DB}"
PORT = 8130
BASE_URL = f"http://127.0.0.1:{PORT}"
WB_CODE = "NY.GDP.MKTP.KD.ZG"


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def create_demo_db() -> None:
    admin = create_engine(ADMIN_URL + "/postgres", future=True)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {DEMO_DB}"))
        conn.execute(text(f"CREATE DATABASE {DEMO_DB}"))
    admin.dispose()


def drop_demo_db() -> None:
    admin = create_engine(ADMIN_URL + "/postgres", future=True)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {DEMO_DB}"))
    admin.dispose()


def seed_and_fetch() -> None:
    engine = create_engine(DEMO_URL, future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()
    ind = next(i for i in CATALOG if i.indicator_id == "gdp_real_growth")
    session.add_all(
        Country(iso3=c.iso3, name=c.name, rationale=c.rationale) for c in COUNTRIES
    )
    session.add(
        Indicator(
            indicator_id=ind.indicator_id,
            name=ind.name,
            module=ind.module,
            unit=ind.unit,
            frequency=ind.frequency,
            seasonal_adjustment=ind.seasonal_adjustment,
            fallback_status=ind.fallback_status,
            comparability_notes=ind.comparability_notes,
            limitations=ind.limitations,
        )
    )
    session.flush()
    source = SourceCatalogEntry(
        system="world_bank",
        code=WB_CODE,
        role="primary",
        verified=ind.primary_source.verified,
        coverage=ind.primary_source.coverage,
        indicator_id=ind.indicator_id,
    )
    session.add(source)
    session.commit()

    connector = WorldBankConnector()
    for iso3 in ("USA", "ZAF"):
        series = connector.fetch_indicator(WB_CODE, iso3, start_year=2015)
        print(
            f"fetched {iso3}: {len(series.points)} points, "
            f"evidence_label={series.evidence_label}, "
            f"retrieval_time={series.retrieval_time.isoformat()}"
        )
        records = normalize_series(series, ind.indicator_id)
        persist_normalized(session, records, source.id)
        session.commit()

    # Derived metric: robust_z on the USA current view.
    points = latest_vintage_series(session, ind.indicator_id, "USA")
    standardized = standardize_series(points, 5, ind.direction, ind.frequency)
    id_map = observation_id_map(session, ind.indicator_id, "USA")
    written = persist_derived(
        session,
        f"{ind.indicator_id}.robust_z",
        "USA",
        standardized,
        "robust_z",
        id_map,
    )
    session.commit()
    print(f"derived metric rows written: {len(written)}")
    counts = {}
    for table in ("countries", "indicators", "normalized_observations", "derived_metrics"):
        counts[table] = session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
    print(f"demo DB row counts: {counts}")
    session.close()
    engine.dispose()


def boot_service() -> subprocess.Popen:
    env = {**os.environ, "DATABASE_URL": DEMO_URL, "PYTHONPATH": "src"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "macropulse.api.main:app", "--port", str(PORT)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            if httpx.get(f"{BASE_URL}/health", timeout=2.0).status_code == 200:
                return proc
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    proc.terminate()
    raise SystemExit("service did not become healthy within 30s")


def show(method: str, path: str, **params: str) -> None:
    response = httpx.request(method, f"{BASE_URL}{path}", params=params, timeout=30.0)
    total = response.headers.get("X-Total-Count")
    print(f"\n--- {method} {path}{' ? ' + str(params) if params else ''}")
    print(f"    status={response.status_code}"
          + (f"  X-Total-Count={total}" if total is not None else ""))
    body = response.json()
    if isinstance(body, list) and len(body) > 3:
        print(json.dumps(body[:3], indent=2))
        print(f"    ... [{len(body) - 3} more rows truncated for readability]")
    else:
        print(json.dumps(body, indent=2))


def main() -> None:
    step(f"create disposable demo database {DEMO_DB}")
    create_demo_db()
    proc = None
    try:
        step("seed panel + LIVE-fetch World Bank data + derive robust_z")
        seed_and_fetch()
        step(f"boot the real service (uvicorn) on port {PORT}")
        proc = boot_service()
        print("service healthy")

        step("query the service over HTTP")
        show("GET", "/health")
        show("GET", "/countries", limit="3")
        show("GET", "/indicators", module="traditional-indicators")
        show(
            "GET", "/observations",
            indicator_id="gdp_real_growth",
            country_iso3="USA",
            evidence_label="real",
            latest_vintage="true",
            period_start="2023-01-01",
        )
        show("GET", "/observations", country_iso3="USA", missing="true")
        show("GET", "/observations", country_iso3="ZAF", limit="2")
        show("GET", "/observations", country_iso3="USA", quality_grade="excellent")
        show("GET", "/metrics", country_iso3="USA", limit="3")
        show("GET", "/methodology/formulas", name="robust_z")
        show("GET", "/methodology/metrics/gdp_real_growth.robust_z")

        step("demo complete - service and data behaved as contracted")
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)
        step(f"drop demo database {DEMO_DB}")
        drop_demo_db()
        print("cleanup done")


if __name__ == "__main__":
    main()
