# S01 Evidence - Research Scope and Claims Boundary (2026-08-19)

## Prior-state check
- Previous unit: WORKSPACE_AUDIT accepted 2026-08-04. Confirmed via TASKS.md /
  STATUS.md / SESSION_STATE.md. S01 is the only active unit.
- Git checkpoint at unit start: `08852af` (rollback point).
- Working tree was not clean: modified `.gitignore` plus three untracked LLM
  setup scripts. Committed the `.gitignore` change as prior-state hygiene
  (`269dbb4`); the setup scripts are now gitignored and remain untracked by
  design (local tooling, one contains an API key - flagged to the user for
  relocation/rotation; not committed).

## Environment drift found and handled (truthful record)
- `python -m macropulse.smoke` FAILED at unit start with
  `ModuleNotFoundError: No module named 'macropulse'`, contradicting the
  audit-era evidence. Pytest still passed only because `pyproject.toml` sets
  `pythonpath=["src"]`, which masked the breakage.
- Root cause: the editable-install `.pth`
  (`.venv/lib/python3.13/site-packages/__editable__.macropulse-0.1.0.pth`)
  carries the macOS BSD `hidden` file flag, and this Anaconda Python 3.13.14
  build skips hidden `.pth` files at startup (supply-chain hardening).
- An unknown local process re-applies `chflags hidden` to `.venv` contents
  within seconds of removing it (confirmed twice; prior session's
  `.claude/settings.local.json` permissions show this was fought before).
  Culprit not identified; recorded as an open defect for E01.
- Actions taken: `pip install -e '.[dev]'` (repair), `chflags nohidden`
  attempts (temporary only). Deterministic workaround adopted for this unit:
  `PYTHONPATH=src python -m macropulse.smoke`. Documented in
  `docs/EnvironmentRecord.md`.

## Decisions locked (student choices, confirmed in session)
- Country panel: balanced global set (USA, CHN, JPN, DEU, GBR, IND, BRA, KOR,
  ZAF, MEX).
- Research questions: all four lenses (RQ1-RQ4 as listed in
  `docs/ResearchScope.md`), with RQ3 scoped as a case study.

## Commands and actual results
- `.venv/bin/python -m pytest -q` -> 20 passed (4 baseline + 16 new scope tests).
- `PYTHONPATH=src .venv/bin/python -m macropulse.smoke` -> passed.
- `ruff check src/macropulse/scope.py tests/test_scope.py` -> All checks passed.

## Changed files
- New: `src/macropulse/scope.py`, `tests/test_scope.py`, `docs/ResearchScope.md`,
  `evidence/S01/scope-lock.md`.
- Updated: `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`, `docs/decisions.md`,
  `docs/CoBuildLog.md`, `docs/EnvironmentRecord.md`.

## Limitations
- Scope is documentation + invariant tests only; no data, connectors, or
  database were touched. Docker still absent (E01 gap, unchanged).
- The `.venv` hidden-flag defect is worked around, not resolved.

## Rollback checkpoint
- Pre-unit: `08852af`. This unit's commit follows `269dbb4` (state hygiene).
