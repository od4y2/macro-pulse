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
   of rejections appears under Limitations). The document is markdown
   with a machine-composed readability frame — `## Headlines`
   (deterministic bullets from validated claim fields), `## Key figures`
   (a table), `## Statements` (the validated claim texts verbatim),
   `## Availability` (compacted to per-indicator counts), and
   `## Limitations` — described under *Document structure* below.
   `check_prose()` is the banned-phrase rejection layer — causal
   phrasing, investment advice, forecasting, and merit rankings (closed,
   named regex vocabulary) — which the rendered document must itself
   pass.
5. **Persistence** (`run.py`): `record_briefing_run()` writes one
   `briefing_runs` row (generator identity + prompt version + status)
   and one `briefing_claims` row per attempt — **including rejected
   claims with `validated=False`** — so the audit trail records what
   was refused, not only what passed.
6. **Orchestration** (`generate.py`): `generate_briefing()` runs the
   whole path for one country — facts → claims → adjudication →
   prose source (LLM source when configured, else the deterministic
   template) → gates → `compose_document()` or `render_briefing()` →
   `record_briefing_run()`. Every call returns a `BriefingOutcome`
   and appends exactly one run row, whichever prose source served.

## Document structure

Both document paths — the LLM path (`compose_document`) and the
deterministic fallback (`render_briefing`) — open with the same
machine-composed frame (`frame_head_lines`), so the readability never
drifts between them:

```markdown
# MacroPulse briefing — Germany (DEU)

Scope: 1 economies, 11 indicator(s), 372 validated observations …        ← scope_line(), counts from the facts

## Headlines
- **Consumer price inflation [cpi_inflation_pct]**: **2.17** percent_per_year
  in 2025-01-01, down from 2.26 in 2024-01-01.                            ← first 4 series, sorted (never merit-based)
- Recorded missing: 354 observation(s) across 11 indicator(s) — itemized under Availability.

## Key figures
| Indicator | Latest period | Value | Change | Source |                   ← exhaustive (one row per series)
|---|---|---|---|---|
| Consumer price inflation [cpi_inflation_pct] | 2025-01-01 | **2.17** percent_per_year | down from **2.26** (2024-01-01) | world_bank FP.CPI.TOTL.ZG |

_Values in Headlines and Key figures are rounded for display (2 decimals); Statements carry full precision exactly as served._   ← ROUNDING_NOTE, only when rows exist

## Overview            ← LLM path only (the draft's own heading); absent on fallback
2–3 gated sentences, every number copied exactly from the claims.

## Statements
- <validated claim texts verbatim, full precision, full citations>        ← LLM: its own grouped bullets; fallback: the claim texts as adjudicated

## Availability        ← compacted on BOTH paths
- account_ownership_pct: 34 observation(s) recorded missing (reasons: …).
- The full per-observation list is persisted with this run's claims (audit trail).

## Limitations
- <limitation_lines(): excluded/rejected counts, the NON_CLAIMS boundary line>
```

The frame is machine text: Headlines and Key figures round for display
(`display_value`, ROUND_HALF_UP over `repr`, 2 decimals, trailing zeros
stripped, a nonzero that would round to zero shown as `<0.01`/`>-0.01`
rather than flattened to `0`) and say so via the ROUNDING_NOTE; the
`## Statements` section and the persisted claims carry the served
precision exactly. Multi-country payloads (the fallback's
`render_briefing` only — generation is one country per run) gain an
Economy column and an `(ISO3)` suffix per headline. The document never
computes a comparison the claims layer refused: a change clause appears
only when a validated change claim exists (consecutive periods). The
Availability section names every indicator with recorded-missing counts
and points at the audit trail; the 354-bullet per-observation wall is
gone from the document but fully retained in the persisted claims.

## AI boundary

docs/Architecture.md §5: the LLM may summarize validated facts, compare
periods, and state limitations; it may not calculate source-of-truth
metrics, invent causes, hide missingness, or produce financial advice.

The S16 core implements the **enforcement machinery** with deterministic
templates (the run row records `model="deterministic-template"` so the
record says so honestly). The LLM prose source (`llm.py`,
`generate.py`) plugs in as *another prose source* under the same
machinery — its identifier replaces `deterministic-template` in
`briefing_runs.model` only when its draft survives every gate. The
machine computes; the prose reports.

