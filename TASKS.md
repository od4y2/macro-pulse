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
- [ ] S05 - World Bank and ILOSTAT Connectors
- [ ] S06 - Normalization Pipeline
- [ ] S07 - Quality, Missingness, and Vintage Control
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
