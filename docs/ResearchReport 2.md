# MacroPulse Research Report

MacroPulse is a global macroeconomic monitoring and statistical-blind-spot
analysis platform: traceable public data in, transparent derived metrics,
structured briefings, and an explicit claims boundary out. This document is
the unit S19 deliverable - the complete report, the typeset methodology, the
limitations, and the reproducibility appendix.

Every value quoted below is observed, carried over from a validated
repository artifact (an evidence file or a stored observation with full
provenance), and cited to the file it was verified in. Values are stated
as served - no rounding beyond what the cited artifact records. The report
is a point-in-time record: each finding carries the date its evidence was
captured, and later vintages may differ. No statement in this document goes
beyond descriptive arithmetic on observed values.

Date of record: October 2026. Unit sequence: S01-S19 under
`prompts/GlobalEngineeringContract.md`.

## Research scope and claims boundary

The locked scope lives in code (`src/macropulse/scope.py`) and is the single
machine-readable source of truth for the questions, the panel, and the
boundary. Four research questions drive the platform:

- **RQ1 (labor-slack-youth, S10):** How do youth unemployment, NEET, and
  school-to-work transition indicators diverge from headline unemployment
  across the panel, and how does that divergence change across data vintages?
- **RQ2 (digital-inclusion, S11):** How do internet, mobile, and
  account-ownership rates co-vary with income and gender across the panel,
  and where do measurement gaps hide digital exclusion?
- **RQ3 (payment-resilience-healthcare, S12):** What do payment-outage
  episodes reveal about resilience measurement in digitized healthcare
  systems, for the case-study subset of the panel?
- **RQ4 (vintage-transparency, S07):** Where do official release calendars,
  revisions, and methodology breaks create systematic blind spots in
  cross-country comparison?

The country panel is ten economies, locked in S01: United States, China,
Japan, Germany, United Kingdom, India, Brazil, South Korea, South Africa,
and Mexico - a balanced set chosen for coverage across the three data
systems (FRED mirrors, World Bank, ILOSTAT), not for outcomes.

The claims boundary is a closed list (`macropulse.scope.NON_CLAIMS`), restated
below in bounded wording: this document is itself scanned by the platform's
banned-phrase filter with no exemption, and the S16 lesson is that a
disclaimer using banned phrasing is textually identical, to the check, to
the thing it disclaims. In the boundary's own register:

- No causal claims about macroeconomic outcomes without documented evidence.
- No financial guidance, price objectives, or trade directives.
- No fabricated values, release dates, citations, or test results.
- No presentation of synthetic, mocked, or cached data as observed data.
- AI-generated prose derives only from validated structured inputs.
- No claims of live API, cloud deployment, or production status without
  evidence.
- Cross-country comparisons are descriptive, not rankings or scores of
  merit.

Every dataset and observation carries one evidence label from a closed
vocabulary: `real` (live-retrieved from the provider API), `synthetic` (test
fixture, never presented as observed), `mocked` (deterministic no-key
fixture), `cached` (reserved; the refresh layer stores real data or records
failure - no cached rows are emitted), and `external` (document-verified
registry entry; a document, never an API observation). Quality grades use
the S07 closed vocabulary (`official`, `revised`, `flagged`, `ungraded`,
plus reserved `preliminary` and `estimated`); grade meanings are surfaced
verbatim in the dashboard. The full scope statement is published in
`docs/ResearchScope.md` and the data governance rules in
`docs/DataGovernance.md`.

## Data architecture and provenance

**Sources.** FRED (and its vintage archive ALFRED) for United States series;
the World Bank indicator API v2 for the cross-country panel; ILOSTAT for
NEET; and official government documents, verified live and quoted verbatim,
for the payment-resilience case study. The indicator catalog
(`src/macropulse/catalog.py`) records, for each of the twelve indicators:
unit, frequency, seasonal adjustment, primary and fallback source codes,
comparability notes, and limitations - published as `docs/IndicatorCatalog.md`.

