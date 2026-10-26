"""Scheduled-refresh orchestrator and CLI (unit S17).

One refresh cycle = one ``refresh_runs`` row + one raw+normalized pass per
planned series. The layer is deliberately BOUNDED and HONEST:

- **Plan**: every catalog indicator's PRIMARY source crossed with the
  countries that source actually covers (``SourceRef.countries``; None =
  whole panel). Fallback sources are NOT fetched by the scheduled layer
  (fallback application is a human decision, and the account_ownership
  "fallback" is a different measure - the female variant - not a
  country alternative).
- **Revision-diff persistence**: a normalized row is born when a period
  is first observed, or when its (value, missing_reason) changed versus
  the latest stored vintage. Unchanged re-observations are archived in
  the raw store ONLY - the raw store is the complete retrieval archive,
  the normalized store is the revision chain. This is what makes
  re-runs idempotent (0 new rows) and keeps RQ4 chains readable (every
  row is a change, not a daily no-op).
- **No silent mocks**: FRED series without ``FRED_API_KEY`` fail with
  reason ``no_api_key``. The S04 no-key fixture mode is a test/dev
  convenience; a scheduled job filling the governed store with fixture
  data would be the "mocked presented as observed" failure the contract
  forbids.
- **Per-series isolation**: each series commits its raw archive first
  (the fetch DID happen), then its normalized rows; one failing series
  never aborts the others, and progress is committed per series so a
  crash leaves an inspectable trail.

Run modes: ``python -m macropulse.ops.refresh`` (one cycle; cron-able),
``--daemon`` (the stdlib scheduler loop), ``--dry-run`` (print the plan,
touch nothing). Exit codes: 0 succeeded, 1 partial, 2 failed.
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable, Iterable
from contextlib import closing
from datetime import date
from typing import Any, NamedTuple

import httpx
from sqlalchemy.exc import SQLAlchemyError

from macropulse.catalog import CATALOG
from macropulse.connectors.base import ConnectorError, FetchedSeries
from macropulse.connectors.fred import FredConnector
from macropulse.connectors.ilostat import IlostatConnector
from macropulse.connectors.persist import PersistError, persist_raw_series
from macropulse.connectors.worldbank import WorldBankConnector
from macropulse.db.base import database_url, make_engine, make_session_factory
from macropulse.db.models import NormalizedObservation, RefreshRun
from macropulse.ops.logging_setup import log_event, setup_logging
from macropulse.ops.retry import (
    DEFAULT_RETRY_POLICY,
    RetryPolicy,
    fetch_with_retries,
    retryable,
)
from macropulse.ops.runs import (
    RUN_TRIGGERS,
    classify_run_status,
    finish_run,
    mark_interrupted_runs,
    start_run,
)
from macropulse.pipeline.normalize import (
    NormalizationError,
    normalize_series,
    persist_normalized,
)
from macropulse.scope import COUNTRIES

DEFAULT_LOG_FILE = "logs/refresh.jsonl"

EXIT_CODES = {"succeeded": 0, "partial": 1, "failed": 2}

ConnectorFactory = Callable[[str], Any]


class SeriesTarget(NamedTuple):
    indicator_id: str
    country_iso3: str
    system: str
    code: str


def plan_series(
    indicator_ids: Iterable[str] | None = None,
    country_iso3s: Iterable[str] | None = None,
) -> list[SeriesTarget]:
    """Plan the refresh: catalog primary sources x covered countries.

    Deterministic order (catalog order, then panel order). The covered
    countries come from the structured ``SourceRef.countries`` field, so
    a country-specific code (FEDFUNDS is US data) can never be planned
    for another economy. Pairs with no covering source are simply not
    planned - the dashboard's no_data state already presents absence
    honestly.
    """
    want_indicators = frozenset(indicator_ids) if indicator_ids is not None else None
    want_countries = frozenset(country_iso3s) if country_iso3s is not None else None
    panel = [c.iso3 for c in COUNTRIES]

    targets: list[SeriesTarget] = []
    for ind in CATALOG:
        if want_indicators is not None and ind.indicator_id not in want_indicators:
            continue
        ref = ind.primary_source
        covered = list(ref.countries) if ref.countries is not None else panel
        for iso3 in panel:  # panel order, not covered order
            if iso3 not in covered:
                continue
            if want_countries is not None and iso3 not in want_countries:
                continue
            targets.append(
                SeriesTarget(
                    indicator_id=ind.indicator_id,
                    country_iso3=iso3,
                    system=ref.system,
                    code=ref.code,
                )
            )
    return targets


def ensure_reference_data(session) -> dict[str, int]:
    """Insert-if-missing the locked panel countries and catalog indicators.

    Reference data is metadata from the locked S01/S02 sources, not
    observation data: seeding it is deterministic and traceable. Never
    updates or deletes - existing rows win.
    """
    from macropulse.db.models import Country, Indicator

    countries_added = 0
    for c in COUNTRIES:
        if session.get(Country, c.iso3) is None:
            session.add(Country(iso3=c.iso3, name=c.name, rationale=c.rationale))
            countries_added += 1
    indicators_added = 0
    for ind in CATALOG:
        if session.get(Indicator, ind.indicator_id) is None:
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
            indicators_added += 1
    session.commit()
    return {"countries_added": countries_added, "indicators_added": indicators_added}


def default_connector_factory(system: str):
    """Build the real connector for a source system (env-driven)."""
    if system == "world_bank":
        return WorldBankConnector()
    if system == "fred":
        return FredConnector()
    if system == "ilostat":
        return IlostatConnector()
    raise ValueError(f"unknown source system {system!r}")


def _do_fetch(connector, target: SeriesTarget) -> FetchedSeries:
    if target.system == "world_bank":
        return connector.fetch_indicator(target.code, target.country_iso3)
    if target.system == "fred":
        return connector.fetch_series(target.code, target.country_iso3)
    if target.system == "ilostat":
        return connector.fetch_dataflow(target.code, target.country_iso3)
    raise ValueError(f"unknown source system {target.system!r}")


def _latest_by_period(
    session, indicator_id: str, country_iso3: str, source_id: int
) -> dict[date, tuple[float | None, str | None]]:
    """Latest-stored (value, missing_reason) per period for one series."""
    rows = (
        session.query(NormalizedObservation)
        .filter_by(
            indicator_id=indicator_id,
            country_iso3=country_iso3,
            source_id=source_id,
        )
        .all()
    )
    best: dict[date, tuple] = {}
    for row in rows:
        prior = best.get(row.period)
        if prior is None or (row.vintage, row.id) > (prior[0], prior[1]):
            best[row.period] = (row.vintage, row.id, row.value, row.missing_reason)
    return {
        period: (None if v is None else float(v), reason)
        for period, (_, _, v, reason) in best.items()
    }


def refresh_series(
    session,
    target: SeriesTarget,
    connector_factory: ConnectorFactory,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    sleep=time.sleep,
    logger=None,
) -> dict:
    """Refresh one series: retry-bounded fetch -> raw archive ->
    normalize -> revision-diff into normalized. Returns the outcome dict
    (shape fixed by the run-record contract; failures carry a closed
    ``reason`` vocabulary)."""
    outcome: dict[str, Any] = {
        "indicator_id": target.indicator_id,
        "country_iso3": target.country_iso3,
        "system": target.system,
        "code": target.code,
        "status": "ok",
        "attempts": 0,
        "points_fetched": 0,
        "new_periods": 0,
        "revised_periods": 0,
        "unchanged_periods": 0,
        "reason": None,
        "detail": None,
    }
    if logger is not None:
        log_event(
            logger,
            "info",
            "series_started",
            indicator_id=target.indicator_id,
            country_iso3=target.country_iso3,
            system=target.system,
            code=target.code,
        )
    try:
        connector = connector_factory(target.system)
        if target.system == "fred" and not getattr(connector, "live", True):
            # The refresh layer never falls back to the mocked no-key
            # fixture: a missing key is a recorded failure, not fake data.
            outcome.update(
                status="failed",
                reason="no_api_key",
                detail=(
                    "FRED_API_KEY not set; the scheduled layer does not use "
                    "the mocked fixture mode"
                ),
            )
            return outcome

        def _on_retry(attempt: int, delay: float, exc: BaseException) -> None:
            if logger is not None:
                log_event(
                    logger,
                    "warning",
                    "series_retry",
                    indicator_id=target.indicator_id,
                    country_iso3=target.country_iso3,
                    attempt=attempt,
                    delay_seconds=delay,
                    error=str(exc),
                )

        result = fetch_with_retries(
            lambda: _do_fetch(connector, target), policy, sleep, _on_retry
        )
        series = result.series
        outcome["attempts"] = result.attempts
        outcome["points_fetched"] = len(series.points)

        # 1. The raw archive commits first: the fetch DID happen, and its
        #    payload is provenance even if normalization rejects the series.
        raw_rows = persist_raw_series(session, series, target.indicator_id)
        session.commit()

        # 2. Normalize under the locked S06 rules.
        records = normalize_series(series, target.indicator_id)
        # persist_raw_series wrote one row per point, so the source row
        # exists (normalize_series has already raised on an empty series).
        source_id = raw_rows[0].source_id

        # 3. Revision-diff: only new or changed periods become rows.
        latest = _latest_by_period(
            session, target.indicator_id, target.country_iso3, source_id
        )
        fresh = []
        for record in records:
            previous = latest.get(record.period)
            if previous is None:
                outcome["new_periods"] += 1
                fresh.append(record)
            elif previous != (record.value, record.missing_reason):
                outcome["revised_periods"] += 1
                fresh.append(record)
            else:
                outcome["unchanged_periods"] += 1
        persist_normalized(session, fresh, source_id)
        session.commit()
    except NormalizationError as exc:
        session.rollback()
        outcome.update(status="failed", reason="normalization_error", detail=str(exc))
    except (PersistError, SQLAlchemyError) as exc:
        session.rollback()
        outcome.update(status="failed", reason="persist_error", detail=str(exc))
    except (ConnectorError, httpx.TransportError) as exc:
        session.rollback()
        # A retryable error only escapes after the policy is exhausted
        # (attempts == max_attempts); a permanent error fails on attempt 1.
        attempts = policy.max_attempts if retryable(exc) else 1
        outcome.update(
            status="failed", reason="fetch_failed", detail=str(exc), attempts=attempts
        )
    except ValueError as exc:
        session.rollback()
        outcome.update(status="failed", reason="unknown", detail=str(exc))
    if logger is not None:
        log_event(logger, "info", "series_finished", **outcome)
    return outcome


def run_refresh(
    session,
    targets: list[SeriesTarget],
    connector_factory: ConnectorFactory | None = None,
    trigger: str = "manual",
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    sleep=time.sleep,
    logger=None,
) -> RefreshRun:
    """Execute one refresh cycle over ``targets`` and persist the run row."""
    if connector_factory is None:
        connector_factory = default_connector_factory
    interrupted = mark_interrupted_runs(session)
    if logger is not None and interrupted:
        log_event(logger, "warning", "run_interrupted_marked", run_ids=interrupted)
    ensure_reference_data(session)
    run = start_run(session, trigger, series_total=len(targets))
    if logger is not None:
        log_event(
            logger,
            "info",
            "run_started",
            run_id=run.id,
            trigger=trigger,
            series_total=len(targets),
        )

    outcomes: list[dict] = []
    for target in targets:
        outcome = refresh_series(
            session, target, connector_factory, policy, sleep, logger
        )
        outcomes.append(outcome)
        # Progress commits per series: a mid-run crash leaves an
        # inspectable trail (interrupted status + partial outcomes).
        run.series_total = len(outcomes)
        run.series_failed = sum(1 for o in outcomes if o["status"] == "failed")
        session.commit()

    status, error = classify_run_status(outcomes)
    finish_run(session, run, status, outcomes, error)
    if logger is not None:
        log_event(
            logger, "info", "run_finished", run_id=run.id, status=status, error=error
        )
    return run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="macropulse.ops.refresh",
        description=(
            "Scheduled refresh: fetch catalog primary sources for their covered "
            "panel countries, archive raw payloads, and persist new/changed "
            "normalized observations with full provenance."
        ),
    )
    parser.add_argument(
        "--indicator",
        action="append",
        default=None,
        metavar="ID",
        help="restrict to one indicator_id (repeatable)",
    )
    parser.add_argument(
        "--country",
        action="append",
        default=None,
        metavar="ISO3",
        help="restrict to one panel country (repeatable)",
    )
    parser.add_argument(
        "--trigger",
        choices=RUN_TRIGGERS,
        default="manual",
        help="why this cycle ran (recorded on the run row)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the planned series and exit; no fetch, no writes",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="run the scheduler loop (daily 06:00 UTC) instead of one cycle",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        metavar="PATH",
        help=f"JSONL log path (default {DEFAULT_LOG_FILE} under the CWD)",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        metavar="URL",
        help="database URL override (default DATABASE_URL / local docker-compose)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logger = setup_logging(
        args.log_file if args.log_file is not None else DEFAULT_LOG_FILE
    )

    targets = plan_series(args.indicator, args.country)

    if args.dry_run:
        log_event(logger, "info", "dry_run_plan", series_count=len(targets))
        print(f"dry run: {len(targets)} series planned (no fetch, no writes)")
        for target in targets:
            print(
                f"  {target.indicator_id} {target.country_iso3} "
                f"{target.system} {target.code}"
            )
        return 0

    engine = make_engine(args.db_url or database_url())
    session_factory = make_session_factory(engine)

    def one_cycle() -> str:
        with closing(session_factory()) as session:
            run = run_refresh(session, targets, trigger=args.trigger, logger=logger)
            return run.status

    if args.daemon:
        from macropulse.ops.scheduler import run_forever

        run_forever(one_cycle, logger=logger)
        return 0

    status = one_cycle()
    engine.dispose()
    return EXIT_CODES[status]


if __name__ == "__main__":
    raise SystemExit(main())
