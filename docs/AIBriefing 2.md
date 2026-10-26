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
  `LLM_API_KEY`, and optionally `LLM_EXTRA_BODY`. Wire format: raw-httpx
  `POST {LLM_BASE_URL}/chat/completions` (no SDK). The key lives in a
  `SecretStr`; error messages carry the HTTP status and a truncated body
  only — never the key. Timeout: 45 s (`LLM_TIMEOUT_SECONDS`), nested
  inside the dashboard client's 75 s (`BRIEFING_TIMEOUT`), so the LLM
  fails first and the fallback still renders inside the request.
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
- **Prompt** — built ONLY from validated claim texts and partition
  counts (`build_prompt`): the LLM never sees raw rows, excluded
  observations' values, or anything unvalidated. The system prompt
  requires exact copying of numbers/units/periods/citations and forbids
  the four banned phrase classes, forecasts, advice, and scope counts.
- **Three gates on the draft** — (1) the adjudication-derived prompt is
  the only input (unchanged from S16); (2) `check_prose` (banned
  phrases); (3) `check_numeric_fidelity` — every numeric token in the
  draft must decimal-equal a token in the validated claim texts, so a
  fabricated number can never render ("2.90" passes against a claim
  stating 2.9; ISO date components pass because dates appear in claim
  text).
- **Machine-composed frame** — the LLM writes the Statements section
  only; title, scope counts, limitations, and the boundary line are
  deterministic (`compose_document`), built from the facts exactly as
  `render_briefing` builds them. Counts are never LLM-generated.
- **Total fallback** — any failure yields the deterministic template
  document, `status="fallback"`, and a warning naming the reason:

  | warning prefix | trigger |
  |---|---|
  | `llm_not_configured` | `LLM_*` env missing/incomplete, provider unsupported, or `LLM_EXTRA_BODY` malformed |
  | `llm_transport_error` | endpoint unreachable, timeout, connection failure |
  | `llm_response_error` | non-200 status, malformed JSON, empty/misshapen prose |
  | `banned_phrase` | `check_prose` found a banned class (names it) |
  | `fabricated_number` | `check_numeric_fidelity` found unbacked tokens (quotes ≤5) |
  | `empty_llm_prose` | 200 with blank content |
  | `no_validated_statements` | no claim validated — the LLM is never even called |

- **Provenance** — every attempt appends a `briefing_runs` row: `model`
  (the LLM's id or `deterministic-template`), `prompt_version`
  (`llm-v1` or `s16-v1`), `status` (`completed` / `fallback`), plus the
  full adjudicated-claim trail. Append-only: nothing is updated or
  deleted.
- **Endpoints** — `POST /briefing {"country_iso3": "USA"}` generates on
  demand and returns the document plus `used_llm`, `warning`, and the
  run `id`; `GET /briefing/{run_id}` reads the persisted audit record
  back (see docs/QueryService.md).
- **Dashboard** — fourth tab, "AI briefing": country selectbox, a
  **Generate briefing** button (every click is one real generation and
  one appended run — never cached or replayed), the warning when the
  fallback served, and the provenance caption
  (`model · prompt · status · run # · country`).
- **Streamlit Community Cloud** — add `LLM_PROVIDER`, `LLM_BASE_URL`,
  `LLM_MODEL`, `LLM_API_KEY` (and `LLM_EXTRA_BODY` when the provider
  needs it) to the app's secrets (beside the Neon URL);
  `cloud_runtime._bridge_secrets` maps them into `os.environ` before
  the service import (env-explicit wins, values are never logged).
  Without them the app keeps working — every generation falls back
  deterministically with `llm_not_configured`.

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

- `tests/test_briefing.py` (43 tests): facts partition and construction
  gates; claim building incl. boundary cases (quarterly step,
  no-change-across-gap, unknown frequency); every rejection reason
  exercised; the rendered document passing `check_prose`; citations
  and full precision in prose; excluded observations named in
  limitations; persistence round-trip with validated flags and
  evidence-ref JSON; `status` kwarg validation; the numeric-fidelity
  guard (`numeric_tokens`, `check_numeric_fidelity`: decimal equality,
  comma grouping, fabrication flagged, dedup).
- `tests/test_briefing_llm.py` (26 tests): `LLMSettings.from_env`
  (success, trailing-slash strip, missing-var names-only messages,
  unsupported provider, overlong model, `LLM_EXTRA_BODY` parsing and
  malformed-value errors); system/user prompt contents (validated
  claims only, rejected excluded, no secret in any prompt); request
  shape over `httpx.MockTransport` (path, Bearer header, body, extra
  keys merged under the fixed ones); 4xx/5xx, malformed JSON, bad
  response shapes, transport failure — each with the API key absent
  from every raised message; call-time env read.
- `tests/test_briefing_generate.py` (15 tests): the orchestration and
  fallback matrix over a FakeSource — LLM success (completed row,
  frame markers), every warning path (banned phrase, fabricated
  number, transport/response error, empty prose, unconfigured env,
  no validated statements with the LLM never called), foreign-country
  rejection, append-only runs, `record_run=False`, warning
  truncation, config warnings naming variables not values.
- `tests/test_api_briefing.py` (9 tests): `POST /briefing` success and
  fallback (200 with warning), unconfigured env, empty scope, unknown
  country 404, bad-length iso3 422, `GET /briefing/{run_id}`
  round-trip (prose not persisted), unknown run 404, two POSTs
  appending two runs.
- `tests/test_views.py` (+4 tests): client POST body/path and the
  nested briefing timeout, error text naming the method, GET run
  path, the D11 timeout-nesting invariant.
- `tests/test_cloud_runtime.py` (7 tests): the secrets bridge —
  values land verbatim, env-explicit wins, missing/raising secrets
  skip silently, non-str stringified, the bridged-key vocabulary,
  scheme normalization.

No test anywhere calls a live LLM; every generation is served by a
fake source or a mocked transport.
