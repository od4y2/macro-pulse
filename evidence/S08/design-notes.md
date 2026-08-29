# S08 design notes

## Prior-state check

- git checkpoint: 860f6d4 (S07), working tree clean
- baseline: 159/159 tests passing, DB healthy

## Scope decision

Extended the audit-era starter `src/macropulse/metrics/transforms.py`
(kept `percent_change`/`weighted_coverage` + their 3 baseline tests) into
the full S08 objective: YoY, MoM, percentage-point change, annualization,
rolling trend. Split concerns:

- `transforms.py` - pure series-level functions with `SeriesPoint` /
  `DerivedPoint` (inputs and outputs both carry explicit missingness)
- `engine.py` - DB glue: latest-vintage loader, observation-id map,
  `persist_derived` writing `derived_metrics` + `metric_versions`

No schema changes: the S03 contract already reserved both tables.

## Rule highlights (full table in docs/TransformationRules.md)

- Closed missing-reason vocabulary on derived points:
  insufficient_history / input_missing / zero_base / non_positive_base /
  incomplete_window. Zero and negative percent-change bases are missing,
  not infinity or misleading ratios.
- Rolling mean requires a COMPLETE consecutive window; a window spanning
  a gap is incomplete (never silently re-denominated).
- Formula registry `FORMULAS`: name -> definition text, recorded verbatim
  into `metric_versions.definition`; `formula_ref` must resolve to a
  registry name (no free-text drift).
- Lineage: `inputs` JSON holds input observation ids; missing derived
  outputs produce no row (schema forbids NULL; no fabrication) with
  reasons retained in the returned list.
- Annualization requires 12 % lag == 0 (whole compounding periods).
- `mom` on non-monthly data degrades honestly: every output
  insufficient_history, not an error.

## Boundary decisions

- `SeriesPoint` enforces the hidden-missingness invariant on the
  transform INPUT side too (NULL requires reason).
- Vintage chain input: engine reads the LATEST vintage per period
  (superseded vintages remain in the store - S07 semantics preserved).
- Empty series -> empty output; lag <= 0 / window < 1 / unknown frequency
  -> ValueError; duplicate input periods -> ValueError.

## Results

- 199/199 tests (40 new: 31 in test_transforms.py on top of the 3 retained
  audit-era baselines, 9 in test_derive_engine.py), ruff clean on all
  unit-intended files (the audit-era I001 in test_transforms.py was fixed
  as the file became unit-intended), smoke passed.
