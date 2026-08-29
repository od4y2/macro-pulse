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
comparability notes, limitations, and a direction (S09 presentation
convention: `higher_is_better` / `lower_is_better` / `neutral` - how a
higher value reads on the dashboard; `policy_rate` is neutral because
direction adjustment would assert a judgment).

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

## Verification status (updated after live audits, 2026-08-19)

Every catalog code has been verified against its live API (S05 World
Bank/ILOSTAT audit + FRED follow-up with a real key): 18/18 probes OK -
see `evidence/S05/live-source-audit.txt` and
`PYTHONPATH=src python scripts/audit_sources.py` to reproduce. Corrections
made from live evidence:

- digital_payments_made_pct primary: WB `g20.any` (was TBD)
- youth_unemployment_rate fallback: ILOSTAT `DF_SDG_0852_SEX_AGE_RT`
  (S02's SDG_0811 guess was wrong - that is GDP growth)
- neet_rate fallback: ILOSTAT `DF_EIP_NEET_SEX_RT` (was TBD)
- gdp_real_growth fallback: FRED `CLVMNACSCAB1GQDE` (S02's guess was
  missing the DE country suffix)

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
