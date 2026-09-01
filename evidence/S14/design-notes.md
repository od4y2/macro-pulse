# S14 design notes

## Intended files (stated before editing; as executed)

- UPDATED `pyproject.toml` — `streamlit>=1.37` and `plotly>=5.22` added
  to project dependencies (pandas arrives transitively; not imported
  directly, so not declared)
- REPLACED `app/dashboard.py` — the prepared starter stub (which
  claimed "no live macroeconomic data has been fetched" — no longer
  true) with the real dashboard: Country / Comparison / Provenance views
- NEW `src/macropulse/views/__init__.py`
- NEW `src/macropulse/views/client.py` — QueryServiceClient (httpx,
  pagination, MockTransport-injectable)
- NEW `src/macropulse/views/assembly.py` — pure view-model builders
- NEW `tests/test_views.py` (26 tests)
- NEW `docs/Dashboard.md`
- NEW `evidence/S14/` (acceptance-run.txt, design-notes.md,
  live-demo-script.py, live-demo-output.txt, these notes)
- UPDATED `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`,
  `docs/decisions.md`, `docs/CoBuildLog.md`
- Environment note (not a repo file): the streamlit wheel could not be
  downloaded through pip on this network (10.5 MB transfer repeatedly
  cut at ~262 kB); downloaded with curl resume-retry into the venv.
  Same pinned requirement in pyproject either way.

## Design decisions

- **Views consume the API, not the DB.** The architecture data flow is
  connectors → store → FastAPI service → dashboard; the dashboard is a
  client of the S13 service over HTTP (`MACROPULSE_API_URL`),
  so provenance is exactly what the service serves - the dashboard
  cannot bypass the pinned contract.

- **Pure assembly, thin rendering.** Everything testable (row shaping,
  missing marking, vintage flagging, gap preservation, coverage
  counting) is a pure function in `assembly.py`; `app/dashboard.py`
  only fetches and renders. All 26 unit tests target the pure layer +
  the client; the rendering layer is verified live (AppTest evidence).

- **Missing data renders as a named state, never blank.** A missing
  value displays as `missing (<reason>)` in tables; chart traces keep
  `None` so plotly draws gaps (`connectgaps=False`) — an interpolated
  line through a missing period would fabricate data. A missing row
  with no recorded reason displays `missing (no reason recorded)` —
  itself a signal that something is out of contract.

- **No shared axis across units.** The country-view chart only renders
  when the selection is one indicator with one unit; multi-unit
  selections get an explicit warning and table only.

- **Values at full precision.** `repr(value)` — no rounding anywhere in
  the view layer; the dashboard shows exactly what the service served.

- **The client refuses silent truncation.** Pagination follows
  `X-Total-Count`; a stream longer than the announced total raises
  rather than returning a partial result.

- **Honest failure/empty states.** Service down → error + the exact
  start command; empty database → explicit message; no data for a
  selection → explicit message. The sidebar shows the live health
  status (ok / degraded) so the backing state is visible.

- **Coverage counts, not coverage judgments.** The comparison view
  counts observed/missing per country over the union period grid;
  S09's gate thresholds are NOT applied — counts are data, thresholds
  are the S09 layer's judgment.

- **st.stop() only outside tabs.** Streamlit's stop halts the whole
  script run, so tab-local empty states use if/else branches instead —
  otherwise an empty Country selection would blank the other two tabs.

- **Cache keys are strings.** Cached fetch functions take the API URL
  (hashable) rather than the client object; a new client per cached
  call is cheap and keeps `st.cache_data` hashing trivial.

## Scope boundary vs S15

S15 refines charts, freshness labels, quality badges, and limitations.
S14 therefore renders `quality_grade` as a plain data column (hiding a
provenance field the service serves would violate "preserve source
metadata") but adds no badges, freshness indicators, or chart
explanations — those are S15's unit.

## Errors found and fixed during the unit (truthful record)

- First draft called `st.stop()` inside tabs for empty selections —
  would have suppressed the other tabs' rendering; restructured to
  if/else branches.
- First draft passed the client object into `st.cache_data` functions
  (unhashable); switched cache keys to the API URL string.
- First draft read the private `client._base_url`; replaced with a
  public `base_url` property.
- Pagination test mock was nested one level too deep (`[["a"], ["b"],
  ["c"]]`); fixed to a flat list so offset slicing behaves like the
  service.
- `use_container_width=True` is deprecated in streamlit 1.62 (removal
  after 2025-12-31); replaced with `width="stretch"` (6 occurrences).
- AppTest resolves relative script paths against the CALLING file; the
  evidence script anchors `app/dashboard.py` via `Path(__file__)`.
- AppTest `set_value` on a selectbox with `format_func` requires the
  FORMATTED option label, not the raw value (ValueError: None is not
  in list); the demo script selects via the formatted label.

## Live demo notes

- The demo (live-demo-output.txt) runs the REAL dashboard script
  against the REAL running service via Streamlit's AppTest harness —
  the same runtime a browser drives, without a browser. 0 exceptions;
  3 tabs; 4 dataframes; the comparison matrix renders 11 periods × 10
  economies of live-fetched World Bank GDP growth (evidence_label=real);
  the provenance view shows all 11 vintage rows with is_latest_vintage
  flags.
- `Periods with >1 vintage: 0` is truthful: the dev DB was seeded once
  (single vintage per period). The revision-chain display is proven in
  unit tests (`test_provenance_rows_show_vintage_chain_and_flag_latest`).
- Missing-value rendering is proven in unit tests; the live WB series
  returned no NULL placeholder rows for these years, so the live tables
  show no missing cells — the demo does not stage synthetic gaps into
  the dev DB to fake a richer picture.
