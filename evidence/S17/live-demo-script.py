"""Live demo for S17 (output captured to evidence/S17/live-demo-output.txt).

Against a DISPOSABLE database (macropulse_s17_demo - created, migrated,
and dropped by this script; nothing touches the dev database):

1. Run A - live refresh of gdp_real_growth (10 economies, World Bank)
   with policy_rate ALSO planned but NO FRED key in the environment:
   the FRED series must fail honestly (no_api_key) while every World
   Bank series succeeds -> run status `partial`, exit code 1.
2. Run B - recovery run (trigger=recovery) of policy_rate with the key
   sourced from gitignored .env.local: the previously failed series now
   fetches live (FEDFUNDS, monthly since 1954) -> status `succeeded`.
3. Run C - immediate re-run of run A's scope: nothing changed at the
   providers, so the revision-diff persists 0 new rows -> idempotency.
4. Verification queries: the refresh_runs audit rows, evidence labels of
   the stored observations, the FEDFUNDS period range, and the JSONL
   structured-log lines.

The FRED key is read from .env.local into the subprocess environment
only; it is never printed, logged, or written to the output.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[2]
DEMO_DB = "macropulse_s17_demo"
DEMO_URL = "postgresql+psycopg://macropulse:macropulse@localhost:5432/" + DEMO_DB
ADMIN_URL = "postgresql+psycopg://macropulse:macropulse@localhost:5432/postgres"
PY = str(REPO / ".venv" / "bin" / "python")


def _base_env() -> dict[str, str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = DEMO_URL
    src = str(REPO / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def run_cli(args: list[str], fred_key: str | None) -> int:
    env = _base_env()
    if fred_key is None:
        env.pop("FRED_API_KEY", None)
    else:
        env["FRED_API_KEY"] = fred_key
    print(
        f"$ PYTHONPATH=src python -m macropulse.ops.refresh {' '.join(args)}"
        + ("" if fred_key is None else "   # FRED_API_KEY sourced from .env.local")
    )
    proc = subprocess.run(
        [PY, "-m", "macropulse.ops.refresh", *args],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    # Show the CLI's stderr (structured log stream); stdout carries the
    # human summary lines.
    sys.stdout.write(proc.stdout)
    for line in proc.stderr.splitlines():
        print(f"    {line}")
    print(f"-> exit code {proc.returncode}")
    return proc.returncode


def read_fred_key() -> str:
    env_line = next(
        (
            line
            for line in (REPO / ".env.local").read_text().splitlines()
            if line.startswith("FRED_API_KEY=")
        ),
        None,
    )
    if env_line is None:
        raise SystemExit("FRED_API_KEY not found in .env.local")
    return env_line.split("=", 1)[1].strip()


def _demo_runs(log_path: str) -> dict:
    """Runs A/B/C plus the database and log verification. Returns the
    facts the summary asserts on."""
    print()
    print("== Run A: live WB refresh + FRED series with NO key (safe failure) ==")
    code_a = run_cli(
        [
            "--indicator",
            "gdp_real_growth",
            "--indicator",
            "policy_rate",
            "--log-file",
            log_path,
        ],
        fred_key=None,
    )

    print()
    print("== Run B: recovery of the failed FRED series (key from .env.local) ==")
    code_b = run_cli(
        [
            "--indicator",
            "policy_rate",
            "--trigger",
            "recovery",
            "--log-file",
            log_path,
        ],
        fred_key=read_fred_key(),
    )

    print()
    print("== Run C: immediate re-run of run A's scope (idempotency) ==")
    code_c = run_cli(
        [
            "--indicator",
            "gdp_real_growth",
            "--indicator",
            "policy_rate",
            "--log-file",
            log_path,
        ],
        fred_key=None,
    )

    print()
    print("== Verification against the demo database ==")
    engine = create_engine(DEMO_URL, future=True)
    with engine.connect() as conn:
        print("-- refresh_runs audit rows --")
        run_rows = conn.execute(
            text(
                "SELECT id, trigger, status, series_total, series_failed, error"
                " FROM refresh_runs ORDER BY id"
            )
        ).fetchall()
        for row in run_rows:
            print(
                f"   run {row[0]}: trigger={row[1]} status={row[2]}"
                f" series={row[3]} failed={row[4]} error={row[5]!r}"
            )

        print("-- run A outcome detail (from outcomes JSON) --")
        outcomes_a = conn.execute(
            text("SELECT outcomes FROM refresh_runs WHERE id = 1")
        ).fetchone()[0]
        for outcome in outcomes_a:
            print(
                f"   {outcome['indicator_id']:<18} {outcome['country_iso3']}: "
                f"{outcome['status']:<7} reason={outcome['reason']!r} "
                f"points={outcome['points_fetched']} new={outcome['new_periods']}"
            )

        print("-- stored observations by indicator and evidence label --")
        for row in conn.execute(
            text(
                "SELECT indicator_id, evidence_label, count(*)"
                " FROM normalized_observations GROUP BY 1, 2 ORDER BY 1, 2"
            )
        ):
            print(f"   {row[0]:<24} {row[1]:<6} {row[2]} rows")

        print("-- FEDFUNDS period range and freshness of the run-B write --")
        row = conn.execute(
            text(
                "SELECT min(period), max(period), max(vintage), max(retrieval_time)"
                " FROM normalized_observations WHERE indicator_id = 'policy_rate'"
            )
        ).fetchone()
        print(f"   periods {row[0]} .. {row[1]} (vintage/retrieval {row[2]}/{row[3]})")

        print("-- gdp_real_growth latest values (sample, full precision) --")
        for row in conn.execute(
            text(
                "SELECT country_iso3, period, value, unit, evidence_label,"
                " quality_grade FROM normalized_observations"
                " WHERE indicator_id = 'gdp_real_growth' AND country_iso3 IN ('USA', 'ZAF')"
                " ORDER BY country_iso3, period DESC LIMIT 4"
            )
        ):
            print(
                f"   {row[0]} {row[1]} value={row[2]} {row[3]}"
                f" evidence={row[4]} grade={row[5]}"
            )

        outcomes_c = conn.execute(
            text("SELECT outcomes FROM refresh_runs WHERE id = 3")
        ).fetchone()[0]
    engine.dispose()

    print()
    print("== JSONL structured log (first 6 lines + retry/error events) ==")
    lines = Path(log_path).read_text().splitlines()
    for line in lines[:6]:
        print(f"   {line}")
    special = [l for l in lines if '"series_retry"' in l or '"level": "warning"' in l]
    if special:
        print("   ... warnings:")
        for line in special[:3]:
            print(f"   {line}")

    wb_new = [
        o["new_periods"] for o in outcomes_c if o["indicator_id"] == "gdp_real_growth"
    ]
    return {
        "code_a": code_a,
        "code_b": code_b,
        "code_c": code_c,
        "wb_new": wb_new,
        "n_runs": len(run_rows),
    }


def main() -> None:
    admin = create_engine(ADMIN_URL, future=True, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {DEMO_DB}"))
        conn.execute(text(f"CREATE DATABASE {DEMO_DB}"))
    admin.dispose()

    env = _base_env()
    print("== disposable demo database: alembic upgrade head ==")
    proc = subprocess.run(
        [PY, "-m", "alembic", "upgrade", "head"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    print(proc.stdout.strip() or proc.stderr.strip())

    with tempfile.TemporaryDirectory() as tmp:
        facts = _demo_runs(str(Path(tmp) / "refresh.jsonl"))

    print()
    print("== summary ==")
    print(f"   run A exit={facts['code_a']} (expected 1: partial - FRED no_api_key)")
    print(f"   run B exit={facts['code_b']} (expected 0: recovered)")
    print(
        f"   run C exit={facts['code_c']} (expected 1: partial again - key still"
        " absent, WB series idempotent)"
    )
    print(
        f"   run C gdp_real_growth new_periods per series: {facts['wb_new']}"
        " (all zero -> idempotent)"
    )
    ok = (
        facts["code_a"] == 1
        and facts["code_b"] == 0
        and facts["code_c"] == 1
        and all(v == 0 for v in facts["wb_new"])
        and facts["n_runs"] == 3
    )
    print(f"   DEMO {'PASSED' if ok else 'FAILED'}")

    admin = create_engine(ADMIN_URL, future=True, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {DEMO_DB}"))
    admin.dispose()
    print(f"== disposable database {DEMO_DB} dropped ==")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