**Pipeline.** Connectors (`src/macropulse/connectors/fred.py`,
`src/macropulse/connectors/worldbank.py`,
`src/macropulse/connectors/ilostat.py`) fetch and archive raw payloads;
normalization (`src/macropulse/pipeline/normalize.py`) maps them onto one
observation schema; quality control stamps grades and names missingness
(`src/macropulse/quality/assessment.py`,
`src/macropulse/quality/missingness.py`); vintage control
(`src/macropulse/quality/vintage.py`) keeps every vintage as a distinct
stored identity. Derived metrics are computed by the S08/S09 engine
(`src/macropulse/metrics/engine.py`) behind publication gates
(`src/macropulse/metrics/gates.py`). A FastAPI query service
(`src/macropulse/api/main.py`) serves the data under pinned response
schemas, and the Streamlit dashboard (`app/dashboard.py`) is a thin HTTP
client over it (`src/macropulse/views/client.py`).

**Storage.** PostgreSQL under Alembic migrations: a raw archive
(`raw_observations`), the normalized observation store, a derived-metrics
store with lineage, and audit tables for refresh and briefing runs
(`docs/DatabaseContract.md`). Every normalized observation preserves nine
provenance fields (the S01 contract): `period`, `release_time`,
`retrieval_time`, `vintage`, `unit`, `frequency`, `seasonal_adjustment`,
`source`, and `quality_grade`. Superseded vintages are retained - nothing
is overwritten - so a value can always be traced to the release that
carried it. The operational database is a Neon-managed Postgres instance;
the full-data migration to it was verified with 12-table parity on
2026-09-18 (recorded in `docs/decisions.md`). Public cloud hosting is in
rehearsal and is S20 scope; no live-deployment claim is made here.

**The three faces of every formula.** Each formula exists as code (the
computing function), as registry text (what the methodology API serves),
and - new in this unit - as typeset math (`src/macropulse/report/formulas.py`).
The typeset layer is anchored: every registry-backed entry carries the
registry's exact current text, and quantities without a registry entry
(Spearman rank covariation, panel coverage) are anchored to their computing
functions by import. A validator reports drift in either direction, so a
registry edit that leaves the report behind is a reported problem, never
silent divergence.

## Formula presentation

All fourteen quantities the platform computes are presented below in
scientific notation, exactly as the typeset registry holds them. Notation
tables define every symbol; guard conditions state when a quantity is
missing rather than computed.

### Metric transforms (S08)

**Percent change over a lag of L months** (`pct_change`; requires a
positive non-zero base; missing inputs stay missing):

$$100\,\left(\frac{v_t}{v_{t-L}} - 1\right)$$

| symbol | meaning |
|---|---|
| $v_t$ | value at period t |
| $L$ | lag in months (positive integer) |

**Year-over-year percent change** (`yoy`; pct_change with L = 12 months -
same period one year earlier):

$$100\,\left(\frac{v_t}{v_{t-12\,\mathrm{m}}} - 1\right)$$

| symbol | meaning |
|---|---|
| $v_t$ | value at period t |
| $v_{t-12\,\mathrm{m}}$ | same period one year earlier |

**Month-over-month percent change** (`mom`; pct_change with L = 1 month;
monthly series only):

$$100\,\left(\frac{v_t}{v_{t-1\,\mathrm{m}}} - 1\right)$$

| symbol | meaning |
|---|---|
| $v_t$ | value at period t |
| $v_{t-1\,\mathrm{m}}$ | the previous month (monthly series only) |

**Percentage-point change over a lag of L months** (`pp_change`; for
rate-type series where percent-of-percent is meaningless; defined for any
sign of input):

$$\delta_t = v_t - v_{t-L}$$

| symbol | meaning |
|---|---|
| $\delta_t$ | percentage-point change |
| $v_t$ | value at period t |
| $L$ | lag in months |

**Annualized percent rate from a period-over-period change** 
(`annualized_pct`; requires 12 % L == 0 - whole compounding periods per
year):

$$100\,\left(\left(1 + \frac{r}{100}\right)^{12/L} - 1\right)$$

| symbol | meaning |
|---|---|
| $r$ | period-over-period percent change (in percent) |
| $12/L$ | whole compounding periods per year (12 % L == 0) |

**Trailing arithmetic mean** (`rolling_mean`; over the last W consecutive
periods; every window member must exist with a non-NULL value - partial
windows are missing, never half-computed):

$$\bar{v}_t = \frac{1}{W}\sum_{i=0}^{W-1} v_{t-i}$$

