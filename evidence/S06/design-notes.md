# S06 design notes: normalization rules and the vintage fix

## Scope decision

`normalize_series()` is a **pure function** (no DB, no clock, no network):
`FetchedSeries` + catalog indicator -> `list[NormalizedRecord]`. Only
`persist_normalized()` touches the session. This keeps every unification
rule unit-testable without Postgres and keeps the pipeline deterministic.

## Rule highlights (full table in docs/NormalizationRules.md)

- **Unit**: canonical from catalog, values NEVER converted. Unit
  transformation is S08's derived-metric concern and must be labelled.
- **Frequency**: median month-gap inference (1/3/12 -> monthly/quarterly/
  annual). Median (not mode/min) tolerates a single missing period; any
  other median gap is an error, not a guess.
- **Seasonal adjustment**: default = catalog value, explicitly
  overridable per series because FRED/WB differ (e.g. SA vs NSA CPI).
  The applied value is stored per observation - never silently defaulted.
- **Missingness**: value=None MUST carry a missing_reason; a value with a
  reason is rejected too. No imputation, no dropping.
- **Quality**: `ungraded` here; grading deferred to S07 by design.
- **release_time = retrieval_time** as a documented proxy (none of the
  three source endpoints expose per-observation release timestamps).

## Connector vintage fix (live-audit follow-up, fixed in this unit)

Code contradicted the documented snapshot semantics: the WB and ILOSTAT
parsers stamped `vintage = period`. Since both APIs serve only the
current snapshot, the connectors now rebuild every point with
`vintage = retrieval_time.date()` after parsing. This matters for RQ4:
observation identity (indicator, country, period, vintage, source) must
change on each refetch or revisions become invisible.

## Prior-state check (before edits)

- git checkpoint: 8836f30 (S05 follow-up), working tree clean
- baseline: 94/94 tests passing, DB healthy

## Results

- 117/117 tests (23 new in tests/test_normalize.py)
- ruff clean on all unit-intended files
- smoke passed (`PYTHONPATH=src python -m macropulse.smoke`)
- pre-existing ruff I001 in audit-era baseline files (smoke.py,
  test_health.py, test_transforms.py) left untouched - out of unit scope,
  policy recorded in S05 evidence
