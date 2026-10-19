# MacroPulse — Portfolio and Defense Package

This document is the portfolio entry point for MacroPulse: what the project is,
what it claims, where every claim's evidence lives, how to run it, and — stated
plainly — what is and is not deployed. It is written under the same contract as
the rest of the repository: no fabricated values, citations, results,
deployment status, or causal claims.

## 1. What MacroPulse is

MacroPulse is a global macroeconomic monitoring platform built around one
discipline: **every number is traceable to a source, and every limitation is
named.** It ingests official statistics (World Bank, FRED), normalizes them
into a governed, versioned store, derives metrics through registered formulas
with per-point lineage, serves them through a typed query API, renders them in
a Streamlit dashboard with explicit missingness and quality labels, and
generates a structured briefing whose every sentence is validated against the
store before it is allowed to exist.

The research framing is the analysis of **statistical blind spots** — places
where official data is revised, missing, or structurally unable to answer the
question being asked of it. The China year-end medical-insurance suspension
case (S12) is the emblem: a real, recurring 48-hour window in which a
platform processes rollover that no catalog frequency can observe.

### Research questions (locked in S01, `docs/ResearchScope.md`)

- **RQ1** — How do labor-market slack measures and youth transition outcomes
  relate across the panel, and where do vintages disagree?
- **RQ2** — Where do digital reach and digital inclusion diverge — who is
  online but excluded from digital payments?
- **RQ3** — What does the payment-resilience lens and the China healthcare
  case show about exposure to institutional processing windows?
- **RQ4** — How visibly do data revisions propagate through the store, and
  can a user see exactly which vintage a number came from?

### Non-claims (enforced, not promised)

No investment advice, no price targets, no causal claims unsupported by
evidence, no fabricated release dates. The S16 banned-phrase filter enforces
this on generated prose (`src/macropulse/briefing/prose.py`), and the S19 QA
gate enforces it on the published report (`src/macropulse/report/qa.py`) with
**no exemption** — the report's own NON_CLAIMS section was reworded when it
first tripped the filter.

## 2. Architecture in one paragraph

Connectors (`src/macropulse/connectors/`) fetch from World Bank, FRED, and
ILOSTAT with retry policies; the normalization pipeline
(`src/macropulse/pipeline/normalize.py`) writes raw payloads and canonical
observations with per-point vintage dates into a 12-table PostgreSQL schema
(`docs/DatabaseContract.md`, Alembic-migrated). Quality and missingness
(`src/macropulse/quality/`) grade and flag without inventing values; metrics
(`src/macropulse/metrics/`) derive registered transformations with
observation-id lineage; gates (`evaluate_gate`) decide publication with a
closed reason vocabulary. Lenses (`src/macropulse/lenses/`) compose RQ1–RQ3
analyses as pure functions. The FastAPI query service (`src/macropulse/api/`)
serves typed, paginated endpoints; the Streamlit dashboard (`app/dashboard.py`)
is a thin HTTP client over that service — it never touches the database
directly. The briefing layer (`src/macropulse/briefing/`) builds atomic claims
from served facts, adjudicates them against a closed rejection vocabulary, and
persists the audit trail. Ops (`src/macropulse/ops/`) schedules, logs (JSONL),
and recovers refresh runs with per-series isolation.

## 3. Unit-by-unit evidence index

Every unit below links to its evidence directory; the full narrative for each
is in `TASKS.md` (the durable ledger, updated-not-replaced by contract).

| Unit | What it delivered | Evidence |
|---|---|---|
| S01 | Research scope, 10-economy panel, RQ1–RQ4, evidence vocabulary | `evidence/S01/scope-lock.md` |
| S02 | 12-indicator catalog with units, frequency, source codes | `evidence/S02/catalog-audit.md` |
| S03 | 11-table schema + API contract (schemas pinned, byte-verified later in S13) | `evidence/S03/db-contract.md` |
| S04 | FRED connector vertical slice (live + deterministic no-key modes) | `evidence/S04/fred-slice.md` |
| S05 | World Bank + ILOSTAT connectors; live audit 14/14 catalog codes | `evidence/S05/` |
| S06 | Normalization: canonical units, vintages, explicit missingness | `evidence/S06/` |
| S07 | Quality grades, missingness, revision chains (live ALFRED window check) | `evidence/S07/` |
| S08 | Transformations + derived-metric engine with lineage | `evidence/S08/` |
| S09 | Robust standardization, panel coverage, publication gates | `evidence/S09/` |
| S10 | Labor slack / youth transition lens (RQ1) | `evidence/S10/` |
| S11 | Digital reach / inclusion gap lens (RQ2) | `evidence/S11/` |
| S12 | Payment resilience + China healthcare case (RQ3) | `evidence/S12/` |
| S13 | FastAPI query service serving the pinned contract | `evidence/S13/` |
| S14 | Streamlit country/comparison/provenance views | `evidence/S14/` |
| S15 | Visual quality labels + freshness (as-of driven) | `evidence/S15/` |
| S16 | Structured AI briefing from validated claims | `evidence/S16/` |
| S17 | Scheduling, JSONL logging, operational recovery (111-series planner) | `evidence/S17/` |
| S18 | End-to-end integration proof + 2020 historical case + visual language | `evidence/S18/` |
| S19 | Published research report under an enforceable QA gate | `evidence/S19/` |
| S20 | Release gates, production demo rehearsal, this portfolio | `evidence/S20/` |

