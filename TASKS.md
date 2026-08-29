# TASKS - Durable Ledger

## Initialization
- [x] INIT accepted: prepared starter created; do not rerun.
- [x] WORKSPACE_AUDIT accepted (2026-08-04): structure validated, no secrets, baseline tests green; evidence in `evidence/WORKSPACE_AUDIT/audit.md`. Open gap: Docker not installed (deferred to E01).

## Units
- [ ] E01 - Local Toolchain and Repository Safety
- [ ] E02 - Reproducible Dry Run and Recovery Practice
- [x] S01 - Research Scope and Claims Boundary (2026-08-19): countries, RQ1-RQ4, non-claims, evidence vocabulary locked in `src/macropulse/scope.py` + `docs/ResearchScope.md`; 16 new tests. Evidence: `evidence/S01/scope-lock.md`. Env defect logged for E01: local process re-applies `chflags hidden` to `.venv`, breaking editable install; workaround `PYTHONPATH=src`.
- [x] S02 - Indicator Catalog and Source Audit (2026-08-19): 12-indicator catalog with units/frequency/sources/fallback status in `src/macropulse/catalog.py`; 14 new tests (34/34 total). 7 source codes marked unverified for S04/S05 live confirmation (2 explicit TBD-S05). Evidence: `evidence/S02/catalog-audit.md`.
- [x] S03 - Architecture and Database Contract (2026-08-19): 11-table PostgreSQL schema (ORM + Alembic migration `bcc78be651f0` applied to live docker-compose DB), API contract schemas, data flow/module boundaries in `docs/DatabaseContract.md`; 18 new tests (52/52 total, 6 live-DB). Docker gap closed (29.7.2). Evidence: `evidence/S03/db-contract.md`.
- [x] S04 - FRED Connector Vertical Slice (2026-08-19): `FredConnector` (live + deterministic no-key modes, shared parser), raw-store persistence, 18 new tests (70/70 total) incl. httpx.MockTransport live-path tests and 3 live-DB persistence tests. No live FRED call made (no key) - catalog FRED codes still unverified live. Evidence: `evidence/S04/fred-slice.md`.
- [x] S05 - World Bank and ILOSTAT Connectors (2026-08-19): WorldBankConnector + IlostatConnector (live, no key), shared connector base, source-generic raw persistence; live audit 14/14 catalog codes OK (`scripts/audit_sources.py`) with 2 catalog corrections (g20.any, DF_SDG_0852_SEX_AGE_RT/DF_EIP_NEET_SEX_RT). 24 new tests (94/94). Evidence: `evidence/S05/`.
- [x] S06 - Normalization Pipeline (2026-08-19): pure `normalize_series()` + `persist_normalized()` in `src/macropulse/pipeline/normalize.py` unifying country panel, periods, canonical units (values never converted), median-gap frequency inference, per-series seasonal adjustment, per-point vintage, explicit missingness; rules doc `docs/NormalizationRules.md`; WB/ILOSTAT vintage=period bug fixed to retrieval-date snapshot semantics; 23 new tests (117/117). Evidence: `evidence/S06/`.
- [x] S07 - Quality, Missingness, and Vintage Control (2026-08-29): `src/macropulse/quality/` (assessment/missingness/vintage) - closed grade vocabulary (`flagged`>`ungraded`>`revised`>`official`; `preliminary`/`estimated` reserved, never fabricated), closed flag set (`missing_value`, `series_gap`, `vintage_precedes_period`), non-fabricating missingness reports, revision history + deltas (`relative=None` on zero base), append-only flags; FRED ALFRED realtime windows live-verified incl. a real -300K PAYEMS revision chain; normalize duplicate check rekeyed to (period, vintage); 42 new tests (159/159). Evidence: `evidence/S07/`.
- [ ] S08 - Time-Series Transformations
- [ ] S09 - Robust Standardization and Coverage
- [ ] S10 - Labor Slack and Youth Transition Lens
- [ ] S11 - Digital Reach and Inclusion Gap
- [ ] S12 - Payment Resilience and Healthcare Case Study
- [ ] S13 - FastAPI Query Service
- [ ] S14 - Streamlit Country and Comparison Views
- [ ] S15 - Visual Explanation and Quality Labels
- [ ] S16 - Structured AI Briefing
- [ ] S17 - Scheduling, Logging, and Operational Recovery
- [ ] S18 - End-to-End Integration and Historical Case
- [ ] S19 - Research Report and Methodology Publication
- [ ] S20 - Release, Demo, and Portfolio Defense
- [ ] C01 - Integration Failure Reserve
- [ ] C02 - Deployment and Release Reserve

## Evidence and issues
Append only. Record actual results, blockers, decisions, and rollback checkpoints.
