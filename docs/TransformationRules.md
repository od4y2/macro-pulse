# Transformation Rules (S08)

How normalized series become derived metrics. Implementation:
`src/macropulse/metrics/transforms.py` (pure functions) and
`src/macropulse/metrics/engine.py` (persistence). Tests:
`tests/test_transforms.py`, `tests/test_derive_engine.py`.

Transformations are pure: same points in, same derived points out. No DB,
no clock, no network.

## Formula table

Every formula has a definition text in `FORMULAS`, recorded verbatim in
`metric_versions.definition` when persisted (traceability; no magic
constants - the only numbers are 12 months/year, 100 for percent scale,
and 1 for the base step).

| Formula | Definition | Valid bases |
|---|---|---|
| `yoy` | `100 * (v_t / v_{t-12m} - 1)` - same period one year earlier | positive non-zero |
| `mom` | `100 * (v_t / v_{t-1m} - 1)` - lag 1 month (monthly series) | positive non-zero |
| `pct_change` | general lag-L-months percent change (`yoy`/`mom` are wrappers) | positive non-zero |
| `pp_change` | `v_t - v_{t-L}` in points - for rate-type series where percent-of-percent is meaningless | any sign |
| `annualized_pct` | `(1 + r/100)^(12/L) - 1` from the lag-L percent change r; requires 12 % L == 0 | inherited from `pct_change` |
| `rolling_mean` | trailing arithmetic mean of the last W **consecutive** periods (frequency step) | all window members non-NULL |

## Missingness rules (non-fabrication)

Closed missing-reason vocabulary on `DerivedPoint`:

| Reason | Trigger |
|---|---|
| `insufficient_history` | the lag/window input period is absent from the series |
| `input_missing` | the input period exists but its value is NULL |
| `zero_base` | percent change against a base of exactly 0 |
| `non_positive_base` | percent change against a negative base |
| `incomplete_window` | rolling window missing any member (absent period or NULL) |

- **Never imputed, interpolated, or filled.** A missing input yields a
  missing output with its reason; the reason is recorded, not hidden.
- Percent change against zero/negative bases is *missing*, not infinity
  or a misleading negative ratio - a documented policy decision.
- A rolling window spanning a gap is **incomplete**: the mean is never
  silently computed over the remaining members (that would change the
  denominator invisibly).
- `SeriesPoint` enforces the no-hidden-missingness invariant on inputs
  (NULL requires a reason; a value cannot carry one).

## Persistence rules (`engine.py`)

- **Input**: `latest_vintage_series(session, indicator, country)` reads
  the LATEST vintage per period (S07 superseded semantics - older
  vintages stay in the store untouched).
- **Output**: `persist_derived(...)` writes only computable points. The
  S03 schema forbids NULL derived values, and the engine never fabricates
  one: missing outputs produce **no row**, with their reasons retained in
  the returned list. Whether a value should exist is derivable from
  source coverage (the formula documents its lag/window requirements).
- **Lineage**: each row's `inputs` JSON stores the input observation ids
  (mapped from the input periods via `observation_id_map`).
- **Versioning**: each written row gets a `metric_versions` row carrying
  the formula definition text (default version `v1`).
- **Identity**: `(metric_key, country, period)` unique per the S03
  contract. Metric key convention: `{indicator_id}.{formula_name}` e.g.
  `cpi_inflation.yoy`.
- `formula_ref` must resolve to a `FORMULAS` name; unknown names raise
  (no free-text formula strings drifting from the registry).

## Applicability notes

- `mom` on a non-monthly series is not an error: the lag-1-month input
  simply never exists, so every output is `insufficient_history` (honest
  rather than a crash - the caller selected the wrong formula, and the
  data says so).
- `annualized_pct` composes `pct_change_series`; missing reasons
  propagate unchanged.
- Transform choice is the analyst's responsibility (S10-S12 lenses apply
  these to the right indicator types: pp changes on rates, YoY on
  levels/indices).
