# Co-Build Log

Append student decisions, AI assistance, manual verification, and learning evidence by unit.

## S01 (2026-08-19)
- Student decisions: selected the balanced global ten-economy panel and confirmed all four research-question lenses (RQ1-RQ4); RQ3 scoped as a case study.
- AI assistance: drafted `src/macropulse/scope.py` (locked scope module), `tests/test_scope.py` (16 tests: normal/boundary/missing/invalid), `docs/ResearchScope.md`, and evidence.
- Manual verification: student reviewed concern list (plaintext API key in local setup scripts, uncommitted .gitignore, broken editable install) before unit start.
- Learning evidence: diagnosed why `python -m macropulse.smoke` failed while pytest passed (Anaconda Python 3.13.14 skips `.pth` files carrying the macOS `hidden` BSD flag; a local process re-applies the flag to `.venv`). Recorded as an E01 defect with `PYTHONPATH=src` workaround.

## S02 (2026-08-19)
- Student decisions: approved moving to S02 after reviewing S01 handover concerns; approved the module/source-system mapping (WB primary cross-panel, FRED US-first, ILOSTAT youth fallback).
- AI assistance: drafted `src/macropulse/catalog.py` (12 indicators + validation), `src/macropulse/catalog_report.py`, `tests/test_catalog.py`, `docs/IndicatorCatalog.md`, evidence.
- Manual verification: catalog report inspected for provenance, verification labels, and claims boundaries; 7 unverified codes surfaced explicitly rather than hidden.
- Learning evidence: the no-whitespace source-code validation rule caught 2 annotated codes mid-unit, demonstrating tests-as-contract; TBD placeholders used instead of inventing uncertain API codes.

## S03 (2026-08-19)
- Student decisions: installed Docker manually (29.7.2); reaffirmed PostgreSQL-only (local Docker + cloud for Vercel target).
- AI assistance: drafted `src/macropulse/db/` (engine/session + 11 ORM entities), Alembic scaffold + initial migration, `src/macropulse/api/schemas.py` contract, 18 tests, `docs/DatabaseContract.md`, evidence.
- Manual verification: `\dt` output inspected (all 11 tables + alembic_version); migration applied and downgrade path documented.
- Learning evidence: governance rules expressed as executable schema constraints (CHECK missing_reason, native enums, unique observation identity) and caught by live-DB integration tests rather than prose-only rules.

## S04 (2026-08-19)
- Student decisions: proceed with S04 in mocked/no-key mode (`.env.local` has placeholder FRED key only).
- AI assistance: drafted `src/macropulse/connectors/{__init__,fred,persist}.py`, 18 tests, shared DB fixture in `tests/conftest.py`, evidence.
- Manual verification: reviewed fixture values are obviously-round and labelled `mocked`; confirmed no test touches the network (MockTransport) and no live API call was claimed.
- Learning evidence: httpx.MockTransport lets live-mode code paths be tested deterministically; "." missingness handling demonstrates "no hidden missingness" as code, not prose.
