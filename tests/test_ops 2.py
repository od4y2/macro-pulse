"""Operational layer tests (unit S17): retry boundary, refresh plan,
run lifecycle, revision-diff persistence, scheduler, logging, CLI.

Provider calls are NEVER made here: connectors are fakes or
``httpx.MockTransport``; the live proof lives in evidence/S17. Live-DB
tests use the shared ``session`` fixture (skipped without PostgreSQL).
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta, timezone

import httpx
import pytest

from macropulse import catalog
from macropulse.catalog import CATALOG, validate_catalog
from macropulse.connectors.base import (
    ConnectorError,
    FetchedPoint,
    FetchedSeries,
    RetryableFetchError,
)
from macropulse.connectors.fred import FredConnector
from macropulse.connectors.ilostat import IlostatConnector
from macropulse.connectors.worldbank import WorldBankConnector
from macropulse.db.models import NormalizedObservation, RawObservation
from macropulse.ops.logging_setup import log_event, setup_logging
from macropulse.ops.refresh import (
    SeriesTarget,
    ensure_reference_data,
    plan_series,
    refresh_series,
    run_refresh,
)
from macropulse.ops.refresh import (
    main as cli_main,
)
from macropulse.ops.retry import (
    DEFAULT_RETRY_POLICY,
    RetryPolicy,
    fetch_with_retries,
    retryable,
)
from macropulse.ops.runs import (
    RUN_STATUSES,
    RUN_TRIGGERS,
    classify_run_status,
    finish_run,
    mark_interrupted_runs,
    start_run,
)
from macropulse.ops.scheduler import next_run_at, run_forever
from macropulse.scope import COUNTRIES

# --- Shared fakes ------------------------------------------------------------


def make_series(
    values: dict[int, float | None],
    retrieval_day: date,
    country_iso3: str = "USA",
    series_id: str = "NY.GDP.MKTP.KD.ZG",
) -> FetchedSeries:
    """A deterministic WB-shaped series: annual periods, vintage = retrieval."""
    points = tuple(
        FetchedPoint(
            period=date(year, 1, 1),
            value=value,
            missing_reason=None if value is not None else "wb_missing_value",
            vintage=retrieval_day,
        )
        for year, value in sorted(values.items())
    )
    return FetchedSeries(
        system="world_bank",
        series_id=series_id,
        country_iso3=country_iso3,
        evidence_label="real",
        retrieval_time=datetime(
            retrieval_day.year,
            retrieval_day.month,
            retrieval_day.day,
            12,
            0,
            tzinfo=UTC,
        ),
        points=points,
        raw_payload=json.dumps({"fixture": series_id}),
    )


class FakeConnector:
    live = True

    def __init__(self, series: FetchedSeries) -> None:
        self._series = series

    def fetch_indicator(self, code, country_iso3, start_year=None, end_year=None):
        return self._series


class SequenceConnector:
    """Returns successive fetch results (revision chains in tests)."""

    live = True

    def __init__(self, series_list: list[FetchedSeries]) -> None:
        self._series = list(series_list)
        self.calls = 0

    def fetch_indicator(self, code, country_iso3, start_year=None, end_year=None):
        series = self._series[min(self.calls, len(self._series) - 1)]
        self.calls += 1
        return series


class FailingConnector:
    live = True

    def __init__(self, error: Exception) -> None:
        self._error = error

    def fetch_indicator(self, code, country_iso3, start_year=None, end_year=None):
        raise self._error


def factory_returning(connector):
    return lambda system: connector


GDP_USA = SeriesTarget(
    indicator_id="gdp_real_growth",
    country_iso3="USA",
    system="world_bank",
    code="NY.GDP.MKTP.KD.ZG",
)


# --- Retry boundary ----------------------------------------------------------


def test_retry_backoff_sequence_and_success() -> None:
    sleeps: list[float] = []
    calls = {"n": 0}

    def fetch() -> FetchedSeries:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RetryableFetchError("X: HTTP 503 from World Bank")
        return make_series({2020: 1.0, 2021: 2.0}, date(2026, 9, 10))

    outcome = fetch_with_retries(fetch, DEFAULT_RETRY_POLICY, sleep=sleeps.append)
    assert outcome.attempts == 3
    assert len(outcome.retried_errors) == 2
    assert sleeps == [1.0, 2.0]  # base_delay, base_delay * backoff_factor


def test_retry_non_retryable_raises_immediately() -> None:
    sleeps: list[float] = []
    calls = {"n": 0}

    def fetch() -> FetchedSeries:
        calls["n"] += 1
        raise ConnectorError("X: HTTP 404 from World Bank")

    with pytest.raises(ConnectorError):
        fetch_with_retries(fetch, DEFAULT_RETRY_POLICY, sleep=sleeps.append)
    assert calls["n"] == 1
    assert sleeps == []


def test_retry_exhaustion_reraises_last_error() -> None:
    sleeps: list[float] = []
    calls = {"n": 0}

    def fetch() -> FetchedSeries:
        calls["n"] += 1
        raise RetryableFetchError(f"X: HTTP 503 attempt {calls['n']}")

    with pytest.raises(RetryableFetchError, match="attempt 3"):
        fetch_with_retries(fetch, DEFAULT_RETRY_POLICY, sleep=sleeps.append)
    assert calls["n"] == 3
    assert sleeps == [1.0, 2.0]


def test_transport_errors_are_retryable() -> None:
    assert retryable(httpx.ConnectError("connection refused"))
    assert retryable(httpx.ReadTimeout("read timed out"))
    assert not retryable(ConnectorError("parse failed"))
    assert not retryable(ValueError("unrelated"))


def test_on_retry_hook_receives_attempts_and_delay() -> None:
    seen: list[tuple[int, float]] = []
    calls = {"n": 0}

    def fetch() -> FetchedSeries:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RetryableFetchError("X: HTTP 429 from FRED")
        return make_series({2020: 1.0, 2021: 2.0}, date(2026, 9, 10))

    fetch_with_retries(
        fetch,
        DEFAULT_RETRY_POLICY,
        sleep=lambda _: None,
        on_retry=lambda a, d, e: seen.append((a, d)),
    )
    assert seen == [(1, 1.0)]


def test_retry_policy_must_allow_one_attempt() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        fetch_with_retries(
            lambda: make_series({2020: 1.0}, date(2026, 9, 10)),
            RetryPolicy(max_attempts=0),
        )


# --- Connector retryable classification --------------------------------------


def _transport_with(status: int) -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(status, text="{}"))


def test_worldbank_5xx_is_retryable() -> None:
    connector = WorldBankConnector(transport=_transport_with(503))
    with pytest.raises(RetryableFetchError, match="HTTP 503"):
        connector.fetch_indicator("NY.GDP.MKTP.KD.ZG", "USA")


def test_worldbank_4xx_is_permanent() -> None:
    connector = WorldBankConnector(transport=_transport_with(404))
    with pytest.raises(ConnectorError, match="HTTP 404") as excinfo:
        connector.fetch_indicator("NO.SUCH.CODE", "USA")
    assert not isinstance(excinfo.value, RetryableFetchError)


def test_fred_429_is_retryable() -> None:
    connector = FredConnector(api_key="test-key", transport=_transport_with(429))
    with pytest.raises(RetryableFetchError, match="HTTP 429"):
        connector.fetch_series("FEDFUNDS")


def test_ilostat_5xx_is_retryable() -> None:
    connector = IlostatConnector(transport=_transport_with(503))
    with pytest.raises(RetryableFetchError, match="HTTP 503"):
        connector.fetch_dataflow("DF_SDG_0852_SEX_AGE_RT", "USA")


# --- Catalog coverage field ---------------------------------------------------


def test_catalog_countries_field_valid_and_consistent() -> None:
    assert validate_catalog() == []
    panel = {c.iso3 for c in COUNTRIES}
    for ind in CATALOG:
        for ref in (ind.primary_source, ind.fallback_source):
            if ref is None or ref.countries is None:
                continue
            assert set(ref.countries) <= panel, (ind.indicator_id, ref.code)
    # The country-specific codes must be pinned, not left as None.
    policy_rate = next(i for i in CATALOG if i.indicator_id == "policy_rate")
    assert policy_rate.primary_source.countries == ("USA",)


def test_catalog_rejects_countries_outside_panel() -> None:
    original = catalog.CATALOG
    ind = original[0]
    try:
        bad = ind._replace(
            primary_source=ind.primary_source._replace(countries=("ZZZ",))
        )
        catalog.CATALOG = (bad,)
        problems = validate_catalog()
        assert any("outside the locked panel" in p for p in problems)
    finally:
        catalog.CATALOG = original


def test_catalog_rejects_duplicate_countries() -> None:
    original = catalog.CATALOG
    ind = original[0]
    try:
        bad = ind._replace(
            primary_source=ind.primary_source._replace(countries=("USA", "USA"))
        )
        catalog.CATALOG = (bad,)
        problems = validate_catalog()
        assert any("duplicate countries" in p for p in problems)
    finally:
        catalog.CATALOG = original


def test_catalog_rejects_empty_countries_tuple() -> None:
    original = catalog.CATALOG
    ind = original[0]
    try:
        bad = ind._replace(primary_source=ind.primary_source._replace(countries=()))
        catalog.CATALOG = (bad,)
        problems = validate_catalog()
        assert any("countries is empty" in p for p in problems)
    finally:
        catalog.CATALOG = original


# --- Refresh plan --------------------------------------------------------------


def test_plan_series_default_covers_primary_sources_with_coverage() -> None:
    targets = plan_series()
    # 11 panel-wide World Bank primaries x 10 economies + policy_rate USA.
    assert len(targets) == 11 * 10 + 1
    policy = [t for t in targets if t.indicator_id == "policy_rate"]
    assert [(t.country_iso3, t.system, t.code) for t in policy] == [
        ("USA", "fred", "FEDFUNDS")
    ]
    # No FRED target outside the US: a US-only code never plans for
    # another economy.
    assert not [t for t in targets if t.system == "fred" and t.country_iso3 != "USA"]
    # Every world_bank target carries the catalog primary code.
    gdp = next(i for i in CATALOG if i.indicator_id == "gdp_real_growth")
    assert (
        SeriesTarget("gdp_real_growth", "ZAF", "world_bank", gdp.primary_source.code)
        in targets
    )


def test_plan_series_filters_intersect() -> None:
    targets = plan_series(
        indicator_ids=["gdp_real_growth", "policy_rate"], country_iso3s=["ZAF", "USA"]
    )
    assert sorted((t.indicator_id, t.country_iso3) for t in targets) == [
        ("gdp_real_growth", "USA"),
        ("gdp_real_growth", "ZAF"),
        ("policy_rate", "USA"),  # policy_rate covers only the US
    ]


def test_plan_series_order_is_deterministic() -> None:
    assert plan_series() == plan_series()
    assert plan_series()[0] == plan_series(indicator_ids=["gdp_real_growth"])[0]


def test_plan_series_unknown_filters_yield_empty_plan() -> None:
    assert plan_series(indicator_ids=["nope"]) == []
    assert plan_series(country_iso3s=["ZZZ"]) == []


# --- Reference data (live DB) ---------------------------------------------------


def test_ensure_reference_data_seeds_panel_and_catalog(session) -> None:
    counts = ensure_reference_data(session)
    assert counts == {"countries_added": 10, "indicators_added": len(CATALOG)}
    from macropulse.db.models import Country, Indicator

    for country in COUNTRIES:
        assert session.get(Country, country.iso3) is not None
    for ind in CATALOG:
        assert session.get(Indicator, ind.indicator_id) is not None


def test_ensure_reference_data_is_idempotent(session) -> None:
    ensure_reference_data(session)
    assert ensure_reference_data(session) == {
        "countries_added": 0,
        "indicators_added": 0,
    }


# --- refresh_series (live DB) ----------------------------------------------------


def test_refresh_series_persists_raw_and_normalized(session) -> None:
    ensure_reference_data(session)
    series = make_series({2015: 2.5, 2016: 3.0, 2017: None}, date(2026, 9, 10))
    outcome = refresh_series(session, GDP_USA, factory_returning(FakeConnector(series)))

    assert outcome["status"] == "ok"
    assert outcome["new_periods"] == 3
    assert outcome["revised_periods"] == 0
    assert outcome["unchanged_periods"] == 0
    assert outcome["attempts"] == 1

    rows = (
        session.query(NormalizedObservation)
        .order_by(NormalizedObservation.period)
        .all()
    )
    assert [r.period.isoformat() for r in rows] == [
        "2015-01-01",
        "2016-01-01",
        "2017-01-01",
    ]
    assert [float(r.value) if r.value is not None else None for r in rows] == [
        2.5,
        3.0,
        None,
    ]
    assert rows[2].missing_reason == "wb_missing_value"
    assert all(r.evidence_label == "real" for r in rows)
    assert all(r.quality_grade == "ungraded" for r in rows)
    assert all(r.vintage == date(2026, 9, 10) for r in rows)
    assert all(
        r.retrieval_time == datetime(2026, 9, 10, 0, 0, tzinfo=UTC) for r in rows
    )


def test_refresh_series_same_day_refetch_is_idempotent(session) -> None:
    ensure_reference_data(session)
    series = make_series({2015: 2.5, 2016: 3.0}, date(2026, 9, 10))
    refresh_series(session, GDP_USA, factory_returning(FakeConnector(series)))

    outcome = refresh_series(session, GDP_USA, factory_returning(FakeConnector(series)))
    assert outcome["status"] == "ok"
    assert outcome["new_periods"] == 0
    assert outcome["revised_periods"] == 0
    assert outcome["unchanged_periods"] == 2
    assert session.query(NormalizedObservation).count() == 2


def test_refresh_series_persists_only_revisions_and_new_periods(session) -> None:
    ensure_reference_data(session)
    first = make_series({2015: 2.0, 2016: 2.5, 2017: 3.0}, date(2026, 9, 10))
    second = make_series(
        {2015: 2.0, 2016: 2.9, 2017: 3.0, 2018: 3.1}, date(2026, 9, 11)
    )
    connector = SequenceConnector([first, second])
    refresh_series(session, GDP_USA, factory_returning(connector))

    outcome = refresh_series(session, GDP_USA, factory_returning(connector))
    assert outcome["new_periods"] == 1
    assert outcome["revised_periods"] == 1
    assert outcome["unchanged_periods"] == 2

    rows = session.query(NormalizedObservation).all()
    assert len(rows) == 5  # 3 first pass + revision + new period
    revised = [r for r in rows if r.period == date(2016, 1, 1)]
    assert sorted(float(r.value) for r in revised) == [2.5, 2.9]
    assert {r.vintage for r in revised} == {date(2026, 9, 10), date(2026, 9, 11)}
    newest = [r for r in rows if r.period == date(2018, 1, 1)]
    assert [float(r.value) for r in newest] == [3.1]
    assert newest[0].vintage == date(2026, 9, 11)


def test_refresh_series_value_to_missing_is_a_revision(session) -> None:
    ensure_reference_data(session)
    first = make_series({2015: 2.0, 2016: 2.5}, date(2026, 9, 10))
    second = make_series({2015: 2.0, 2016: None}, date(2026, 9, 11))
    connector = SequenceConnector([first, second])
    refresh_series(session, GDP_USA, factory_returning(connector))

    outcome = refresh_series(session, GDP_USA, factory_returning(connector))
    assert outcome["revised_periods"] == 1
    missing_rows = [
        r for r in session.query(NormalizedObservation).all() if r.value is None
    ]
    assert len(missing_rows) == 1
    assert missing_rows[0].missing_reason == "wb_missing_value"


def test_refresh_series_no_api_key_fails_honestly(session, monkeypatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    from macropulse.ops.refresh import default_connector_factory

    target = SeriesTarget(
        indicator_id="policy_rate", country_iso3="USA", system="fred", code="FEDFUNDS"
    )
    outcome = refresh_series(session, target, default_connector_factory)
    assert outcome["status"] == "failed"
    assert outcome["reason"] == "no_api_key"
    assert outcome["attempts"] == 0
    assert session.query(NormalizedObservation).count() == 0


def test_refresh_series_retryable_failure_exhausts_and_records(session) -> None:
    ensure_reference_data(session)
    sleeps: list[float] = []
    failing = FailingConnector(RetryableFetchError("X: HTTP 503 from World Bank"))
    outcome = refresh_series(
        session, GDP_USA, factory_returning(failing), sleep=sleeps.append
    )
    assert outcome["status"] == "failed"
    assert outcome["reason"] == "fetch_failed"
    assert outcome["attempts"] == DEFAULT_RETRY_POLICY.max_attempts
    assert "503" in outcome["detail"]
    assert sleeps == [1.0, 2.0]
    assert session.query(NormalizedObservation).count() == 0


def test_refresh_series_permanent_failure_fails_fast(session) -> None:
    ensure_reference_data(session)
    sleeps: list[float] = []
    failing = FailingConnector(ConnectorError("X: HTTP 404 from World Bank"))
    outcome = refresh_series(
        session, GDP_USA, factory_returning(failing), sleep=sleeps.append
    )
    assert outcome["status"] == "failed"
    assert outcome["reason"] == "fetch_failed"
    assert outcome["attempts"] == 1
    assert sleeps == []


def test_refresh_series_normalization_error_recorded(session) -> None:
    ensure_reference_data(session)
    # Duplicate (period, vintage) violates the S06 rule: the series is
    # archived raw, but the governed store is protected.
    duplicate = FetchedSeries(
        system="world_bank",
        series_id="NY.GDP.MKTP.KD.ZG",
        country_iso3="USA",
        evidence_label="real",
        retrieval_time=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        points=(
            FetchedPoint(date(2015, 1, 1), 1.0, None, date(2026, 9, 10)),
            FetchedPoint(date(2015, 1, 1), 2.0, None, date(2026, 9, 10)),
            FetchedPoint(date(2016, 1, 1), 3.0, None, date(2026, 9, 10)),
        ),
        raw_payload="{}",
    )
    outcome = refresh_series(
        session, GDP_USA, factory_returning(FakeConnector(duplicate))
    )
    assert outcome["status"] == "failed"
    assert outcome["reason"] == "normalization_error"
    assert "duplicate" in outcome["detail"]
    assert session.query(NormalizedObservation).count() == 0
    # The raw archive keeps the retrieval (the fetch DID happen).
    assert session.query(RawObservation).count() == 3


# --- run_refresh (live DB) --------------------------------------------------------


def test_run_refresh_persists_audit_row_and_data(session) -> None:
    targets = [GDP_USA]
    series = make_series({2015: 2.5, 2016: 3.0}, date(2026, 9, 10))
    run = run_refresh(session, targets, factory_returning(FakeConnector(series)))

    assert run.status == "succeeded"
    assert run.series_total == 1
    assert run.series_failed == 0
    assert run.finished_at is not None
    assert run.trigger == "manual"
    assert [o["status"] for o in run.outcomes] == ["ok"]
    assert session.query(NormalizedObservation).count() == 2


def test_run_refresh_partial_failure_isolates_series(session, monkeypatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    from macropulse.ops.refresh import default_connector_factory

    class SplitFactory:
        def __call__(self, system: str):
            if system == "fred":
                return default_connector_factory(system)  # no key -> no_api_key
            return FakeConnector(make_series({2015: 2.5, 2016: 3.0}, date(2026, 9, 10)))

    targets = [
        GDP_USA,
        SeriesTarget(
            indicator_id="policy_rate",
            country_iso3="USA",
            system="fred",
            code="FEDFUNDS",
        ),
    ]
    run = run_refresh(session, targets, SplitFactory())

    assert run.status == "partial"
    assert run.series_total == 2
    assert run.series_failed == 1
    assert run.error == "1 of 2 series failed"
    reasons = {o["indicator_id"]: o["reason"] for o in run.outcomes}
    assert reasons == {"gdp_real_growth": None, "policy_rate": "no_api_key"}
    # The healthy series was stored despite its sibling failing.
    assert session.query(NormalizedObservation).count() == 2


def test_run_refresh_all_failed(session) -> None:
    failing = FailingConnector(RetryableFetchError("X: HTTP 503 from World Bank"))
    run = run_refresh(
        session, [GDP_USA], factory_returning(failing), sleep=lambda _: None
    )
    assert run.status == "failed"
    assert run.error == "all 1 series failed"


def test_run_refresh_empty_plan_fails_with_reason(session) -> None:
    run = run_refresh(session, [], factory_returning(FakeConnector(None)))
    assert run.status == "failed"
    assert run.error == "no series planned (empty plan or all filtered out)"


def test_run_refresh_marks_stale_running_interrupted(session) -> None:
    stale = start_run(session, "scheduled")
    run = run_refresh(
        session,
        [GDP_USA],
        factory_returning(
            FakeConnector(make_series({2015: 2.5, 2016: 3.0}, date(2026, 9, 10)))
        ),
    )
    session.refresh(stale)
    assert stale.status == "interrupted"
    assert "marked interrupted" in stale.error
    assert run.status == "succeeded"
    assert run.id != stale.id


def test_start_run_rejects_unknown_trigger(session) -> None:
    with pytest.raises(ValueError, match="unknown trigger"):
        start_run(session, "cron")


def test_mark_interrupted_runs_only_touches_running(session) -> None:
    finished = start_run(session, "manual")
    finish_run(session, finished, "succeeded", [])
    stale = start_run(session, "scheduled")
    interrupted = mark_interrupted_runs(session)
    assert interrupted == [stale.id]
    session.refresh(finished)
    assert finished.status == "succeeded"


def test_run_vocabularies_are_closed() -> None:
    assert RUN_TRIGGERS == ("manual", "scheduled", "recovery")
    assert RUN_STATUSES == (
        "running",
        "succeeded",
        "partial",
        "failed",
        "interrupted",
    )
    assert classify_run_status([]) == (
        "failed",
        "no series planned (empty plan or all filtered out)",
    )
    assert classify_run_status([{"status": "ok"}]) == ("succeeded", None)
    assert classify_run_status([{"status": "ok"}, {"status": "failed"}]) == (
        "partial",
        "1 of 2 series failed",
    )
    assert classify_run_status([{"status": "failed"}]) == (
        "failed",
        "all 1 series failed",
    )


# --- Scheduler ---------------------------------------------------------------------


def test_next_run_at_before_the_slot() -> None:
    now = datetime(2026, 9, 10, 5, 59, tzinfo=UTC)
    assert next_run_at(now) == datetime(2026, 9, 10, 6, 0, tzinfo=UTC)


def test_next_run_at_after_the_slot_is_tomorrow() -> None:
    now = datetime(2026, 9, 10, 6, 0, 1, tzinfo=UTC)
    assert next_run_at(now) == datetime(2026, 9, 11, 6, 0, tzinfo=UTC)


def test_next_run_at_exact_slot_is_strictly_after() -> None:
    now = datetime(2026, 9, 10, 6, 0, 0, tzinfo=UTC)
    assert next_run_at(now) == datetime(2026, 9, 11, 6, 0, tzinfo=UTC)


def test_next_run_at_converts_to_utc() -> None:
    # 15:00 at UTC+8 == 07:00 UTC, i.e. after the day's 06:00 slot.
    now = datetime(2026, 9, 10, 15, 0, tzinfo=timezone(timedelta(hours=8)))
    assert now.utcoffset() == timedelta(hours=8)
    assert next_run_at(now) == datetime(2026, 9, 11, 6, 0, tzinfo=UTC)


def test_run_forever_runs_job_then_sleeps_until_slot() -> None:
    jobs: list[int] = []
    sleeps: list[float] = []
    now = datetime(2026, 9, 10, 14, 0, tzinfo=UTC)

    def job() -> None:
        jobs.append(len(jobs))

    iterations = run_forever(
        job,
        now_fn=lambda: now,
        sleep_fn=sleeps.append,
        stop_after=2,
    )
    assert iterations == 2
    assert len(jobs) == 2
    # After the first job: sleep until tomorrow 06:00 UTC = 16 hours.
    assert sleeps == [16 * 3600.0]


# --- Logging -------------------------------------------------------------------------


def test_jsonl_logging_roundtrip(tmp_path) -> None:
    log_file = tmp_path / "refresh.jsonl"
    logger = setup_logging(log_file)
    log_event(logger, "info", "run_started", run_id=7, trigger="manual")
    log_event(logger, "warning", "series_retry", attempt=1, delay_seconds=1.0)

    lines = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert [entry["event"] for entry in lines] == ["run_started", "series_retry"]
    assert lines[0]["run_id"] == 7
    assert lines[0]["trigger"] == "manual"
    assert lines[1]["level"] == "warning"
    for entry in lines:
        assert set(entry) >= {"ts", "level", "event"}
        datetime.fromisoformat(entry["ts"])  # parses as ISO-8601


def test_log_event_serializes_non_json_fields_via_str(tmp_path) -> None:
    log_file = tmp_path / "refresh.jsonl"
    logger = setup_logging(log_file)
    log_event(logger, "info", "series_finished", error=RuntimeError("boom"))
    entry = json.loads(log_file.read_text().splitlines()[0])
    assert "boom" in entry["error"]


# --- CLI -------------------------------------------------------------------------------


def test_cli_dry_run_prints_plan_without_db(capsys) -> None:
    code = cli_main(["--dry-run", "--indicator", "policy_rate"])
    out = capsys.readouterr().out
    assert code == 0
    assert "1 series planned" in out
    assert "policy_rate USA fred FEDFUNDS" in out


def test_cli_dry_run_empty_plan(capsys) -> None:
    code = cli_main(["--dry-run", "--indicator", "nope"])
    out = capsys.readouterr().out
    assert code == 0
    assert "0 series planned" in out


def test_cli_parser_accepts_repeated_filters() -> None:
    from macropulse.ops.refresh import build_parser

    args = build_parser().parse_args(
        [
            "--indicator",
            "a",
            "--indicator",
            "b",
            "--country",
            "USA",
            "--trigger",
            "recovery",
        ]
    )
    assert args.indicator == ["a", "b"]
    assert args.country == ["USA"]
    assert args.trigger == "recovery"
    assert args.dry_run is False
    assert args.daemon is False
