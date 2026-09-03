# Structured AI Briefing (S16)

The briefing layer generates prose **only from validated JSON with
citations, under rejection tests**. Package: `src/macropulse/briefing/`.

## Pipeline

```
S13 query service  →  BriefingFacts (validated JSON)  →  build_claims
                       (real / missing / excluded         (deterministic templates)
                        partition)                              ↓
briefing_runs +  ←  record_briefing_run  ←  adjudicate_all  ←  Claim
briefing_claims       (persistence)        (accept / REJECT     (atomic, cited)
                                            with closed reasons)
                                                 ↓
                            render_briefing  +  check_prose
                            (document,          (banned-phrase
                             rejection report)   rejection layer)
```

1. **Facts** (`facts.py`): `BriefingFacts.from_observations()` consumes
   observation dicts exactly as served by the query service
   (`ObservationOut` shape; fetch with `latest_vintage=True`) and
   partitions them: real-evidence values are `facts` (the only things a
   briefing may state), real-evidence NULLs are `missing` (surfaced as
   availability statements, never hidden), and anything not
   `evidence_label="real"` (mocked/synthetic/cached/external) is
   `excluded` — counted and named under Limitations, never stated as
   observed. Construction itself rejects duplicates (two vintages for
   one period) and out-of-vocabulary evidence labels.
2. **Claims** (`claims.py`): every statement is an atomic `Claim`
   (`level` / `change` / `availability`) carrying the observations it
   cites (`refs`, the S03 observation identity). Claims are built by
   deterministic templates — one level claim per (country, indicator)
   at its latest observed period, one change claim when the two latest
   observed periods are exactly one frequency step apart (no
   comparison across gaps: a "rose from" sentence across a gap would
   mislead about timing), one availability claim per recorded missing
   observation.
3. **Adjudication** (`adjudicate`): every claim is validated against
   the facts JSON — exact value match, citation resolution — and
   rejected with a reason from a closed vocabulary:
   `fact_not_found`, `value_mismatch`, `evidence_not_real`,
   `missing_value_claimed`, `citation_missing`, `citation_mismatch`,
   `availability_contradicted`, `reason_mismatch`.
4. **Prose** (`prose.py`): `render_briefing()` assembles the document
   from **validated claims only** (rejected text never renders; a count
   of rejections appears under Limitations). `check_prose()` is the
   banned-phrase rejection layer — causal phrasing, investment advice,
   forecasting, and merit rankings (closed, named regex vocabulary) —
   which the rendered document must itself pass.
5. **Persistence** (`run.py`): `record_briefing_run()` writes one
   `briefing_runs` row (generator identity + prompt version) and one
   `briefing_claims` row per attempt — **including rejected claims with
   `validated=False`** — so the audit trail records what was refused,
   not only what passed.

## AI boundary

docs/Architecture.md §5: the LLM may summarize validated facts, compare
periods, and state limitations; it may not calculate source-of-truth
metrics, invent causes, hide missingness, or produce financial advice.

This unit implements the **enforcement machinery** with deterministic
templates — no LLM is called (no key exists in this environment), and
the run row records `model="deterministic-template"` so the record says
so honestly. An LLM attached later plugs in as *another prose source*:
whatever it produces must survive the same claim adjudication and
banned-phrase check, and its identifier replaces
`deterministic-template` in `briefing_runs.model`. The machine computes;
the prose reports.

## Values and wording conventions

- Values render at full precision (`repr`) — the briefing states exactly
  what the service served.
- Direction wording is descriptive comparison only: `up from` /
  `down from` / `unchanged from`.
- The document is pure: no clock reads, no I/O. The run row records
  the time; the document does not.

## Live demo

```bash
# service running on :8000, then:
PYTHONPATH=src .venv/bin/python evidence/S16/live-demo-script.py
```

Fetches the latest-vintage real-WB panel, builds and adjudicates
claims, renders and phrase-checks the document, demonstrates both
rejection paths on deliberately bad input (a tampered value and a
causal sentence), persists the run to the dev database, and re-reads
the rows. Output: `evidence/S16/live-demo-output.txt`.

## Verification

- `tests/test_briefing.py` (35 tests): facts partition and construction
  gates; claim building incl. boundary cases (quarterly step,
  no-change-across-gap, unknown frequency); every rejection reason
  exercised; the rendered document passing `check_prose`; citations
  and full precision in prose; excluded observations named in
  limitations; persistence round-trip with validated flags and
  evidence-ref JSON.