| symbol | meaning |
|---|---|
| $\bar{v}_t$ | trailing mean at period t |
| $W$ | window length in periods (frequency steps) |
| $v_{t-i}$ | the i-th previous period; every member must exist |

### Robust standardization (S09)

**Robust fixed-window standardization** (`robust_z`; over the trailing N
consecutive periods, direction-adjusted so positive = favorable; window
occupancy of at least 3 non-missing members is required; zero MAD is
missing with reason `zero_scale`, never fabricated):

$$z_t = \frac{v_t - \operatorname{median}(W_t)}{\operatorname{MAD}(W_t)}$$

| symbol | meaning |
|---|---|
| $z_t$ | robust standardized score (direction-adjusted so positive = favorable) |
| $W_t$ | the trailing N consecutive periods (frequency step) |
| $\operatorname{median}(W_t)$ | window median |
| $\operatorname{MAD}(W_t)$ | window median absolute deviation |

### Labor lens relationships (S10)

**Youth-headline unemployment divergence** (`youth_headline_gap`; the RQ1
divergence measure; only computed when both inputs exist, never imputed;
dual-anchored to the metric and labor registries):

$$g_t = u^{\mathrm{youth}}_t - u^{\mathrm{headline}}_t$$

| symbol | meaning |
|---|---|
| $g_t$ | divergence in percentage points (positive = youth worse) |
| $u^{\mathrm{youth}}_t$ | youth unemployment rate |
| $u^{\mathrm{headline}}_t$ | headline unemployment rate |

**Youth-to-headline unemployment ratio** (`youth_ratio`; reported alongside
the pp gap; level-dependent; None on zero headline):

$$R_t = \frac{u^{\mathrm{youth}}_t}{u^{\mathrm{headline}}_t}$$

| symbol | meaning |
|---|---|
| $R_t$ | unitless multiple; None on zero headline |
| $u^{\mathrm{youth}}_t$ | youth unemployment rate |
| $u^{\mathrm{headline}}_t$ | headline unemployment rate |

**NEET minus headline unemployment** (`neet_minus_unemployed`; measures the
withdrawn/discouraged component of youth disengagement not visible in
unemployment):

$$d_t = \mathrm{NEET}_t - u^{\mathrm{headline}}_t$$

| symbol | meaning |
|---|---|
| $d_t$ | withdrawn/discouraged component, in percentage points |
| $\mathrm{NEET}_t$ | NEET rate (not in education, employment or training) |
| $u^{\mathrm{headline}}_t$ | headline unemployment rate |

### Digital lens relationships (S11)

**Account-internet gap** (`account_internet_gap`; financial exclusion among
the connected; denominators differ - adults vs population - a documented
comparability limitation, reported unadjusted):

$$g_t = a_t - i_t$$

| symbol | meaning |
|---|---|
| $g_t$ | exclusion among the connected, in percentage points |
| $a_t$ | account ownership, share of adults |
| $i_t$ | internet usage, share of population |

**Gender account gap** (`gender_account_gap`; conservative proxy - the male
series is not in the locked catalog, and the all-adult average includes
women, understating the female deficit):

$$g_t = a^{\mathrm{female}}_t - a^{\mathrm{all\ adults}}_t$$

| symbol | meaning |
|---|---|
| $g_t$ | conservative gender gap, in percentage points (negative = women below the national average) |
| $a^{\mathrm{female}}_t$ | female account ownership |
| $a^{\mathrm{all\ adults}}_t$ | all-adult account ownership |

### Quantities anchored to code

**Spearman rank covariation** (`spearman_rho`; computed by
`src/macropulse/lenses/digital.py` - always reported with its panel size n;
ties share average ranks):

$$\rho = 1 - \frac{6 \sum_{i=1}^{n} d_i^2}{n\,(n^2 - 1)}$$

| symbol | meaning |
|---|---|
| $\rho$ | Spearman rank correlation; always reported with n |
| $d_i$ | rank difference of the i-th economy (ties share average ranks) |
| $n$ | panel size (10 economies) |

**Panel coverage** (`panel_coverage`; computed by
`src/macropulse/metrics/standardize.py` as a ratio of sums - the S09
publication gate reads it):

