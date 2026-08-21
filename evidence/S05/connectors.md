# S05 Evidence - World Bank and ILOSTAT Connectors (2026-08-19)

## Prior-state check
- S04 accepted 2026-08-19; ledger consistent; S05 sole active unit.
- Git checkpoint at unit start: `b98b4c1` (rollback point). Working tree clean.
- Baseline: 70 tests passed; smoke passed; DB container healthy.

## Objective result
- `src/macropulse/connectors/worldbank.py`: `WorldBankConnector` - live, no
  key, JSON API v2; null values -> explicit `wb_missing_value` missingness;
  annual periods as year-start dates; full payload preserved.
- `src/macropulse/connectors/ilostat.py`: `IlostatConnector` - SDMX 3.0 REST,
  CSV format (rich metadata: REF_AREA, SEX, FREQ, OBS_STATUS, SOURCE,
  UNIT_MEASURE preserved verbatim in payload); filters to one country and
  `SEX_T`; annual rows selected by the FREQ dimension (mixed-frequency
  dataflows like DF_EIP_NEET_SEX_RT carry quarterly rows).
- Shared connector types extracted to `connectors/base.py`; `persist_raw_series`
  generalized to any source system (was FRED-only).
- `scripts/audit_sources.py`: reproducible live audit of every world_bank and
  ilostat catalog code. **Result: 14/14 OK, 0 failures** (full output in
  `evidence/S05/live-source-audit.txt`). This is the project's first live
  external data retrieval; all such data carries the `real` label.

## Live source audit findings (catalog corrections applied)
All previously-unverified WB codes verified live, plus two corrections:
- `SL.UEM.NEET.ZS` (NEET) - confirmed.
- `FX.OWN.TOTL.ZS`, `FX.OWN.TOTL.FE.ZS` (Findex account ownership, female
  variant) - confirmed. Survey years only: e.g. USA has 2 non-null values in
  the last 6 years, IND digital payments 4 non-null of 66 rows. The WB API
  returns null rows for non-survey years - handled as explicit missingness.
- TBD digital-payments code resolved: `g20.any` = "Made or received a digital
  payment (% age 15+)" (Global Findex, source 28) - confirmed with data
  (IND: 2014 22.2, 2017 28.7, 2021 34.9, 2024 48.5).
- S02's ILOSTAT guess `SDG_0811_SEX_AGE_RT` was **wrong** (SDG 8.1.1 is GDP
  growth). Correct codes found via the live dataflow registry:
  `DF_SDG_0852_SEX_AGE_RT` (unemployment by sex and age, SDG 8.5.2) and
  `DF_EIP_NEET_SEX_RT` (NEET rate) - both confirmed with data. The S02
  unverified-flag discipline caught this before production use.
- Remaining unverified (1): FRED `CLVMNACSCAB1GQ` - needs a FRED API key.

## Live-run bug fixes (found by the audit, missed by mocked tests)
- WB open-ended date ranges (`date=2020:`) are rejected by the API - removed
  the param; filtering is client-side.
- ILOSTAT full-dataflow CSVs need a long read timeout (180s set; the first
  run timed out at the httpx default).
- ISO3 validation accepted lowercase codes - now requires uppercase.

## Commands and actual results
- `python -m pytest -q` -> 94 passed (70 prior + 24 new WB/ILOSTAT tests,
  including 1 live-DB persistence test; all network paths via MockTransport).
- `PYTHONPATH=src python scripts/audit_sources.py` -> 14 OK / 0 FAIL
  (live, network), saved to `evidence/S05/live-source-audit.txt`.
- `ruff check` on changed files -> clean.
- `PYTHONPATH=src python -m macropulse.smoke` -> passed.

## Changed files
- New: `src/macropulse/connectors/{base,worldbank,ilostat}.py`,
  `tests/test_worldbank_connector.py`, `tests/test_ilostat_connector.py`,
  `scripts/audit_sources.py`, `evidence/S05/`.
- Updated: `src/macropulse/connectors/{__init__,fred,persist}.py` (shared
  types, source-generic persistence), `src/macropulse/catalog.py`
  (live-verified codes), state files.

## Limitations
- ILOSTAT fetch downloads the full dataflow (all countries) then filters
  client-side; SDMX key filtering (ref_area in the key) would cut transfer
  size and is a follow-up optimization.
- WB/ILOSTAT snapshots carry no per-observation release timestamps;
  `release_time` = `retrieval_time` and `vintage` = retrieval date
  (documented; S07 owns vintage control).
- Raw data was fetched for audit probes only; no raw_observations rows were
  persisted to the dev database in this unit (persistence tested against
  the disposable test database).
- FRED mirror code still unverified (no FRED key).

## Rollback checkpoint
- Pre-unit: `b98b4c1`.
