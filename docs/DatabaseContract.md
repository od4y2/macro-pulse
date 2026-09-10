# Database and API Contract (locked in S03, 2026-08-19)

Machine-readable sources of truth: `src/macropulse/db/models.py` (schema) and
`src/macropulse/api/schemas.py` (API contract). Alembic migration
`bcc78be651f0` implements the schema on PostgreSQL 16 (docker-compose);
`c9af6b543047` adds the S17 `refresh_runs` table (see the dated note below).
The S13 FastAPI service must implement the API contract below without
changing response shapes; changes require a new decision entry.

## Data flow (locked)

```text
Connector (S04/S05) --writes--> raw_observations (immutable, full payload)
    |
    v
Normalization pipeline (S06) --writes--> normalized_observations
    |                                        |
    v                                        v
Release calendar (S07)              data_quality_flags (S07)
    |
    v
Derived metric engine (S08-S12) --writes--> derived_metrics + metric_versions
    |
    v
FastAPI query service (S13) --reads only--> Streamlit (S14) / AI briefing (S16)
```

Module boundaries: connectors write raw only; the pipeline writes normalized
only; the metric engine reads normalized and writes derived + versions; the
API layer is read-only; AI briefings (S16) read validated facts and record
claims with evidence refs. The S17 refresh layer ORCHESTRATES connectors and
the S06 pipeline (writing raw + normalized through them) and additionally
writes its own `refresh_runs` audit rows — it adds no new observation tables
or paths.

## Tables (12)

| Table | Purpose | Key constraints |
|---|---|---|
| countries | locked S01 panel | PK iso3 |
| indicators | locked S02 catalog | PK indicator_id; enum frequency, seasonal_adjustment |
| source_catalog | primary/fallback sources per indicator | unique (system, code, role); enum source_system, verification_status |
| release_calendar | scheduled/actual releases per series | unique (system, country, indicator, reference_period) |
| raw_observations | immutable as-retrieved payloads | FK source; value nullable; full JSON payload |
| normalized_observations | governed observations | unique (indicator, country, period, vintage, source); enum evidence_label; CHECK value NULL requires missing_reason |
| derived_metrics | computed metrics | unique (metric_key, country, period); formula_ref + input ids recorded |
| metric_versions | definition history per metric | unique (metric_id, version) |
| data_quality_flags | explicit quality/missingness flags | FK normalized_observation |
| briefing_runs | one row per AI briefing attempt | model + prompt_version recorded |
| briefing_claims | atomic claims with evidence refs | FK briefing_run; validated flag |
| refresh_runs | one row per scheduled-refresh cycle (S17) | append-only lifecycle; outcomes JSON with closed reason vocabulary |

Dated note (S17, 2026-09-10): the twelfth table `refresh_runs` was added by
migration `c9af6b543047` — the operational audit layer. It breaks no S03
lock: observation identity, provenance fields, and evidence governance are
untouched (verified by the unchanged S03 model tests plus the S13 pin).

Governance enforced at the schema level:

1. Every normalized observation carries all nine S01 provenance fields
   (period, release_time, retrieval_time, vintage, unit, frequency,
   seasonal_adjustment, source -> source_id, quality_grade) plus
   evidence_label from the locked five-label vocabulary.
2. A NULL value requires a missing_reason - missingness is never hidden.
3. Vintages are first-class: the same (indicator, country, period) can hold
   multiple vintages and sources without collision.
4. Raw payloads are immutable provenance; normalization never overwrites.

## Cloud deployment constraints (Vercel target)

- Connection strings come from `DATABASE_URL` only (no local assumptions).
- Engine pooling uses SQLAlchemy defaults so a managed provider's pooler
  (e.g., pgBouncer-style transaction pooling) can be injected via URL
  parameters.
- Migrations run via `alembic upgrade head` against the managed database;
  `alembic/env.py` prefers `DATABASE_URL` over `alembic.ini`.
- The schema uses no local-only extensions (no `uuid_ossp`, etc.).

## API contract (implemented in S13)

| Endpoint | Returns |
|---|---|
| `GET /health` | HealthOut: status, data_mode |
| `GET /countries` | list[CountryOut] |
| `GET /indicators` | list[IndicatorOut] |
| `GET /observations?indicator_id&country_iso3&from&to&vintage&evidence_label` | list[ObservationOut] - full provenance per row |
| `GET /metrics/{metric_key}?country_iso3&from&to` | list[MetricOut] with version |
| `GET /briefings/latest?country_iso3` | BriefingOut with claims + evidence refs |

Rules: ObservationOut forbids extra fields (`extra="forbid"`) so unlabelled
data cannot leak; `value: null` is valid output meaning missing; only the
five locked evidence labels are accepted.