$$C = \frac{\sum_{c} n^{\mathrm{obs}}_c}{\sum_{c} n^{\mathrm{exp}}_c}$$

| symbol | meaning |
|---|---|
| $C$ | panel coverage as a ratio of sums (S09) |
| $n^{\mathrm{obs}}_c$ | observed points for economy c |
| $n^{\mathrm{exp}}_c$ | expected points for economy c |

## Findings

Findings are descriptive statements about observed values, cited to the
evidence file each was verified in. They are not causal statements,
statements about policy, or statements about any period after the cited
capture date.

**Youth divergence separates economies the headline rate alone does not
(RQ1).** Full-component profiles (WB unemployment, WB youth unemployment,
ILOSTAT NEET; all `real`; aligned to the latest period covered by all
series; captured 2026-08-29 in `evidence/S10/live-lens-demo.md`):

| economy | period | headline | youth | NEET | youth-headline gap | NEET-headline gap |
|---|---|---|---|---|---|---|
| USA | 2025-01-01 | 4.198 | 9.34 | 11.59 | 5.1pp | 7.4pp |
| ZAF | 2024-01-01 | 32.279 | 60.248 | 34.61 | 28.0pp | 2.3pp |
| BRA | 2025-01-01 | 5.97 | 13.981 | 18.703 | 8.0pp | 12.7pp |

School-enrollment was unfetched in these profiles and is named as
`component_not_fetched` rather than hidden. The arithmetic contrast is the
finding: South Africa's 28.0pp youth-headline gap comes with only a 2.3pp
NEET-headline gap (youth disengagement there is mostly recorded as active
job search), while Brazil's smaller 8.0pp gap comes with a 12.7pp
NEET-headline gap (a larger withdrawn component). Gap and ratio are
reported together precisely so level differences like these stay visible.
ZAF's profile aligns to 2024, not 2025 - ILOSTAT's NEET series ends a
year earlier than the WB unemployment series, and the profile keeps the
common period rather than blending.

**Digital reach co-moves with income, and the two gaps separate economies
that reach levels alone do not (RQ2).** Panel-wide (all `real`, live World
Bank API, captured 2026-08-29 in `evidence/S11/live-lens-demo.md`):
account ownership and internet usage rank-correlate with GDP per capita
PPP at rho = +0.70 and +0.82 respectively (n = 10 - a small panel; the
coefficient is always reported with n). Mexico pairs moderate connectivity
(83.1% internet, 2024) with the panel's deepest financial exclusion among
the connected (account-internet gap -30.1pp) and the largest female
account deficit (-5.6pp against the all-adult average); India shows
+24.1pp account-above-internet (financial reach ahead of connectivity -
a descriptive observation, not an explanation); gender gaps are near zero
in high-income economies (USA +0.1, GBR -0.0) and widest in MEX (-5.6) and
BRA (-4.1). Three measurement findings came out of the same run:
the World Bank API returns NULL placeholder rows for unpublished years
(USA internet carried 31 NULL rows; Findex series 61), which the connector
maps to explicit missingness; Japan's four-component profile aligns to
2021, not 2024, and that binding constraint is shown rather than hidden
(mobile ends 2023 and Findex has no 2022/2023 observations); and the
panel's Findex waves are 2011/2014/2017/2021/2024 - the catalog's coverage
text was corrected against the live source and recorded in the same
evidence file.

**Documented outage episodes show a recurring, scheduled resilience cost
(RQ3).** The case-study registry (`src/macropulse/case_study/episodes.py`,
published as `docs/PaymentResilienceCaseStudy.md`) holds four
machine-verified Yunnan medical-insurance payment-outage episodes, each
external-labelled and citation-mandatory, verified 2026-08-29 in
`evidence/S12/live-verification.md`: year-end rollover suspensions of 48
hours each (2024-12-31 20:00 to 2025-01-02 20:00, and 2025-12-31 20:00 to
2026-01-02 20:00), an 8-hour platform upgrade (2026-03-24 22:00 to
2026-03-25 06:00), and a 2-hour upgrade (2026-06-12 23:00 to 2026-06-13
01:00). The year-end 48-hour suspension is recurring under provincial
unified arrangement - a scheduled, announced resilience cost, distinct from
failures. The healthcare-geography record for the same lens: China's 2023
NHC bulletin reports 1,070,785 institutions and 10,174,000 beds nationwide
(machine-extracted verbatim); Yunnan records 28,765 institutions and
359,900 beds "as of 2023" (Yunnan Daily, quoted verbatim). 29 of 31
provinces have no verified record and are explicitly listed as unrecorded -
named missingness, never imputed. Sources that failed verification (a
scanned-image PDF with no text layer, an HTML-returned PDF endpoint, a
TLS-mismatched mirror, an unreachable bulletin) are excluded from the
registry and listed with their failure modes.

