# S11 live lens demo - Digital Reach and Inclusion Gap (RQ2)

- Date: 2026-08-29 (~08:35 UTC)
- Evidence labels: all figures below are **real** (live World Bank API v2,
  `api.worldbank.org`), fetched via `WorldBankConnector.fetch_indicator`
- Reproduction: `PYTHONPATH=src .venv/bin/python evidence/S11/live-demo-script.py`
  (raw output in `live-demo-output.txt`)
- Panel: USA, CHN, JPN, DEU, GBR, IND, BRA, KOR, ZAF, MEX (10 economies)
- Alignment rule: each profile uses the latest period where ALL four lens
  dimensions have an observed (non-NULL) value

## Panel output (verbatim)

```
== panel (aligned to latest period with all four dimensions observed) ==
iso3 period   internet  mobile  account  female acct-int  gender
USA  2024    94.7  113.2   97.0   97.1    +2.3    +0.1
CHN  2024    92.0  131.8   89.4   89.2    -2.6    -0.2
JPN  2021    82.9  159.5   98.5   98.8   +15.6    +0.4
DEU  2024    93.5  129.2   98.3   98.9    +4.8    +0.6
GBR  2024    95.5  121.6   99.3   99.3    +3.8    -0.0
IND  2024    64.9   79.4   89.0   89.2   +24.1    +0.2
BRA  2024    84.5  101.9   86.4   82.3    +1.9    -4.1
KOR  2024    97.9  172.5   96.9   97.1    -1.0    +0.2
ZAF  2024    78.4  179.3   81.1   81.0    +2.8    -0.1
MEX  2024    83.1  116.5   53.0   47.4   -30.1    -5.6
```

(columns: internet % pop, mobile per 100, account % adults, female
account % adults, `account_internet_gap` pp, `gender_account_gap` pp;
rounded from raw values in `live-demo-output.txt`)

```
== rank covariation vs GDP per capita PPP (same aligned year) ==
account   vs gdp_pc: rho=+0.70 (n=10)
internet  vs gdp_pc: rho=+0.82 (n=10)

== measurement gaps (panel-union observed years, as_of 2026) ==
internet         last_observed=2025 years_since=1
mobile           last_observed=2024 years_since=2
account          last_observed=2024 years_since=2
account_female   last_observed=2024 years_since=2
```

## What the demo shows (descriptive only, no causal claims)

- Reach co-moves with income: both account ownership and internet usage
  rank-correlate strongly with GDP per capita PPP across the 10 economies
  (+0.70 / +0.82, n=10 - small panel, coefficient reported with n).
- The two gaps separate countries that reach levels alone would not:
  MEX pairs moderate connectivity (83.1%) with the panel's deepest
  financial exclusion among the connected (-30.1pp) and the largest
  female deficit (-5.6pp); IND shows +24.1pp account-above-internet
  (financial reach ahead of connectivity - mobile-money era effect;
  descriptive observation only).
- Gender gaps are near-zero in high-income economies (USA +0.1, GBR
  -0.0) and largest in MEX (-5.6) and BRA (-4.1). The measure is a
  conservative proxy (female minus all-adult average, so the female-male
  deficit is understated - documented in
  `docs/DigitalLensMethodology.md`).

## Live findings (the RQ2 "measurement gaps hide digital exclusion" half)

1. **World Bank API returns NULL placeholder rows for unpublished
   years** (live, 2026-08-29): e.g. USA internet carries 31 NULL rows,
   Findex series 61 NULL rows, including 2025 rows across the whole
   panel. The connector maps them to explicit missingness; alignment
   MUST use observed periods, not returned periods - a max-of-returned
   periods rule would produce all-NULL profiles.

2. **JPN's profile aligns to 2021, not 2024** (live): JPN internet is
   observed through 2024 (contiguous since 1990), mobile ends 2023
   (contiguous since 1960), Findex account waves are
   {2011, 2014, 2017, 2021, 2024}. Intersection = {2011, 2014, 2017,
   2021} - the stalest dimension (mobile, 2023) blocks 2024, and Findex
   has no 2022/2023 observations. The four-component truth for JPN is 3
   years older than its newest data. This is the lens working as
   designed: the binding measurement constraint is made visible, not
   hidden by mixing vintages.

3. **Findex wave years are 2024, not 2025** (live): the panel's latest
   Findex observations are 2024. `src/macropulse/catalog.py` coverage
   strings previously said "2021/2025 waves"; corrected to
   "2011/2014/2017/2021/2024 waves; re-verified live 2026-08-29" for
   both FX.OWN.TOTL.ZS and FX.OWN.TOTL.FE.ZS. (Catalog content
   correction, verified against the live source - within the S11
   intended-files statement.)

4. **Asymmetric staleness** (live): internet usage publishes a year
   ahead of mobile and Findex (2025 vs 2024, as of 2026-08-29) - the
   measurement_gap map quantifies this per dimension instead of letting
   a silently mixed-period profile imply alignment that does not exist.
