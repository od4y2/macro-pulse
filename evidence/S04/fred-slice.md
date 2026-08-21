# S04 Evidence - FRED Connector Vertical Slice (2026-08-19)

## Prior-state check
- S03 accepted 2026-08-19; ledger consistent; S04 sole active unit.
- Git checkpoint at unit start: `0b2ce8c` (rollback point). Working tree clean.
- Baseline: 52 tests passed; smoke via `PYTHONPATH=src` passed; DB container healthy.

## Objective result
One traceable connector path: FRED `series/observations` -> parsed points
with provenance -> `raw_observations` rows.

- `src/macropulse/connectors/fred.py`: `FredConnector` with two modes sharing
  one parser - live (key present, label `real`) and deterministic no-key
  (canned FRED-shaped fixture, label `mocked`). FRED's `"."` values become
  explicit missingness (`fred_missing_value`), never dropped. `vintage` is
  taken from each observation's `realtime_start`.
- `src/macropulse/connectors/persist.py`: `persist_raw_series()` writes the
  immutable raw payload (including evidence label and full provider response)
  into `raw_observations`; refuses unregistered countries/indicators rather
  than silently inventing reference data.
- `tests/test_fred_connector.py`: 18 tests. Live-mode behavior is exercised
  via `httpx.MockTransport` - no network, no key, fully deterministic.
- Refactor: DB test fixture moved to `tests/conftest.py` (shared, self-skipping
  when Postgres is unreachable); `tests/test_db_integration.py` now uses it.
  No behavior change to S03 tests.

## Provenance honesty record
- **No live FRED call was made**: `.env.local` contains only the placeholder
  key. All runs in this unit are mocked/no-key. The S02 catalog's FRED codes
  (`UNRATE`, `CPIAUCSL`, `FEDFUNDS`, `CLVMNACSCAB1GQ`) therefore remain
  unverified against the live API until a real key is configured.
- FRED's plain observations endpoint does not expose first-release
  timestamps; `release_time` is recorded as equal to `retrieval_time` with
  this limitation documented in the module docstring. True vintage history
  requires ALFRED realtime queries (planned S07).
- The no-key fixture uses obviously-round placeholder values labelled
  `mocked`; they are never presented as observed data.

## Commands and actual results
- `python -m pytest -q` -> 70 passed (52 prior + 18 new; includes 3 live-DB
  persistence tests on the `macropulse_test` database).
- `ruff check` on changed files -> All checks passed.
- `PYTHONPATH=src python -m macropulse.smoke` -> passed.

## Changed files
- New: `src/macropulse/connectors/{__init__,fred,persist}.py`,
  `tests/test_fred_connector.py`, `tests/conftest.py`, `evidence/S04/`.
- Updated: `tests/test_db_integration.py` (fixture extraction only),
  `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`, `docs/decisions.md`,
  `docs/CoBuildLog.md`.

## Limitations
- Live FRED path is implemented and mock-tested but not yet exercised
  against the real API (no key). First live run should re-verify catalog
  codes and record results.
- No pagination handling (FRED default limit 1000 observations per request);
  acceptable for the slice, must be revisited when fetching long histories.
- Normalization (S06) intentionally not implemented; connectors stop at raw.

## Rollback checkpoint
- Pre-unit: `0b2ce8c`.
