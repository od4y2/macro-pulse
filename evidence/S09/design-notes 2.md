# S09 design notes

## Prior-state check

- git checkpoint: c0a3a87 (S08), working tree clean
- baseline: 199/199 tests passing, DB healthy

## Scope decisions

Four deliverables - fixed-window scaling, direction handling, coverage,
publication gates - as pure functions plus one engine loader:

- `metrics/standardize.py`: `standardize_series` (median/MAD robust
  z over a trailing fixed-size window) + `panel_coverage` (ratio of sums)
- `metrics/gates.py`: `evaluate_gate` with explicit reason codes
- `metrics/transforms.py`: `robust_z` added to the FORMULAS registry
  (persistence path for standardized scores)
- `metrics/engine.py`: `latest_vintage_records` loader (latest_vintage_
  series refactored onto it)
- `catalog.py`: `direction` field (defaults "neutral" so partially
  constructed test entries stay valid; all 12 entries declare it;
  validate_catalog rejects invalid values)

## Rule highlights (full table in docs/StandardizationRules.md)

- Robust = median/MAD; no normal-consistency constant (comparability,
  not normality, is the goal). Fixed window SIZE -> same history depth
  per country, no dependence on future data.
- Partial window occupancy is recorded (`window_occupancy`), never
  hidden; below 3 -> missing `insufficient_history`. MAD == 0 ->
  missing `zero_scale` (never fabricated 0/inf).
- Direction is a presentation convention: value > 0 = favorable vs own
  median; `policy_rate` is NEUTRAL (adjusting it would assert a
  judgment). Raw deviation retained alongside the adjusted value.
- Panel coverage = ratio of sums (series-length weighted), per-country
  detail preserved; mean-of-ratios rejected (equal-weights small series).
- Gates check CONDITIONS (coverage, n_observed, evidence label,
  chronology), not S07 grade labels - one source of truth, one reason
  per failure. Reason codes closed; every failure named, nothing silent.
- Persistence: metric_key `{indicator}.robust_z{window}`, formula_ref
  resolves to the `robust_z` registry entry; missing scores -> no row.

## Boundary decisions

- min_coverage default 0.5 (majority); min_observed 3 (matches
  MIN_WINDOW_OCCUPANCY); require_real True (mocked never published as
  observed data). All parameterized with documented rationale.
- Empty series -> empty outputs; empty panel -> coverage 0.0.
- Input-order preservation: standardization iterates in input order
  (values are order-independent; callers wanting "latest" must sort -
  noted in evidence after finding WB returns newest-first).

## Live manual check (evidence/S09/live-manual-check.md)

Real WB unemployment 2000-2025 for USA and ZAF: both gate-pass; USA 2025
scores -0.47 (0.47 MADs above own median), ZAF 0.00 (at own median) -
demonstrating the "unusual for this country" semantics across very
different levels (~4% vs ~32%).

## Results

- 240/240 tests (41 new: 22 standardize, 14 gates, 5 catalog direction);
  ruff clean; smoke passed.