**Revisions are real, stored, and revisable-in-place (RQ4).** Live ALFRED
verification (captured 2026-08-29 in
`evidence/S07/live-alfred-verification.md`): the same identity -
January 2023 nonfarm payrolls - first reported 155,073 (vintage 2023-02-03)
was revised to 154,773 by the 2024-04-01 vintage: an absolute change of
-300.0 thousand and a relative change of -0.001934572749608249 (the
annual benchmark revision). Both vintages are distinct stored identities.
In the same run, UNRATE for early 2023 did not change between the two
realtime windows examined (value 3.4 for 2023-01 at vintage 2023-04-01 in
both) - recorded as the honest observation it is, not as a claim about
revision behavior in general.

**The refresh layer is idempotent and failure-honest.** The S17 refresh
evidence (`evidence/S17/live-demo-output.txt`, captured 2026-09-10):
a live World Bank pass stored 66 points per economy for real GDP growth
across all ten economies (660 rows); a FRED series attempted without an
API key failed safely with reason `no_api_key` and stored nothing; the
recovery run with the key stored 866 points of FEDFUNDS spanning
1954-07-01 to 2026-08-01; an immediate re-run of the first pass stored
zero new rows and reported all 660 points unchanged. Every series outcome
is audit-logged per run with new/revised/unchanged counts.

**The full chain holds end to end.** The S18 live demonstration
(`evidence/S18/live-demo-output.txt`, captured 2026-09-24): ten economies
ingested with 66 annual points each (1960-01-01 to 2025-01-01, coverage
0.985 per series, publication gate passed) producing 63 derived
robust-standardized scores per economy; the served USA 2020 real-GDP-
growth row (-2.081375977796 percent per year, vintage 2026-09-24, evidence
`real`, source world_bank/NY.GDP.MKTP.KD.ZG) matched the stored row
byte-for-byte on all six provenance-carrying fields; the derived
robust-standardized score for USA 2020 (-8.91953625571653) served with its
formula reference and lineage; the S16 briefing leg served 660
observations, derived 650 facts with 10 named missing and 0 excluded, and
validated 30 of 30 built claims with no banned phrase in the rendered
document; and the 2020 pandemic-window case presents the observed 2020
panel values beside the documented episode (WHO's pandemic
characterization of 11 March 2020, live-verified and quoted in
`evidence/S18/live-verification.md`).

**Claims are validated, and the validation layer rejects.** The S16
evidence (`evidence/S16/live-demo-output.txt`, captured 2026-09-01):
20 of 20 level and change claims built from 110 served observations were
validated against the structured facts; a deliberately tampered value
claim was rejected with reason `value_mismatch`, and a causal sentence
was rejected by the banned-phrase filter (`causal_phrase`) - both
recorded in the persisted run (21 claims stored: 20 validated, 1
rejected). AI prose in this platform is a deterministic template over
validated claims only (`src/macropulse/briefing/prose.py`); rejected text
never reaches the document.

## Limitations

- **Panel size.** The panel is ten economies. Rank correlations are
  reported with n = 10 always; they describe this panel, not the world.
- **Point-in-time record.** Every finding is anchored to its capture date
  (2026-08-29 to 2026-09-24). Later vintages may differ; the platform
  stores all vintages, and this document does not track them beyond its
  date of record.
- **Missing components are named, not filled.** School-enrollment was not
  fetched in the RQ1 profiles shown (`component_not_fetched`); 29 of 31
  Chinese provinces have no verified record in the case study; the
  reserved `preliminary` and `estimated` quality grades are unused since
  no source exposes release-stage metadata.
