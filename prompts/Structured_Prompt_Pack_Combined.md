# Structured Prompt Pack

Use the global contract, then paste only the current unit prompt. The prepared starter is initialized; run the workspace audit first and do not rerun INIT.



---

# C01 - Integration Failure Reserve

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `C01` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Use only for unresolved connector, database, API, or UI integration defects.

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
Save evidence under `evidence/C01/`. Commit only intended paths with a `C01: Integration Failure Reserve` message. Keep the last verified rollback point.

## Stop condition
Stop when `C01` passes acceptance. Identify `C02` as the next unit but do not implement it.


---

# C02 - Deployment and Release Reserve

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `C02` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Use only for deployment, clean-clone, release-candidate, or final recovery defects.

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
Save evidence under `evidence/C02/`. Commit only intended paths with a `C02: Deployment and Release Reserve` message. Keep the last verified rollback point.

## Stop condition
Stop when `C02` passes acceptance. Identify `NONE` as the next unit but do not implement it.


---

# E01 - Local Toolchain and Repository Safety

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `E01` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Install/verify Python, Git, Docker Desktop and coding assistant; establish secret and Git safety.

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
Save evidence under `evidence/E01/`. Commit only intended paths with a `E01: Local Toolchain and Repository Safety` message. Keep the last verified rollback point.

## Stop condition
Stop when `E01` passes acceptance. Identify `E02` as the next unit but do not implement it.


---

# E02 - Reproducible Dry Run and Recovery Practice

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `E02` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Run PostgreSQL, install dependencies, execute smoke tests, and practise checkpoint/resume.

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
Save evidence under `evidence/E02/`. Commit only intended paths with a `E02: Reproducible Dry Run and Recovery Practice` message. Keep the last verified rollback point.

## Stop condition
Stop when `E02` passes acceptance. Identify `S01` as the next unit but do not implement it.


---

# Global Engineering Contract

Implement only the active unit. Read authoritative and state files first. Preserve the baseline and update rather than replace `TASKS.md`. Keep secrets outside the repository. Label real, external, cached, mocked, and synthetic data. Never fabricate values, citations, results, deployment status, or causal claims. Run focused tests, then smoke tests. Save truthful evidence under `evidence/<UnitID>/`. Report changed files, commands, actual results, limitations, and rollback checkpoint. Update state files, commit, and stop before the next unit.


---

# INIT - Project Initialization

This prompt documents how an empty repository would be initialized. The packaged starter is already initialized, so mark INIT accepted and **do not execute this prompt** against the prepared starter.

Create the canonical structure, placeholder-only configuration, control files, baseline tests, and evidence folders. Never add real credentials or claim external services were tested.


---

# S01 - Research Scope and Claims Boundary

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S01` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Lock research questions, non-claims, countries, modules, and evidence vocabulary.

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
Save evidence under `evidence/S01/`. Commit only intended paths with a `S01: Research Scope and Claims Boundary` message. Keep the last verified rollback point.

## Stop condition
Stop when `S01` passes acceptance. Identify `S02` as the next unit but do not implement it.


---

# S02 - Indicator Catalog and Source Audit

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S02` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Define indicators, units, frequency, source, comparability, and fallback status.

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
Save evidence under `evidence/S02/`. Commit only intended paths with a `S02: Indicator Catalog and Source Audit` message. Keep the last verified rollback point.

## Stop condition
Stop when `S02` passes acceptance. Identify `S03` as the next unit but do not implement it.


---

# S03 - Architecture and Database Contract

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S03` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Lock data flow, tables, module boundaries, and API contracts.

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
Save evidence under `evidence/S03/`. Commit only intended paths with a `S03: Architecture and Database Contract` message. Keep the last verified rollback point.

## Stop condition
Stop when `S03` passes acceptance. Identify `S04` as the next unit but do not implement it.


---

# S04 - FRED Connector Vertical Slice

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S04` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Implement one traceable connector path with mocked tests.

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
Save evidence under `evidence/S04/`. Commit only intended paths with a `S04: FRED Connector Vertical Slice` message. Keep the last verified rollback point.

## Stop condition
Stop when `S04` passes acceptance. Identify `S05` as the next unit but do not implement it.


---

# S05 - World Bank and ILOSTAT Connectors

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S05` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Add structural and labor-market sources with metadata preservation.

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
Save evidence under `evidence/S05/`. Commit only intended paths with a `S05: World Bank and ILOSTAT Connectors` message. Keep the last verified rollback point.

## Stop condition
Stop when `S05` passes acceptance. Identify `S06` as the next unit but do not implement it.


---

# S06 - Normalization Pipeline

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S06` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Unify dates, country codes, units, frequency, and seasonal-adjustment metadata.

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
Save evidence under `evidence/S06/`. Commit only intended paths with a `S06: Normalization Pipeline` message. Keep the last verified rollback point.

## Stop condition
Stop when `S06` passes acceptance. Identify `S07` as the next unit but do not implement it.


---

# S07 - Quality, Missingness, and Vintage Control

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S07` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Implement validation flags, revision history, and non-fabricating missing-data rules.

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
Save evidence under `evidence/S07/`. Commit only intended paths with a `S07: Quality, Missingness, and Vintage Control` message. Keep the last verified rollback point.

## Stop condition
Stop when `S07` passes acceptance. Identify `S08` as the next unit but do not implement it.


---

# S08 - Time-Series Transformations

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S08` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Implement YoY, MoM, percentage-point, annualization, and rolling trend calculations.

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
Save evidence under `evidence/S08/`. Commit only intended paths with a `S08: Time-Series Transformations` message. Keep the last verified rollback point.

