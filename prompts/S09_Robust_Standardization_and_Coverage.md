# S09 - Robust Standardization and Coverage

## Role and bounded context
Act as the implementation partner for this single MacroPulse InnovationLab unit.

## Read first
- `README.md`
- `TASKS.md`
- `STATUS.md`
- `SESSION_STATE.md`
- `docs/AuthoritativePlan.md`
- `docs/Architecture.md`
- `docs/DataGovernance.md`
- `prompts/GlobalEngineeringContract.md`
- latest `docs/decisions.md` and `docs/CoBuildLog.md`

## Prior-state check
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S09` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Implement fixed-window scaling, direction handling, coverage, and publication gates.

## Allowed changes
Modify only files directly needed for this unit, its tests, documentation, evidence, and persistent state. State the intended files before editing.

## Implementation requirements
- Build the smallest complete and testable vertical change.
- Preserve source metadata, units, dates, quality, and limitations.
- Use deterministic mocked/no-key behavior when live external services are not required.
- Add or update tests for normal, boundary, missing, and invalid cases.
- Keep formulas and methodology traceable; never use undocumented magic constants.

## Tests and manual checks
Run the smallest relevant tests, then `python -m pytest` and `python -m macropulse.smoke` when available. Inspect outputs manually for provenance, labels, and claims boundaries.

## Acceptance criteria
- The objective is demonstrably complete.
- Tests and manual checks have truthful evidence.
- No secret, fabricated result, hidden missingness, or unsupported claim is introduced.
- `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`, decisions, and co-build log are updated without deleting history.

## Do not do
Do not implement future units, rewrite unrelated architecture, overwrite state history, insert real credentials, invent data, or claim live/deployed success without evidence.

## Evidence and checkpoint
Save evidence under `evidence/S09/`. Commit only intended paths with a `S09: Robust Standardization and Coverage` message. Keep the last verified rollback point.

## Stop condition
Stop when `S09` passes acceptance. Identify `S10` as the next unit but do not implement it.
