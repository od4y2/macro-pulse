# S13 design notes

## Intended files (stated before editing; as executed)

- UNCHANGED `src/macropulse/api/schemas.py` — the S03-pinned contract,
  implemented unchanged (verified byte-identical in the acceptance run;
  a stray `ruff format` rewrap of one tuple was reverted before commit)
- UPDATED `src/macropulse/api/main.py` — `create_app()` factory, router
  registration, truthful `/health`
- NEW `src/macropulse/api/deps.py` — per-request session dependency
- NEW `src/macropulse/api/routes.py` — `/countries`, `/indicators`,
  `/observations`, `/metrics`
- NEW `src/macropulse/api/methodology.py` — `/methodology/formulas`,
  `/methodology/metrics/{metric_key}`
- UPDATED `src/macropulse/smoke.py` — smoke now boots the assembled
  service and requires a healthy `/health`
- DELETED `tests/test_health.py` — starter assertion
  (`data_mode="starter-no-live-data"`) superseded by the real service's
  health tests (ok + degraded) in `tests/test_api_service.py`
- NEW `tests/test_api_service.py` (23 tests)
- NEW `docs/QueryService.md`
- NEW `evidence/S13/` (acceptance-run.txt, design-notes.md,
  live-demo-script.py, live-demo-output.txt, these notes)
- UPDATED `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`,
  `docs/decisions.md`, `docs/CoBuildLog.md`

## Design decisions

- **Pinned contract served verbatim.** `schemas.py` was not touched; the
  test suite asserts the served observation JSON key set equals
  `ObservationOut.model_fields` exactly, so drift from the S03 pin
  fails a test rather than passing silently.

- **Health tells the truth about backing, not content.** The starter's
  `data_mode="starter-no-live-data"` described a stub. The real service
  reports `data_mode="database"` when the DB answers `SELECT 1`, and
  `status="degraded"` + `data_mode="database-unreachable"` when it does
  not. Data *content* is never claimed by the health endpoint — that is
  what per-row evidence labels are for.

- **`latest_vintage` composes with filters, not after them.** The
  max-vintage subquery is built from the same filtered query, so
  `evidence_label=real&latest_vintage=true` means "the newest vintage
  among real-labelled rows", not "newest vintage, then drop it if it is
  not real-labelled". Grouping is per (indicator, country, period,
  source) — the schema's observation identity without vintage.

- **Closed vocabularies validated at the boundary.** `module`
  (S01 scope), `evidence_label` (S01), and `quality_grade` (S07) are
  `Literal`-typed query params: an invalid value is a 422 that lists
  the legal values, never a silent empty page that reads as "no data".
  Unknown indicator/country IDs remain filter semantics (empty list),
  because those are open-ended identifiers, not vocabularies.

- **Pagination is uniform and honest.** Every list endpoint takes
  `limit` (default 50, max 500) and `offset`, returns deterministic
  order, and carries the unpaginated filtered count in `X-Total-Count`
  — an empty page with `X-Total-Count: 247` is visibly a page, not "no
  data".

- **Methodology is served from where it actually lives.** Formula
  definitions come from the `FORMULAS` registry (the code that runs),
  and per-metric definitions come from `metric_versions` rows written by
  `persist_derived` (what was recorded, when). An unknown metric key is
  a 404, not an empty list — "no methodology" must not be
  indistinguishable from "never heard of it".

- **A metric without a recorded version is skipped, not invented.**
  `MetricOut.version` has no "unknown" value in the pinned contract, so
  a version-less derived row is omitted rather than served with a
  fabricated version string. Sanctioned write paths always record a
  version, so this guards only out-of-contract rows.

## Errors found and fixed during the unit (truthful record)

- `ruff format` run over the whole `src/macropulse/api` directory
  reformatted the PINNED `schemas.py` (rewrapped the `_QUALITY_GRADES`
  tuple). Reverted with `git checkout`; format scope now excludes the
  pinned file. The pin outranks format conformity.
- B008 (`Depends(...)`/`Query(...)` calls in parameter defaults, ruff
  0.16.1 default rule set) — fixed by the `Annotated` style (`DbSession`,
  `PageLimit`, `PageOffset` aliases), not by noqa.
- First `Annotated[int, Query(50, ...)]` attempt put parameters without
  defaults after defaulted ones — invalid Python syntax; fixed by giving
  explicit constant defaults (`limit: PageLimit = DEFAULT_LIMIT`) and
  moving `db: DbSession` first in signatures.

## Demo notes (live-demo-output.txt)

- The demo is a real HTTP run: uvicorn boots against a disposable
  database seeded with a LIVE World Bank fetch (USA + ZAF
  NY.GDP.MKTP.KD.ZG, evidence_label=real, 11 points each, 2015-2025)
  normalized through the S06 pipeline, plus a robust_z derived metric
  through the S08 engine. 10 HTTP requests across all endpoints; the
  disposable database is dropped at the end.
- `GET /observations?missing=true` returned 0 rows in the live demo —
  truthful for that fetch (this WB series returned only published
  years, no NULL placeholders). The missing-row path (value null +
  missing_reason served, `missing=false` complement) is proven in
  `tests/test_api_service.py` with synthetic seeds.
- Pre-existing lint findings in `scripts/validate_structure.py`
  (INIT-era) are outside S13 scope and were not touched.