- **Comparability is documented, not corrected.** The account-internet gap
  subtracts an adults-denominated share from a population-denominated
  share; the gender account gap is a conservative proxy (no male series
  in the locked catalog, and the all-adult average includes women);
  seasonal-adjustment regimes differ across sources; per-indicator
  comparability notes live in the catalog and are surfaced in the
  dashboard.
- **Alignment trades freshness for truth.** Lens profiles align to the
  latest period with all components observed - so Japan's digital profile
  is 2021, not 2024, and ZAF's labor profile is 2024, not 2025. Staler
  components are shown as the binding constraint rather than mixed.
- **Revision evidence is exemplary, not exhaustive.** The RQ4 finding
  demonstrates the vintage machinery on one revision chain and one
  no-revision observation across two realtime windows; it is not a survey
  of revision incidence.
- **External evidence is document-verified.** Case-study episodes and
  geography figures come from official documents, verified live and
  quoted verbatim; a scanned-image PDF that could not be
  machine-verified was excluded rather than recorded.
- **No causal, advisory, or forward-looking content.** The banned-phrase
  filter runs on briefing documents, and this report was written to the
  same standard and checked by the same machinery - the QA run recorded in
  `evidence/S19/qa-run.txt` shows the checks and their results.
- **Derivation guards bound the metrics.** robust_z requires window
  occupancy of at least 3 non-missing members and reports zero MAD as
  missing (`zero_scale`); rolling means require full windows; percent
  changes require positive non-zero bases; annualization requires whole
  compounding periods (12 % L == 0).

## Reproducibility appendix

The measured toolchain (interpreter, package versions, OS) is recorded in
`docs/EnvironmentRecord.md` and was appended to during this unit. The
test suite is the acceptance instrument: `python -m pytest` runs the full
suite including this report's own gate, and `python -m macropulse.smoke`
runs the platform smoke check.

**Repository layout for reproduction.** Scope in `src/macropulse/scope.py`;
catalog in `src/macropulse/catalog.py`; connectors, normalization, quality,
vintage control, metrics engine, lenses, case-study registries, briefing
layer, ops refresh, API service, and views under `src/macropulse/`. Unit
docs under `docs/` (for example `docs/TransformationRules.md`,
`docs/StandardizationRules.md`, `docs/QualityGovernance.md`); unit
evidence under `evidence/` (S01 through S19); the engineering contract in
`prompts/GlobalEngineeringContract.md`; decisions history in
`docs/decisions.md` and `docs/CoBuildLog.md`.

**Commands (from the repository root).**

```bash
# environment
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

# acceptance
.venv/bin/python -m pytest
.venv/bin/python -m macropulse.smoke

# lint
.venv/bin/ruff check .

# database migrations (Postgres connection via DATABASE_URL)
.venv/bin/alembic upgrade head

# query service + dashboard
PYTHONPATH=src .venv/bin/python -m uvicorn macropulse.api.main:app --port 8000
PYTHONPATH=src .venv/bin/streamlit run app/dashboard.py

# scheduled-refresh entrypoint (S17)
PYTHONPATH=src .venv/bin/python -m macropulse.ops.refresh --indicator gdp_real_growth
```

API keys and database URLs live only in gitignored `.env.local` and are
sourced into the process environment at run time; they are never printed
or committed. The FRED connector runs without a key in deterministic
fixture mode (evidence label `mocked`), so the suite reproduces without
secrets; live runs carry the `real` label and record their retrieval
times.

**This report's own QA.** `scripts/report-qa.py` runs the rendered-document
QA checks over this file - formula presentation (all fourteen typeset
formulas present in display math, exactly), citations (every cited
repository path exists on disk), structure (all contract sections), and
the claims boundary (the banned-phrase filter over the whole document) -
and writes the machine-readable result to `evidence/S19/qa-run.txt`
together with a deterministic standalone HTML rendering of this document
(MathJax typesetting) at `evidence/S19/report.html`. The checks are
implemented in `src/macropulse/report/qa.py` and tested in
`tests/test_report_qa.py`; the typeset registry is in
`src/macropulse/report/formulas.py` and tested in
`tests/test_report_formulas.py`. The acceptance gate for this deliverable
is the test `test_real_report_passes_qa`, which runs the full check set
over this document and requires an empty problem list.
