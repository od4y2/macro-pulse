# S17 Design Notes — Scheduling, Logging, and Operational Recovery

Unit objective: "Add scheduled updates, logs, retry boundaries, and safe
failure behavior." Implementation date: 2026-09-10. All live calls below
were made against providers on that date; outputs are in
`live-demo-output.txt`, the full acceptance run in `acceptance-run.txt`.

## What was built

- `src/macropulse/ops/` — the operational layer:
  - `retry.py`: `RetryPolicy` (max_attempts=3, base_delay=1.0s,
    backoff_factor=2.0 → sleeps 1s then 2s; bounded ~3s worst-case added
    latency per failing series) and `fetch_with_retries`. Retryable:
    `RetryableFetchError` (HTTP 429/500/502/503/504, now raised by all
    three connectors via `http_error()` in `connectors/base.py`) and
    `httpx.TransportError`. 4xx and parse errors fail on attempt 1.
    Exhaustion re-raises the LAST error. `sleep` is injectable so tests
    assert delays without sleeping.
  - `runs.py`: the run-record contract. Closed vocabularies — triggers
    `manual|scheduled|recovery`; run statuses
    `running|succeeded|partial|failed|interrupted`; series statuses
    `ok|failed`; failure reasons
    `no_api_key|fetch_failed|normalization_error|persist_error|unknown`.
  - `logging_setup.py`: JSONL structured logs (ts/level/event + fields,
    `default=str`) to stderr + an appending file; re-configure safe.
  - `refresh.py`: the orchestrator + CLI (one cycle, `--daemon`,
    `--dry-run`; exit 0/1/2 = succeeded/partial/failed).
  - `scheduler.py`: stdlib daily loop, 06:00 UTC convention.
- `db/models.py`: 12th table `refresh_runs` (migration
  `c9af6b543047`) — the durable audit: trigger, status, series totals,
  per-series outcomes JSON, error note. Append-only; stale `running`
  rows are flipped to `interrupted` by the next run.
- `catalog.py`: `SourceRef.countries` — structured per-source country
  coverage (None = whole panel). `policy_rate`'s FRED FEDFUNDS is
  `("USA",)`; country-specific fallbacks are tagged too. This is what
  keeps the planner from fetching a US series as another economy.

## Design decisions

1. **Revision-diff persistence.** A normalized row is born only when a
   period is first observed or its (value, missing_reason) changed vs
   the latest stored vintage. Unchanged re-observations are archived in
   the RAW store only. Consequences: re-runs are idempotent (proved
   live: run C wrote 0 new rows over 10 series × 66 periods), the
   normalized store stays a readable revision chain (RQ4) instead of a
   daily no-op log, and DB growth is bounded.
2. **Stdlib scheduler, no APScheduler** (large-wheel installs have
   failed in this environment before; platform cron alone leaves
   nothing testable in-repo). `next_run_at`/`run_forever` take injected
   clock/sleep functions; 06:00 UTC is a polling convention and is
   explicitly NOT a release-schedule claim (the release calendar stays
   unpopulated by the S07 decision).
3. **`cached` stays reserved.** The refresh layer writes live `real`
   rows or records a failure; it never re-labels existing data.
4. **No silent mocks.** FRED without `FRED_API_KEY` fails with reason
   `no_api_key` BEFORE any DB write. The S04 no-key fixture is a
   test/dev convenience; a scheduled job filling the governed store
   with fixture data would be "mocked presented as observed", which the
   contract forbids. Proved live in run A/C.
5. **Plan = PRIMARY sources only.** Fallback application stays a human
   decision (the account_ownership "fallback" is a different measure —
   the female variant — not a country alternative). Default plan:
   11 World Bank panel-wide indicators × 10 economies + policy_rate USA
   = 111 series.
6. **Per-series isolation.** Raw archive commits FIRST (the fetch did
   happen), then normalized rows; one failing series never aborts the
   others, and progress commits per series so a crash leaves an
   inspectable trail. Recovery = re-run with the same command; the
   `trigger=recovery` value distinguishes it in the audit.
7. **Raw = complete retrieval archive, normalized = governed chain.**
   Every successful fetch lands in raw_observations even when the
   normalized diff is empty (that's what makes "unchanged" auditable).

## Verification

- `tests/test_ops.py`: 46 tests — retry backoff/exhaustion/fail-fast,
  connector 5xx/429 classification (httpx.MockTransport), catalog
  coverage validation, plan (111 default, USA-only policy_rate,
  determinism), reference seeding idempotency, per-series outcomes with
  full provenance, same-day idempotency, revision + value→missing
  diffs, no_api_key, partial-failure isolation, stale-running→
  interrupted, empty plan, closed vocabularies, scheduler boundaries
  incl. UTC conversion, JSONL roundtrip, CLI dry-run.
- Full suite: 497 passed (451 baseline + 46 new). Smoke: query service
  OK. Ruff: clean. S13 pin `api/schemas.py`: 0 diff lines vs `63d867f`.
- Live demo (disposable DB `macropulse_s17_demo`, created/migrated/
  dropped by the script; dev DB untouched): run A partial (10 WB series
  ok @66 points, FRED no_api_key, exit 1) → run B recovery with key
  (FEDFUNDS live, 866 monthly points 1954-07…2026-08, exit 0) → run C
  idempotent (all new_periods=0, exit 1 — key still absent). All 1,526
  stored rows labelled `real`. Three audit rows with correct
  triggers/statuses.

## Not done / deferred (honest boundaries)

- No cron entry is installed anywhere; the daemon and the cron-able
  one-shot both exist and are documented (docs/OpsRunbook.md).
- No alerting/monitoring beyond the run row + log stream (out of unit
  scope; the run row IS the machine-readable signal).
- The scheduler is single-host, in-process; not distributed-safe (one
  daemon only, by runbook instruction).
