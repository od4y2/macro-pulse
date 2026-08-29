# Digital Lens Methodology (S11, RQ2)

RQ2: *How do internet, mobile, and account-ownership rates co-vary with
income and gender across the panel, and where do measurement gaps hide
digital exclusion?*

Implementation: `src/macropulse/lenses/digital.py`. Tests:
`tests/test_digital_lens.py`. Live demonstration:
`evidence/S11/live-lens-demo.md`.

## Two dimensions (the unit objective, made explicit)

1. **Reach** - how far digital access extends: internet usage
   (IT.NET.USER.ZS, % of population), mobile subscriptions
   (IT.CEL.SETS.P2, per 100 people), account ownership (FX.OWN.TOTL.ZS,
   % of adults). Levels, each with its own identity.
2. **Inclusion gaps** - who is inside vs outside:
   `account_internet_gap` and `gender_account_gap`.

Component-first (S10 pattern): no index, no composite score, each
component keeps its identity; relationships are explicit documented
arithmetic; missingness is named, never imputed.

## Components

| Key | Indicator | Source code | Unit |
|---|---|---|---|
| internet | internet_users_pct | IT.NET.USER.ZS | % of population |
| mobile | mobile_subscriptions_per100 | IT.CEL.SETS.P2 | per 100 people |
| account | account_ownership_pct | FX.OWN.TOTL.ZS | % of adults |
| account_female | *(catalog fallback reference, not a catalog indicator)* | FX.OWN.TOTL.FE.ZS | % of adults |

`account_female` is the catalog's account-ownership fallback source,
repurposed as the gender dimension - it is a source-level component, not
a new indicator (the locked catalog is not extended).

## Relationships (defined in `RELATIONSHIPS`)

| Relationship | Formula | Reading |
|---|---|---|
| `account_internet_gap` | account − internet (pp) | financial exclusion among the connected (negative) or financial reach beyond connectivity (positive). **Denominators differ (adults vs population) - documented limitation, reported unadjusted.** |
| `gender_account_gap` | account_female − account (pp) | female deficit vs the all-adult average. **Conservative proxy**: the proper female−male gap needs the male series, which is not in the locked catalog; the all-adult average includes women, so the female deficit is understated. Negative = women below the national average. |

## Co-variation with income (RQ2's income dimension)

`rank_covariation(xs, ys)` - Spearman rank correlation (ties share
average ranks), always returning `(coefficient, n)`. Rank (not Pearson)
because the panel is 10 economies and the distributions are not normal;
reporting `n` because a coefficient without its sample size would hide
the fragility. **Descriptive measure of co-movement only** - a high
coefficient licenses no causal claim (S01 non-claims).

The income reference series is GDP per capita PPP
(NY.GDP.PCAP.PP.KD, live-verified 2026-08-29) - an analysis auxiliary,
not a monitored catalog indicator.

## Measurement gaps (RQ2's blind-spot half)

`measurement_gap(observed_years, as_of)` reports per dimension the last
year with a real observed value and the years since - relative to a
caller-supplied reference year (the lens is pure: no clock reads).
Never-observed dimensions are named explicitly (`never_observed`).

This makes measurement asymmetries visible instead of hiding them:

- Findex is survey-wave data (2011/2014/2017/2021/2024) while internet
  usage is annual - a two-dimensional profile can only be built where the
  waves intersect.
- The World Bank API returns NULL placeholder rows for not-yet-published
  years (live finding, 2026-08-29: 2025 rows across the panel) - the
  connector maps them to explicit missingness; alignment must use
  OBSERVED periods, not returned periods.
- A country's stalest dimension drags its whole profile back (live
  finding: JPN's mobile series ends 2023, so JPN's four-component profile
  aligns to 2021 even though its account data reaches 2024).

## Construction rules

- One period + one vintage per profile; multi-period/multi-vintage input
  raises `LensError` (build one profile per snapshot).
- Duplicate component keys rejected (ambiguous value selection).
- Missing components named `(key, reason)`; unfetched = `component_not_fetched`.
- Relationships needing a missing component are `None`, never guessed.
- Non-lens keys are ignored but at least one lens component is required.
- `Component` enforces: NULL requires a reason; a value cannot carry one.

## Claims boundary (S01)

- All relationships are descriptive arithmetic on observed values.
- The gender gap is a measurement, not an accusation of policy; the
  account-internet gap is a spread, not a diagnosis.
- Rank covariation describes co-movement across 10 economies at one
  point in time - no causal direction, no ranking of merit.
