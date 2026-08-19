# Indicator Catalog (defined in S02, 2026-08-19)

Machine-readable source of truth: `src/macropulse/catalog.py`. Render the
auditable table with `PYTHONPATH=src python -m macropulse.catalog_report`.
The catalog is metadata only - it contains no observation values.

## Catalog summary

12 indicators across 4 of the 5 locked modules. The fifth module
(`vintage-transparency`, RQ4) intentionally has no standalone indicators: it
is realized through provenance fields on every observation and the release
calendar built in S07.

| Module | Indicators |
|---|---|
| traditional-indicators | gdp_real_growth, cpi_inflation, unemployment_rate, policy_rate |
| labor-slack-youth (RQ1) | youth_unemployment_rate, neet_rate, tertiary_enrollment |
| digital-inclusion (RQ2) | internet_users_pct, mobile_subscriptions_per100, account_ownership_pct |
| payment-resilience-healthcare (RQ3) | digital_payments_made_pct (case-study reserve), health_expenditure_pct_gdp |

Each entry carries: unit, frequency, seasonal-adjustment status, primary and
fallback source references (system, code, verification status, coverage),
comparability notes, and limitations.

## Source systems and fallback policy

- **world_bank** is the primary cross-panel system (all ten economies) for
  annual macro, labor, and digital-inclusion indicators.
- **fred** is the primary for US high-frequency series (UNRATE, CPIAUCSL,
  FEDFUNDS) and a partial fallback elsewhere; FRED mirrors for non-US
  economies are country-specific and audited per indicator.
- **ilostat** is the planned fallback/direct source for youth and NEET
  series; its codes are the least stable and are fully re-audited in S05.

Fallback statuses: `primary-and-fallback` (fallback defined),
`primary-only` (no acceptable fallback yet - single point of failure),
`case-study-reserve` (sourcing deferred to S12).

## Verification honesty

Codes are marked `confirmed` only when they are long-established, widely
documented identifiers; everything else is `unverified` and must be
confirmed against the live APIs in S04/S05 before production use.
As of S02, 7 source references await live verification:

- gdp_real_growth fallback: FRED `CLVMNACSCAB1GQ` (DEU GDP mirror)
- youth_unemployment_rate fallback: ILOSTAT `SDG_0811_SEX_AGE_RT`
- neet_rate primary: WB `SL.UEM.NEET.ZS`; fallback: ILOSTAT code TBD-S05
- account_ownership_pct primary: WB `FX.OWN.TOTL.ZS`; fallback: `FX.OWN.TOTL.FE.ZS`
- digital_payments_made_pct primary: WB Findex code TBD-S05

## Comparability rules (enforced at catalog level)

1. ILO-modeled estimates (WB labor series) and national releases (e.g., BLS
   UNRATE) are not interchangeable; every observation must carry its source.
2. US monthly SA series (FRED) and panel-wide annual series (WB) answer
   different questions; mixing them in one chart requires explicit labelling.
3. Age-band differences (15-24 vs 16-24) affect all youth indicators.
4. Findex indicators exist only in survey years; interpolation between
   survey years would be synthetic data and must be labelled as such.
5. Mobile subscriptions per 100 people is a weak proxy for individual access
   and is used only alongside usage series.