## Stop condition
Stop when `S08` passes acceptance. Identify `S09` as the next unit but do not implement it.


---

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


---

# S10 - Labor Slack and Youth Transition Lens

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S10` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Build transparent component-first labor lens and methodology tests.

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
Save evidence under `evidence/S10/`. Commit only intended paths with a `S10: Labor Slack and Youth Transition Lens` message. Keep the last verified rollback point.

## Stop condition
Stop when `S10` passes acceptance. Identify `S11` as the next unit but do not implement it.


---

# S11 - Digital Reach and Inclusion Gap

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S11` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Build two-dimensional digital inclusion analysis.

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
Save evidence under `evidence/S11/`. Commit only intended paths with a `S11: Digital Reach and Inclusion Gap` message. Keep the last verified rollback point.

## Stop condition
Stop when `S11` passes acceptance. Identify `S12` as the next unit but do not implement it.


---

# S12 - Payment Resilience and Healthcare Case Study

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S12` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Implement the payment profile and bounded China healthcare geography case.

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
Save evidence under `evidence/S12/`. Commit only intended paths with a `S12: Payment Resilience and Healthcare Case Study` message. Keep the last verified rollback point.

## Stop condition
Stop when `S12` passes acceptance. Identify `S13` as the next unit but do not implement it.


---

# S13 - FastAPI Query Service

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S13` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Expose typed, paginated, filterable data and methodology endpoints.

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
Save evidence under `evidence/S13/`. Commit only intended paths with a `S13: FastAPI Query Service` message. Keep the last verified rollback point.

## Stop condition
Stop when `S13` passes acceptance. Identify `S14` as the next unit but do not implement it.


---

# S14 - Streamlit Country and Comparison Views

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S14` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Create country, comparison, and provenance views.

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
Save evidence under `evidence/S14/`. Commit only intended paths with a `S14: Streamlit Country and Comparison Views` message. Keep the last verified rollback point.

## Stop condition
Stop when `S14` passes acceptance. Identify `S15` as the next unit but do not implement it.


---

# S15 - Visual Explanation and Quality Labels

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S15` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Refine charts, freshness labels, quality badges, and limitations.

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
Save evidence under `evidence/S15/`. Commit only intended paths with a `S15: Visual Explanation and Quality Labels` message. Keep the last verified rollback point.

## Stop condition
Stop when `S15` passes acceptance. Identify `S16` as the next unit but do not implement it.


---

# S16 - Structured AI Briefing

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S16` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Generate prose only from validated JSON with citations and rejection tests.

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
Save evidence under `evidence/S16/`. Commit only intended paths with a `S16: Structured AI Briefing` message. Keep the last verified rollback point.

## Stop condition
Stop when `S16` passes acceptance. Identify `S17` as the next unit but do not implement it.


---

# S17 - Scheduling, Logging, and Operational Recovery

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S17` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Add scheduled updates, logs, retry boundaries, and safe failure behavior.

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
Save evidence under `evidence/S17/`. Commit only intended paths with a `S17: Scheduling, Logging, and Operational Recovery` message. Keep the last verified rollback point.

## Stop condition
Stop when `S17` passes acceptance. Identify `S18` as the next unit but do not implement it.


---

# S18 - End-to-End Integration and Historical Case

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S18` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Validate one full evidence chain and historical case.

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
Save evidence under `evidence/S18/`. Commit only intended paths with a `S18: End-to-End Integration and Historical Case` message. Keep the last verified rollback point.

## Stop condition
Stop when `S18` passes acceptance. Identify `S19` as the next unit but do not implement it.


---

# S19 - Research Report and Methodology Publication

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S19` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Complete report, formula presentation, limitations, and reproducibility appendix.

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
Save evidence under `evidence/S19/`. Commit only intended paths with a `S19: Research Report and Methodology Publication` message. Keep the last verified rollback point.

## Stop condition
Stop when `S19` passes acceptance. Identify `S20` as the next unit but do not implement it.


---

# S20 - Release, Demo, and Portfolio Defense

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
Confirm the previous unit is accepted, the repository state is clean or truthfully documented, and `S20` is the only active unit. Record the current Git checkpoint and run the currently passing baseline checks.

## Objective
Run release gates, rehearse demo, and package portfolio evidence.

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
Save evidence under `evidence/S20/`. Commit only intended paths with a `S20: Release, Demo, and Portfolio Defense` message. Keep the last verified rollback point.

## Stop condition
Stop when `S20` passes acceptance. Identify `C01` as the next unit but do not implement it.


---

# Workspace Audit - Run Once

Read `README.md`, `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`, `docs/AuthoritativePlan.md`, `docs/EnvironmentRecord.md`, and `prompts/GlobalEngineeringContract.md`. Confirm the prepared starter is initialized, INIT is accepted, no secrets exist, baseline tests run, and S01 is the only next implementation unit. Record actual commands and results in `evidence/WORKSPACE_AUDIT/`, update state files, commit, and stop. Do not implement S01.
