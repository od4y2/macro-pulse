# S16 design notes

## Intended files (stated before editing; as executed)

- NEW `src/macropulse/briefing/facts.py` — validated facts JSON
  contract (real/missing/excluded partition; construction gates)
- NEW `src/macropulse/briefing/claims.py` — atomic claim models,
  deterministic builder, adjudication with closed rejection vocabulary
- NEW `src/macropulse/briefing/prose.py` — document assembly +
  banned-phrase rejection tests
- NEW `src/macropulse/briefing/run.py` — briefing_runs/briefing_claims
  persistence
- NEW `src/macropulse/briefing/__init__.py`, NEW `tests/test_briefing.py`
  (35 tests), NEW `docs/AIBriefing.md`
- NEW `evidence/S16/` (live-demo-script.py, live-demo-output.txt,
  acceptance-run.txt, design-notes.md)
- UPDATED `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`,
  `docs/decisions.md`, `docs/CoBuildLog.md`

## Design decisions

- **The AI boundary is enforced as machinery, not as prompt
  discipline.** Architecture §5 lets an LLM summarize validated facts
  but forbids it from calculating source-of-truth metrics, inventing
  causes, hiding missingness, or advising. This unit implements that
  boundary as code: prose derives only from a validated JSON contract
  (`BriefingFacts`), every statement is an atomic claim adjudicated
  against that JSON, and any text must pass a banned-phrase check. No
  LLM is called (no key exists in this environment) - the deterministic
  template generator is the no-key default (the S04 connector pattern),
  and `briefing_runs.model` records `deterministic-template` so the
  audit row says so honestly. An LLM attached later is just another
  prose source behind the same validators.
- **Rejection is the unit's core feature, not an error path.** A closed
  8-reason vocabulary (fact_not_found, value_mismatch, evidence_not_real,
  missing_value_claimed, citation_missing, citation_mismatch,
  availability_contradicted, reason_mismatch), each exercised by a test;
  plus the 4-class banned-phrase layer (causal/advice/forecast/merit).
  Rejected claims are persisted with validated=False - the audit trail
  records what was refused, not only what passed.
- **Non-real evidence is structurally not a fact.** `from_observations`
  partitions mocked/synthetic/cached/external observations into
  `excluded` before any claim exists, so a claim about them fails as
  `evidence_not_real` and the Limitations section counts them. A
  mocked value can never be stated as observed because there is no
  code path that treats it as a fact.
- **Change claims only across consecutive periods.** A "up from" /
  "down from" sentence across a gap (2023 → 2025 with 2024 absent)
  would mislead about timing, so the builder emits no change claim
  unless the periods are exactly one frequency step apart
  (FREQUENCY_STEP_MONTHS, same as S15's freshness arithmetic).
- **The disclaimer must pass its own gate.** The first draft's
  Limitations footer said "No forecasts ... no investment advice" -
  which trips the banned-phrase check on our own document (forecast\w*,
  investment advice). The mechanical check is the enforcement layer, so
  it gets no exemption for good intentions: the wording was changed to
  pass ("no forward-looking statements ... no financial guidance").
  A disclaimer using the banned literals would be indistinguishable,
  to the check, from prose committing them.
- **The document is pure** (no clock reads, no I/O - the S15 as-of
  discipline): the run row records time; the document does not.
- **Reuse, not duplication:** the live demo fetches facts via the
  existing typed `QueryServiceClient` (S14) over HTTP - the briefing is
  a second consumer of the read-only service per the DatabaseContract
  data flow, and the client is the repo's one typed HTTP path to it.
  The package itself is HTTP-free (pure functions + ORM writes).

## Live-demo notes (live-demo-output.txt)

- 110 real observations (10 economies × 11 years, world_bank
  NY.GDP.MKTP.KD.ZG) fetched from the running service → 20 claims
  (10 level + 10 change), all validated.
- Rejection demonstrations: a tampered value claim → `value_mismatch`;
  a causal sentence → `causal_phrase`.
- Rendered document passes `check_prose` with zero findings; values at
  full precision (e.g. BRA 2025: 2.2857464902475, down from
  3.41931516501906); every statement carries source, vintage,
  evidence, quality.
- Run 1 persisted to the dev DB: 21 claim rows (20 validated,
  1 rejected), evidence_refs JSON round-tripped.

## Errors found and fixed during the unit (truthful record)

- Ruff (I001/RUF022/RUF100) on the first pass — import and `__all__`
  ordering, plus stale `noqa: ANN001` directives (ANN001 is not
  enabled in this repo's ruff config) → auto-fixed.
- Demo script: `make_session_factory()` called without its required
  `engine` argument → `make_session_factory(make_engine())`; the first
  demo run failed at that line (output captured then overwritten by
  the fixed rerun — exit code was 1, now 0).
- FINAL-VERIFICATION catch (same class as S15's): the demo script had
  an F841 (walrus `rejection` never used) and a `ruff format` rewrap;
  fixed, the demo re-run (the dev DB now honestly holds TWO briefing
  runs — both audit records of real runs), and the acceptance run
  regenerated from the final file states.
- ExcludedObservation initially lacked vintage/source fields, which
  made a ref to an excluded observation fail as citation_mismatch
  instead of the truthful evidence_not_real — caught while wiring
  the identity index; fixed by carrying the full identity on the
  excluded record.

## Deviations from the prompt

None.
