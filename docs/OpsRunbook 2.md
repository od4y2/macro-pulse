# Operations Runbook (S17, 2026-09-10)

The scheduled-refresh layer is `src/macropulse/ops/`. Everything here is in
code and tests (`tests/test_ops.py`, 46 tests); this page is the operator's
map, not a second source of truth.

## Run modes

All commands from the repo root need `PYTHONPATH=src` (`.venv` hidden-flag
defect, E01).

| Mode | Command | What it does |
|---|---|---|
| One cycle | `PYTHONPATH=src python -m macropulse.ops.refresh [--indicator ID ...] [--country ISO3 ...] [--trigger manual\|scheduled\|recovery]` | Plan → fetch with retries → raw archive → normalize → revision-diff persist → one `refresh_runs` row |
| Cron-able one-shot | same, via cron/systemd (no state between runs) | One cycle; cron owns the schedule |
| Daemon | `PYTHONPATH=src python -m macropulse.ops.refresh --daemon` | Stdlib scheduler loop: one cycle at startup, then daily at 06:00 UTC |
| Dry run | `--dry-run` | Prints the planned series; touches no data, writes no run row |

Exit codes: `0` succeeded, `1` partial (some series failed), `2` failed
(all series failed, or the plan was empty). Cron/systemd should alert on
non-zero; a partial run is still a run that mostly worked — read
`refresh_runs.error` and the per-series outcomes before retrying.

Example cron entry (daily 06:10 UTC, key sourced from a root-only file;
log captured by cron to the same JSONL file the CLI writes):

```cron
10 6 * * * cd /path/to/macro-pulse && FRED_API_KEY=$(grep '^FRED_API_KEY=' /path/to/.env.local | cut -d= -f2) PYTHONPATH=src .venv/bin/python -m macropulse.ops.refresh --trigger scheduled >> logs/refresh.jsonl 2>&1
```

Do NOT run the daemon and the cron entry together — one scheduler per
database (the layer is single-host, in-process; nothing arbitrates two
concurrent refreshes beyond the audit rows they both write).

**Schedule disclaimer**: 06:00 UTC is a POLLING convention — a time we
chose to check providers — not a claim about when providers release
data. The release calendar is unpopulated by S07 decision, so no expected
release times exist to schedule against.

## What one cycle does

1. Marks any stale `running` run rows as `interrupted` (the process died
   mid-run; the audit trail never says "running" forever).
2. Seeds reference data if missing (locked S01 countries + S02 catalog
   indicators; insert-only, never updates).
3. Plans series: every catalog indicator's PRIMARY source × the
   countries that source covers (`SourceRef.countries`; `None` = whole
   panel). Default plan = 111 series (11 World Bank panel-wide indicators
   × 10 economies + policy_rate USA). Fallback sources are NOT fetched
   automatically — fallback application is a human decision (and the
   account_ownership "fallback" is a different measure, the female
   variant, not a country alternative).
4. Per series: retry-bounded fetch → raw archive commit (the fetch DID
   happen) → normalize under S06 rules → revision-diff persist → commit.
   One failing series never aborts the others; progress commits per
   series.

**Revision-diff persistence**: a normalized row is born only when a
period is first observed or its (value, missing_reason) changed versus
the latest stored vintage. Unchanged re-observations land in the RAW
store only — raw is the complete retrieval archive, normalized is the
revision chain. Consequences: re-runs are idempotent (live-proved: an
immediate re-run wrote 0 new rows over 10 series × 66 periods), and
RQ4 revision chains stay readable (every normalized row is a change,
not a daily no-op).

**No silent mocks**: FRED series without `FRED_API_KEY` fail with reason
`no_api_key` BEFORE any DB write. The S04 no-key fixture mode is a
test/dev convenience; the scheduled layer never fills the governed
store with fixture data. Recovery = fix the cause (e.g. source the key)
and re-run; `--trigger recovery` records why the re-run happened.

## Failure vocabulary (closed)

Run statuses: `running | succeeded | partial | failed | interrupted`.
Series statuses: `ok | failed`. Failure reasons:
`no_api_key | fetch_failed | normalization_error | persist_error | unknown`.

- `fetch_failed` — connector error or transport error; 4xx/parse errors
  fail on attempt 1, retryable errors only after retries are exhausted.
- `normalization_error` — the series violated S06 rules (e.g. duplicate
  (period, vintage)); raw archive is still committed (provenance).
- `persist_error` — database write failed; the series is rolled back.
- `unknown` — anything unexpected; detail carries the original message.

## Retry policy

`RetryPolicy(max_attempts=3, base_delay=1.0s, backoff_factor=2.0)` — on
a retryable failure (HTTP 429/500/502/503/504 or a transport error) the
layer sleeps 1s, retries, sleeps 2s, retries, then lets the last error
escape as `fetch_failed`. Worst-case added latency ≈ 3s per failing
series, bounded. Constants are class attributes on `RetryPolicy` — the
policy is injectable everywhere so tests assert delays without
sleeping. 4xx and parse errors are permanent: no retry, attempt 1.

## Logs

JSONL, one object per line: `ts` (UTC ISO-8601), `level`, `event`, plus
event fields (`default=str` so an unserializable field degrades, never
crashes the run). Default file `logs/refresh.jsonl` under the CWD
(gitignored); override with `--log-file`. A human-readable stream also
goes to stderr (cron capture). Events: `run_started`,
`run_interrupted_marked`, `run_finished`, `series_started`,
`series_finished` (carries the full per-series outcome),
`series_retry`, `daemon_started`, `daemon_sleep`, `dry_run_plan`.

The log answers "what happened, in order"; the run row answers "what is
the final state". They are written by the same events — no divergence
between what the log says and what the DB records.

## The run record (`refresh_runs`, migration `c9af6b543047`)

One row per cycle: `trigger`, `status`, `series_total`, `series_failed`,
`outcomes` (JSON list — one record per series with counts and, for
failures, the closed reason + detail), `error` (run-level note),
`started_at`/`finished_at`. Append-only lifecycle: inserted `running`,
updated until finished; a `running` row at run time means the process
died and the next run marks it `interrupted`. Query it directly:

```sql
SELECT id, trigger, status, series_total, series_failed, error
FROM refresh_runs ORDER BY id DESC LIMIT 10;
```

## Secrets

`FRED_API_KEY` is read from the environment (or `.env.local` via the
cron/grep pattern above). It is never logged, never written to evidence
outputs, and `.env.local` is gitignored. A run without the key is a
recorded `no_api_key` failure — never mocked data.

## What is NOT here (honest boundaries)

- No alerting/monitoring beyond the run row + log stream; the run row is
  the machine-readable signal for any future watchdog.
- No cron entry is pre-installed anywhere — the one-shot and the daemon
  exist and are documented here; wiring one up is a deployment decision.
- The scheduler is single-host and in-process, not distributed-safe.
- `cached` evidence label remains RESERVED/unemitted: the refresh layer
  stores live `real` rows or records failure; it never re-labels
  existing data.
