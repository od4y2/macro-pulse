# Standardization and Coverage Rules (S09)

How series become comparable scores and when they may be published.
Implementation: `src/macropulse/metrics/standardize.py`,
`src/macropulse/metrics/gates.py`. Tests: `tests/test_standardize.py`,
`tests/test_gates.py`.

## Robust fixed-window scaling

`standardize_series(points, window, direction, frequency)` maps each
point to a signed score using its **trailing window** of `window`
consecutive periods (frequency step):

```
median = median(non-missing window values)
MAD    = median(|v - median|)
deviation = (v_t - median) / MAD
value     = -deviation  if direction == "lower_is_better"
             deviation  otherwise
```

- **Robust**: median/MAD, not mean/std. One extreme observation (crisis
  spike, rebasing jump) cannot dominate the scale - in a [1,2,3,4,100]
  window the deviation of 100 is 97 MADs, while a std-based z would be
  ~1.8 and the outlier would have inflated the scale for every other
  point. No normal-consistency constant (1.4826) is applied: the goal is
  scale-free comparability, not normality.
- **Fixed window**: the window SIZE is fixed, so every country's score is
  scaled by the same amount of history, and the definition never depends
  on data arriving later. Trailing (not full-history) so scores stay
  current; superseded vintages never enter (the engine's current view).
- **Partial occupancy is recorded, not hidden**: absent window members
  are skipped and `window_occupancy` reports how many non-missing values
  informed the scale. Below `MIN_WINDOW_OCCUPANCY` (= 3, the smallest
  sample where the median is an observed value rather than an
  interpolation of two) the score is missing with
  `insufficient_history`.

Missing reasons (closed set): `insufficient_history`, `input_missing`
(current value NULL), `zero_scale` (MAD == 0: more than half the window
identical - no dispersion; **never** fabricated as 0 or infinity).

## Direction handling

`direction` is a catalog field (`catalog.DIRECTIONS`), a presentation
convention - **not a welfare judgment**:

| Direction | Indicators | Adjustment |
|---|---|---|
| `higher_is_better` | GDP growth, tertiary enrollment, internet/mobile/account/payments/health-capacity | none |
| `lower_is_better` | CPI, unemployment, youth unemployment, NEET | sign flip |
| `neutral` | policy rate | none (direction adjustment would assert a judgment) |

After adjustment, `value` > 0 consistently reads "favorable relative to
the country's own window median"; the raw `deviation` is always retained
alongside.

## Panel coverage

`panel_coverage(reports)` aggregates per-country `MissingnessReport`s as
**ratio of sums**: `total observed / total expected`. A mean of
per-country ratios would weight a 2-period series equally with a
40-period one; ratio of sums weights by series length. Per-country
detail is preserved in `per_country`. Boundary: empty panel -> coverage
0.0, `fully_covered` False.

## Publication gates

`evaluate_gate(metric, report, latest_records, thresholds)` decides
whether a series may be published. Gates check **conditions, not S07
grade labels** (grades summarize the same conditions; gating on
conditions keeps one source of truth and one failure per problem).

| Reason code | Condition (default) |
|---|---|
| `coverage_below_minimum` | `report.coverage < 0.5` |
| `too_few_observations` | `report.n_observed < 3` |
| `not_real_evidence` | any latest-vintage record not labelled `real` (mocked/synthetic are never published as observed data) |
| `impossible_chronology` | any latest-vintage record with `vintage < period` |

Default rationale: 0.5 coverage = majority of the series' own span; 3
observations = the same minimum where a median is an observed value.
Every check emits a `GateCheck` with a pass/fail and a detail string
carrying the actual numbers; `GateResult.reasons` names every failure -
a gate never silently drops a series.

## Persistence convention

Standardized scores persist through the S08 engine:
`persist_derived(..., metric_key=f"{indicator_id}.robust_z{window}", formula_name="robust_z")`.
The `robust_z` definition lives in the `FORMULAS` registry (recorded into
`metric_versions`); the window size is embedded in the metric key so
different windows are distinct identities. Missing scores produce no row
(S08 rule: no fabricated NULLs).

## What S09 does not do

- No imputation anywhere: absent/NULL inputs yield missing outputs with
  reasons; occupancy is recorded.
- No direction judgment on neutral indicators; no claim that "favorable"
  scores imply welfare (the non-claims boundary in S01 governs).
- No cross-country pooling of the scaling: each score is relative to the
  country's own history (documented comparability semantics: scores
  answer "unusual for this country", not "high vs. other countries").