## LLM prose source (on-demand)

- **Configuration** — read from the environment **at call time** (never
  at import): `LLM_PROVIDER` (closed vocabulary; only
  `openai-compatible`, the default), `LLM_BASE_URL`, `LLM_MODEL`,
  `LLM_API_KEY`, and optionally `LLM_EXTRA_BODY` and
  `LLM_TIMEOUT_SECONDS`. Wire format: raw-httpx
  `POST {LLM_BASE_URL}/chat/completions` (no SDK). The key lives in a
  `SecretStr`; error messages carry the HTTP status and a truncated body
  only — never the key.
- **Read timeout (`LLM_TIMEOUT_SECONDS`)** — the `/chat/completions`
  read timeout, overridable per deployment; unset it defaults to
  `240 s`, and the value is validated against
  [`LLM_TIMEOUT_MIN`, `LLM_TIMEOUT_MAX`] = [1, 600] s (a non-numeric or
  out-of-range value is a typed config error → fallback, never a silent
  clamp). Sized against the real cross-border cloud path (US runtime →
  the project's Beijing endpoint): both earlier defaults timed out
  there in live service (45 s on 2026-10-28, 90 s on 2026-10-29, each
  rendering the honest `llm_transport_error` fallback), while the same
  calls measured 19–35 s from the best-case network — a non-streaming
  completion must fit entirely inside one read window, and the
  trans-Pacific path inflates it past any tight cap. It is nested
  inside the dashboard client's `300 s` (`BRIEFING_TIMEOUT`), so the
  LLM fails first and the fallback still renders inside the request;
  `tests/test_views.py` asserts `LLM_TIMEOUT_SECONDS <
  BRIEFING_TIMEOUT`. On the cloud host that client hop is in-process
  (loopback), so no external proxy shortens the wait. On cloud hosts
  the key is bridged from `st.secrets` like the other `LLM_*` vars.
- **Provider interop (`LLM_EXTRA_BODY`)** — an optional JSON object
  merged UNDER the fixed request keys (`model`, `messages`,
  `temperature` always win; malformed JSON is a typed config error →
  fallback). Reasoning models need it: their hidden thinking pass over a
  panel-scale prompt (hundreds of validated claims) can exceed any sane
  timeout — measured on the project's Qwen endpoint, 400 claims took
  >280 s with thinking on and **30.5 s** with
  `LLM_EXTRA_BODY={"enable_thinking": false}`. Unset, the body is
  exactly the OpenAI-compatible minimum, so strict endpoints keep
  working.
- **Prompt (`llm-v3`)** — built ONLY from validated claims and
  partition counts (`build_prompt`): the LLM never sees raw rows,
  excluded observations' values, or anything unvalidated. The v2 trim
  (2026-10-29) is unchanged: level/change claims travel verbatim (the
  only statement material), while the per-observation availability
  claims — measured 91–93% of a panel-scale prompt, ~16 K tokens per
  country — are compressed to a per-indicator recorded-missing summary
  with the no-value/no-enumeration rules inline. The numeric-fidelity
  gate is unchanged: it checks the prose against ALL validated claims,
  not against the prompt, so the trim narrows what the LLM may say,
  never what the gate allows. **v3** (2026-10-29 readability redesign)
  changes only the draft's shape: the system prompt requires exactly two
  sections — `## Overview` (2–3 sentences summarizing the current
  picture, numbers copied exactly) then `## Statements` (short bullets
  grouped by theme, indicator name bolded) — and forbids emitting any
  other heading, especially the machine-frame names (Headlines, Key
  figures, Availability, Limitations, Scope, or a document title). The
  exact-copying rule and the four banned phrase classes, forecasts,
  advice, and scope-count bans all still apply.
- **Four gates on the draft** — (1) the adjudication-derived prompt is
  the only input (unchanged from S16); (2) `check_prose` (banned
  phrases); (3) `check_numeric_fidelity` — every numeric token in the
  draft must decimal-equal a token in the validated claim texts, so a
  fabricated number can never render ("2.90" passes against a claim
  stating 2.9; ISO date components pass because dates appear in claim
  text); (4) `check_frame_conflict` — the draft must carry its own
  `## Overview` and `## Statements` headings and must NOT echo a
  machine-frame heading (whole-heading-line match, case-insensitive; an
  inline mention of "limitations" in prose never trips it). Integrity
  reasons (banned phrase, fabricated number) win over the structural
  frame reason, since a draft that both fabricates and misframes is
  reported for the more serious fault first.
- **Machine-composed frame** — the LLM writes the Overview and
  Statements sections only; the title, scope counts, Headlines, Key
  figures, rounding note, compacted Availability, Limitations, and the
  boundary line are deterministic (`compose_document` →
  `frame_head_lines`), built from the facts exactly as `render_briefing`
  builds them. Counts are never LLM-generated; the draft is inserted
  as-is between Key figures and Availability (the frame never parses or
  rewrites it). See *Document structure* above.
- **Total fallback** — any failure yields the deterministic template
  document, `status="fallback"`, and a warning naming the reason:

  | warning prefix | trigger |
  |---|---|
  | `llm_not_configured` | `LLM_*` env missing/incomplete, provider unsupported, `LLM_EXTRA_BODY` malformed, or `LLM_TIMEOUT_SECONDS` non-numeric/out-of-range |
  | `llm_transport_error` | endpoint unreachable, timeout, connection failure |
  | `llm_response_error` | non-200 status, malformed JSON, empty/misshapen prose |
  | `banned_phrase` | `check_prose` found a banned class (names it) |
  | `fabricated_number` | `check_numeric_fidelity` found unbacked tokens (quotes ≤5) |
  | `frame_conflict` | `check_frame_conflict` found a missing required heading or an echoed frame heading (quotes ≤5) |
  | `empty_llm_prose` | 200 with blank content |
  | `no_validated_statements` | no claim validated — the LLM is never even called |

- **Provenance** — every attempt appends a `briefing_runs` row: `model`
  (the LLM's id or `deterministic-template`), `prompt_version`
  (`llm-v3` or `s16-v1`), `status` (`completed` / `fallback`), plus the
  full adjudicated-claim trail. Append-only: nothing is updated or
  deleted.
- **Endpoints** — `POST /briefing {"country_iso3": "USA"}` generates on
  demand and returns the document plus `used_llm`, `warning`, and the
  run `id`; `GET /briefing/{run_id}` reads the persisted audit record
  back (see docs/QueryService.md).
- **Dashboard** — fourth tab, "AI briefing": country selectbox, a
  **Generate briefing** button (every click is one real generation and
  one appended run — never cached or replayed), the warning when the
  fallback served, the document rendered as real markdown
  (`st.markdown` — headings, table, and bold render natively), and the
  provenance caption (`model · prompt · status · run # · country`).
  Below the document, a **Headline figures** tile grid (`st.metric`, one
  per indicator, display-rounded via `display_value`) and an **Indicator
  trends** small-multiples grid (one time-series chart per indicator,
  reusing `line_chart`/`chart_traces` and the S18 theme) are built from
  the same cached latest-vintage rows the generation used, shaped by the
  pure `views.assembly.briefing_highlights` helper. A tile's direction
  and prior value appear in its caption (never as an `st.metric` delta —
  Streamlit draws an arrow glyph for any text delta) and only when the
  two periods are exactly one frequency step apart
  (`consecutive_periods`), the same no-comparison-across-gaps rule the
  change claims honor; charts keep gaps as gaps (never interpolated,
  never zero-filled). A guard caption appears when the displayed run's
  country differs from the currently selected one.
- **Streamlit Community Cloud** — add `LLM_PROVIDER`, `LLM_BASE_URL`,
  `LLM_MODEL`, `LLM_API_KEY` (and `LLM_EXTRA_BODY` when the provider
  needs it) to the app's secrets (beside the Neon URL);
  `cloud_runtime._bridge_secrets` maps them into `os.environ` before
  the service import (env-explicit wins, values are never logged).
  Without them the app keeps working — every generation falls back
  deterministically with `llm_not_configured`.

## Values and wording conventions

- **Statements and persisted claims render at full precision (`repr`)** —
  the briefing states exactly what the service served. The
  machine-composed **Headlines / Key figures frame rounds for display**
  (`display_value`: ROUND_HALF_UP over `repr`, 2 decimals, trailing
  zeros stripped) under the visible `ROUNDING_NOTE`; rounding is
  presentation of a validated value, never a restatement of the record,
  and the exact value always survives in the Statements section and the
  audit trail. A nonzero value that would round to zero shows as
  `<0.01`/`>-0.01`, never a fabricated `0`.
- The **numeric-fidelity gate checks the LLM draft only**, never the
  composed document — so the frame's display-rounded tokens are safe;
  the LLM's Overview and Statements must copy numbers exactly.
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

- `tests/test_briefing.py` (66 tests): facts partition and construction
  gates; claim building incl. boundary cases (quarterly step,
  no-change-across-gap, unknown frequency); every rejection reason
  exercised; the rendered document passing `check_prose`; citations
  and full precision in prose; excluded observations named in
  limitations; persistence round-trip with validated flags and
  evidence-ref JSON; `status` kwarg validation; the numeric-fidelity
  guard (`numeric_tokens`, `check_numeric_fidelity`: decimal equality,
  comma grouping, fabrication flagged, dedup); the readability frame —
  section order, ROUNDING_NOTE placement, `display_value` rounding
  (incl. `<0.01`/`>-0.01`, banker's-rounding traps, extremes), Key
  figures rows (single/level-only/multi-country Economy column, pipe
  escaping), Headlines 4-bullet cap vs exhaustive table, compacted
  Availability, `title_line` country naming and iso3 fallback, and the
  `check_frame_conflict` guard (accepted v3 shape, missing/forbidden
  headings, inline mentions never trip it).
- `tests/test_briefing_llm.py` (44 tests): `LLMSettings.from_env`
  (success, trailing-slash strip, missing-var names-only messages,
  unsupported provider, overlong model, `LLM_EXTRA_BODY` parsing and
  malformed-value errors); system/user prompt contents (validated
  claims only, rejected excluded, no secret in any prompt) incl. the
  v3 two-section draft contract (`## Overview` before `## Statements`,
  frame headings forbidden, `LLM_PROMPT_VERSION == "llm-v3"`, the
  user-message first line); request shape over `httpx.MockTransport`
  (path, Bearer header, body, extra keys merged under the fixed ones);
  4xx/5xx, malformed JSON, bad response shapes, transport failure —
  each with the API key absent from every raised message; call-time env
  read.
- `tests/test_briefing_generate.py` (21 tests): the orchestration and
  fallback matrix over a FakeSource — LLM success (completed row, full
  section order Headlines→Key figures→Overview→Statements→Availability→
  Limitations, ROUNDING_NOTE present), every warning path (banned
  phrase, fabricated number, transport/response error, empty prose,
  unconfigured env, no validated statements with the LLM never called),
  the frame gate (echoed frame heading, missing Overview; banned-phrase
  and fabricated-number win over frame-conflict), both document paths
  passing `check_prose`, foreign-country rejection, append-only runs,
  `record_run=False`, warning truncation, config warnings naming
  variables not values, and the closed eight-reason warning vocabulary.
- `tests/test_api_briefing.py` (9 tests): `POST /briefing` success and
  fallback (200 with warning), unconfigured env, empty scope, unknown
  country 404, bad-length iso3 422, `GET /briefing/{run_id}`
  round-trip (prose not persisted), unknown run 404, two POSTs
  appending two runs.
- `tests/test_views.py` (43 tests): client POST body/path and the
  nested briefing timeout, error text naming the method, GET run
  path, the D11 timeout-nesting invariant, and `briefing_highlights`
  (latest + consecutive prior selection with up/down/unchanged/None
  direction, no comparison across a gap, non-real and NULL-value rows
  skipped, deterministic sorted order, empty input → `[]`).
- `tests/test_cloud_runtime.py` (7 tests): the secrets bridge —
  values land verbatim, env-explicit wins, missing/raising secrets
  skip silently, non-str stringified, the bridged-key vocabulary,
  scheme normalization.

No test anywhere calls a live LLM; every generation is served by a
fake source or a mocked transport.
