# S05 Follow-up Evidence - Live FRED Verification (2026-08-19)

## Context
Student provided a real FRED API key after S05 acceptance; it was written
into the gitignored `.env.local` (verified untracked by git). This addendum
completes the source audit for the FRED codes.

## Findings
- `UNRATE` -> OK: 943 points, 942 non-null (latest 2026-07 = 4.1), label `real`.
- `CPIAUCSL` -> OK: 955 points, 954 non-null (latest 2026-07 = 332.813).
- `FEDFUNDS` -> OK: 865 points, 865 non-null (latest 2026-07 = 3.63).
- `CLVMNACSCAB1GQ` -> **FAIL: HTTP 400 (invalid series id)**. The S02 catalog
  guess was wrong. FRED series search ("Real GDP Germany") found the correct
  code: `CLVMNACSCAB1GQDE` (Real GDP for Germany, quarterly, SA) ->
  OK: 142 points, 142 non-null (latest 2026-Q2).

## Changes applied
- `src/macropulse/catalog.py`: fallback code corrected to `CLVMNACSCAB1GQDE`,
  verified `confirmed`. **The catalog now has zero unverified codes.**
- `scripts/audit_sources.py`: now probes FRED codes too (skips them with a
  SKIP line when `FRED_API_KEY` is absent; loads the gitignored `.env.local`
  itself so the key never appears in commands or output).
- `tests/test_catalog.py`: the "some codes are unverified" honesty assertion
  updated - the honest state is now "zero unverified", and the test pins the
  report to the actual count.
- `docs/IndicatorCatalog.md`: verification section rewritten with the live
  audit results and the corrections trail.

## Commands and actual results
- `PYTHONPATH=src python scripts/audit_sources.py` (with .env.local key) ->
  **18/18 OK, 0 failures**, fred live mode: True. Full output saved to
  `evidence/S05/live-source-audit.txt`.
- `python -m pytest -q` -> 94 passed.
- `ruff check` -> clean. Smoke -> passed.

## Notes
- The key exists only in `.env.local` (gitignored) and in this evidence file
  only as the fact of its presence - the key value is never written to any
  tracked file.
- `FredConnector` live mode is now exercised end-to-end with real data
  (previously mock-tested only, per the S04 evidence limitation).