The S18 demo is the chain-of-custody proof: ingest → derive → serve → render →
brief → case, six legs all through production entry points on a disposable
database, byte-verified between store and API. The S20 rehearsal repeats the
chain against the **production** database (see §5).

## 4. Verification posture

- **Tests**: the suite is green at every unit boundary; S19 closed at 598
  passing (S20 adds release-sweep DB integration tests; the acceptance run's
  count is recorded in `evidence/S20/acceptance-run.txt`).
- **QA gates as code**: the published report must pass its own validator
  (`scripts/report-qa.py` — formula presence, cited-path existence, section
  structure, banned-phrase filter with no exemption); the acceptance test
  `test_real_report_passes_qa` makes a failing report fail CI.
- **No-fabrication machinery, not policy**: missing values carry closed
  reason codes (`missing_value`, `series_gap`, `insufficient_history`,
  `zero_scale`, ...); the API serves `value=null` with a reason rather than
  an invented number; the briefing rejects claims outside the fact base with
  named reasons; the case-study registry refuses records without citations.
- **Label discipline**: every observation carries an evidence label
  (`real` / `external` / `cached` / `mocked` / `synthetic`); the production
  store contains only `real` (observations) and `external` (case-study
  episodes) data.

## 5. Deployment status — stated truthfully

**Production database: live.** Neon (project `blue-rice-74949654`, branch
`production`, database `neondb`), migrated and verified from the local stack
on 2026-09-18 (12-table parity, row counts, md5 spot checks). The S20 release
pass runs the full-catalog refresh (111 series) and the release sweep (gate +
derive) against it; the audit rows (`refresh_runs`) are in the database
itself.

**Application hosting: prepared, cloud deployment pending one user action.**
The curated `deploy` branch (orphan — no curriculum history; public repo
`od4y2/macro-pulse`) carries the app, the cloud runtime bridge
(`st.secrets` → env, in-process API thread), and install instructions. What
remains is configuration only possible from the Streamlit Community Cloud
console: point the app at branch `deploy`, main file `app/dashboard.py`, and
set the secret `DATABASE_URL` to the Neon connection string. Until that is
done and confirmed on the live URL, **no live-deployment claim is made
anywhere in this repository.** The local half of the rehearsal (secrets
bridge + AppTest render) is verified in `evidence/S18/` and repeated against
production in `evidence/S20/demo-rehearsal.txt`.

**Scheduled refresh: documented, not yet scheduled.** The refresh loop
(`macropulse.ops.refresh --daemon`, daily 06:00 UTC) and a GitHub Actions
cron pattern are documented in `docs/OpsRunbook.md`; enabling the cloud cron
with repo secrets is part of the deployment reserve (C02).

## 6. How to run it

Local prerequisites: Docker (Postgres via docker-compose), Python 3.12 venv
(`pip install -e ".[dev]"` or `pip install .`), `.env.local` with
`DATABASE_URL` (local Postgres), `FRED_API_KEY` (optional — connectors run in
deterministic no-key mode without it), and `NEON_DATABASE_URL` when targeting
production. Note the known environment defect (E01): the local `.venv` gets
re-hidden by the launcher, so direct module invocation needs `PYTHONPATH=src`
(pytest is unaffected — `pythonpath` is pinned in `pyproject.toml`).

```bash
# database (local docker Postgres)
docker compose up -d

# ingest one manual refresh cycle (111 series)
PYTHONPATH=src .venv/bin/python -m macropulse.ops.refresh --trigger manual

# release gates: evaluate publication gates for every planned series and
# materialize robust_z5 for the published ones (idempotent re-runs)
PYTHONPATH=src .venv/bin/python scripts/release-report.py

# query service
PYTHONPATH=src .venv/bin/python -m uvicorn macropulse.api.main:app --port 8000

# dashboard (separate terminal; it talks to the service over HTTP)
.venv/bin/python -m streamlit run app/dashboard.py

# full test suite + smoke
.venv/bin/python -m pytest
PYTHONPATH=src .venv/bin/python -m macropulse.smoke

# report QA (validates docs/ResearchReport.md end to end)
PYTHONPATH=src .venv/bin/python scripts/report-qa.py
```

Against production, the same commands take `--db-url` (or `DATABASE_URL`)
with the Neon URL — scheme rewritten to `postgresql+psycopg://`; see the
invocation blocks recorded in `evidence/S20/`.

## 7. Reading map for a reviewer

1. `docs/ResearchReport.md` — the findings, formulas, and limitations (the
   deliverable; QA-gated by S19 machinery).
2. `TASKS.md` — the durable ledger: every unit's actual outcome, including
   defects found and worked around, in order.
3. `docs/decisions.md` + `docs/CoBuildLog.md` — the decision log and the
   build narrative.
4. `evidence/S20/` — the release evidence: production refresh, release
   gates, the 31-province case-study verification, the demo rehearsal, and
   this package.
