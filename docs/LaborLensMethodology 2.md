# Labor Lens Methodology (S10, RQ1)

RQ1: *How do youth unemployment, NEET, and school-to-work transition
indicators diverge from headline unemployment across the panel, and how
does that divergence change across data vintages?*

Implementation: `src/macropulse/lenses/labor.py`. Tests:
`tests/test_labor_lens.py`. Live demonstration:
`evidence/S10/live-lens-demo.md`.

## Component-first principle

The lens **never mixes indicators into a single index or score**. Every
component enters a `SlackProfile` with its own identity (indicator, period,
vintage, value, missing reason) and is reported as-is. The analysis is the
relationships *between* components, each an explicit documented quantity.
Why: a composite index hides exactly the divergence RQ1 asks about, and
weighting choices (which component matters more?) are judgments the
platform does not make (S01 non-claims: comparisons are descriptive, not
rankings).

## Components

| Component | Indicator | Unit | Direction |
|---|---|---|---|
| headline | unemployment_rate | percent | lower_is_better |
| youth | youth_unemployment_rate | percent | lower_is_better |
| neet | neet_rate | percent | lower_is_better |
| enrollment | tertiary_enrollment (school-to-work transition proxy) | percent_gross | higher_is_better |

## Relationships (each defined in `RELATIONSHIPS`)

| Relationship | Formula | Reading |
|---|---|---|
| `youth_headline_gap` | youth − headline (pp) | the RQ1 divergence; positive = youth worse |
| `youth_ratio` | youth ÷ headline (×) | level-independent multiple; None on zero headline (never fabricated) |
| `neet_minus_unemployed` | NEET − headline (pp) | the withdrawn/discouraged component: NEET counts youth outside the labor force, unemployment does not |
| enrollment | reported, never combined | enrollment growth mechanically lowers youth unemployment (composition); no causal or welfare claim |

Gap AND ratio are both reported because they describe different labor
markets: a 2× ratio and a 20pp gap can coexist (ZAF) or diverge (USA) -
neither is collapsed into the other.

## Construction rules

- **One coherent snapshot per profile**: all components must share one
  period and one vintage; multi-period or multi-vintage input raises
  `LensError` (build one profile per snapshot instead - that is how
  vintage analysis works).
- **Period alignment is the caller's job**: sources publish at different
  lags (live demo: ILOSTAT NEET ends 2024 while WB unemployment ends
  2025). The lens takes components AT a period; aligning to the latest
  common period is explicit caller behavior, never silent.
- **Missingness is named, never imputed**: a missing component appears in
  `missing_components` as `(name, reason)`; relationships that need it are
  `None`. An unfetched component is `component_not_fetched`.
- **Non-lens components are ignored** (they contribute nothing), but at
  least one lens indicator must be present.
- `Component` enforces the standard invariant: NULL requires a reason; a
  value cannot carry one.

## Vintage divergence (RQ1's second half)

`divergence_by_vintage(profiles)` groups profiles by period and returns,
per period, the sorted `youth_headline_gap` values from every stored
vintage. Multiple entries = the divergence itself was revised (a genuinely
revision-sensitive quantity); single = stable. Descriptive only - no claim
about which vintage is correct (that is RQ4/S07 territory: vintages are
all preserved, none privileged).

`youth_headline_gap_series(headline, youth)` computes the divergence series
across periods: a period produces a number only when BOTH inputs exist;
otherwise `None` (explicit; no interpolation across gaps).

## Claims boundary (S01)

- All relationships are descriptive arithmetic on observed values.
- "Youth worse" = the gap is positive, nothing more - no welfare, policy,
  or causal claim.
- No country ranking: profiles are per-country; cross-country numbers are
  presented side by side, never aggregated into scores of merit.
