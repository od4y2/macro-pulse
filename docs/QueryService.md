# Query Service (S13)

The FastAPI query service exposes the normalized database through the
S03-pinned response contract (`src/macropulse/api/schemas.py`,
implemented unchanged). Provenance travels with every value: an
observation is never served as a bare number.

Run locally (Docker Postgres up, `PYTHONPATH=src`):

```bash
.venv/bin/python -m uvicorn macropulse.api.main:app --port 8000
```

Interactive docs at `/docs` (FastAPI auto-generated).

## Layout

| File | Role |
|---|---|
| `src/macropulse/api/main.py` | `create_app()` factory, `/health` |
| `src/macropulse/api/deps.py` | per-request DB session dependency (`get_session`, `DbSession`) |
| `src/macropulse/api/routes.py` | data endpoints |
| `src/macropulse/api/methodology.py` | methodology endpoints |
| `src/macropulse/api/briefing.py` | briefing generation + audit-read endpoints |
| `src/macropulse/api/schemas.py` | S03-pinned response shapes (unchanged) |

The session factory is injected at `create_app(session_factory=...)` and
stored on `app.state`; tests bind the service to the dedicated test
database through `app.dependency_overrides[get_session]`. The briefing
endpoints additionally accept an injectable LLM prose source via
`create_app(llm_source_factory=...)` (tests supply a fake; production
builds `HttpLlmSource` from the environment at call time — see
docs/AIBriefing.md).

## Pagination (all list endpoints)

- `limit` — page size, default 50, max 500 (`422` outside `[1, 500]`)
- `offset` — rows skipped, default 0, `422` if negative
- `X-Total-Count` response header — unpaginated count of the filtered set
- Ordering is deterministic (e.g. observations by indicator, country,
  period, vintage, id), so paging is stable

## Endpoints

### `GET /health`
`{status, data_mode}`. `status="degraded"` with
`data_mode="database-unreachable"` when the backing database cannot be
reached. `data_mode` says where data lives, not what it contains —
per-row provenance is the only honest content claim.

### `GET /countries`
Panel countries (iso3, name, rationale).

### `GET /indicators`
Catalog indicators. Filter: `module` (closed vocabulary — invalid values
fail `422`, they do not silently match nothing).

### `GET /observations`
Normalized observations, one row per (indicator, country, period,
vintage, source). Every response row carries the full S03 provenance
contract: value (`null` + `missing_reason` when missing — never imputed),
unit, frequency, seasonal adjustment, source (system/code/role/verified/
coverage), release and retrieval times, vintage, evidence label, quality
grade.

Filters:

| Parameter | Meaning |
|---|---|
| `indicator_id`, `country_iso3` | exact match |
| `period_start`, `period_end` | inclusive period bounds |
| `vintage` | exact vintage |
| `evidence_label` | closed S01 vocabulary (`422` otherwise) |
| `quality_grade` | closed S07 vocabulary (`422` otherwise) |
| `missing` | `true`: value IS NULL; `false`: value present |
| `latest_vintage` | keep only the newest vintage per (indicator, country, period, source) **among rows matching the other filters** — filters restrict which vintages compete, they are not applied after the fact |

### `GET /metrics`
Derived metrics with `formula_ref` and the **latest recorded version**.
Filters: `metric_key`, `country_iso3`, `period_start`, `period_end`.
A derived row with no recorded `metric_versions` row is skipped rather
than served with an invented version (sanctioned write paths always
record one).

### `GET /methodology/formulas`
The implemented formula registry (`FORMULAS`), sorted; optional `name`
filter. This is the code-level source of truth a `formula_ref`
resolves to.

### `GET /methodology/metrics/{metric_key}`
Definitions actually recorded in `metric_versions` for that key, newest
version first — the per-metric audit trail. `404` when the key has no
recorded definitions (an unknown key must not read as "no methodology").

### `POST /briefing`
Generate a structured briefing for **one country** on demand (S16
pipeline + LLM prose source; see docs/AIBriefing.md). Request body:

```json
{"country_iso3": "USA"}
```

- `422` when the iso3 is not exactly 3 characters (schema validation) or
  when the facts contract rejects the rows (e.g. duplicate latest
  vintages) — the contract failure is loud, never silently deduped
- `404` when the country is unknown to the panel

The endpoint reads the country's latest-vintage observations, commits
the read transaction **before** any LLM call (the session is not held
across it), builds/adjudicates claims, and either serves the LLM draft
(only after it passes every gate) or the deterministic template. It
**always returns `200` with a document** once the country exists —
LLM failure is not an HTTP error; it is a fallback:

```json
{
  "id": 12, "created_at": "...", "model": "gpt-...", "prompt_version": "llm-v2",
  "status": "completed", "claims": [{"claim_text": "...", "evidence_refs": [...], "validated": true}],
  "country_iso3": "USA", "prose": "MacroPulse structured briefing\n...",
  "used_llm": true, "warning": null
}
```

On fallback: `status="fallback"`, `model="deterministic-template"`,
`prompt_version="s16-v1"`, `used_llm=false`, and `warning` names the
reason from the closed vocabulary (`llm_not_configured`,
`llm_transport_error`, `llm_response_error`, `banned_phrase`,
`fabricated_number`, `empty_llm_prose`, `no_validated_statements`).
Every attempt appends a `briefing_runs` row (append-only audit); the
response `id` is that row. `evidence_refs` are full fact references
(indicator, country, period, vintage, source system/code) — provenance
travels with the prose too.

### `GET /briefing/{run_id}`
Read a persisted run back: `{id, created_at, model, prompt_version,
status, claims[]}` — the audit record (claims with validated flags and
evidence refs). The generated `prose` is **not persisted**, so it is
not served here; it exists only in the POST response. `404` for an
unknown run id.

## Conventions carried from the governance contract

- No hidden missingness: `value: null` requires `missing_reason` on the
  row (DB CHECK `ck_missing_requires_reason`), and both are served.
- Closed vocabularies (`evidence_label`, `quality_grade`, `module`) are
  validated at the API boundary, so an invalid filter is a loud `422`,
  never a silent empty result that looks like "no data".
- No composite indices, no causal claims, no investment advice — the
  service serves observations and recorded definitions, nothing more.
