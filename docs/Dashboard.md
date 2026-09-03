# Dashboard (S14–S15)

The Streamlit dashboard serves three views over the S13 query service:
country, comparison, and provenance. All data shaping lives in tested,
pure functions (`src/macropulse/views/assembly.py`); presentation labels
(freshness, badges, captions) in `src/macropulse/views/labels.py`; all
fetching lives in the typed client (`src/macropulse/views/client.py`);
the Streamlit script itself is a thin rendering layer.

## Run

The dashboard consumes the query service over HTTP (per the architecture
data flow: connectors → store → FastAPI service → dashboard). Start the
service first, then the dashboard (repo root):

```bash
# terminal 1 - the query service
PYTHONPATH=src .venv/bin/python -m uvicorn macropulse.api.main:app --port 8000

# terminal 2 - the dashboard
PYTHONPATH=src .venv/bin/streamlit run app/dashboard.py
```

`PYTHONPATH=src` is required until the `.venv` hidden-flag defect is
repaired in E01. The service URL defaults to
`http://127.0.0.1:8000` and can be overridden with the
`MACROPULSE_API_URL` environment variable.

## The three views

### Country view
The current picture of one country: latest-vintage observations for the
selected indicators with every provenance field visible (unit, frequency,
vintage, evidence label, quality grade, source system + code + role,
release/retrieval times, missing reason). A line chart is shown when
exactly one indicator (one unit) is selected — several indicators with
different units never share a chart axis, because a shared axis would
mislead; the table is shown instead.

### Comparison view
One indicator across selected countries: a line chart, a
periods × countries matrix, and per-country coverage counts (observed /
missing / total periods, first and last observed). The matrix names
missing cells — never blank, zero, or interpolated; the chart leaves
gaps (`connectgaps=False`) rather than drawing lines through missing
periods.

### Provenance view
Revision transparency (RQ4): every stored vintage for one country +
indicator, sorted by period then vintage, with the newest vintage per
period flagged. Superseded vintages stay visible next to what replaced
them — nothing is overwritten.

## Labels (S15)

The label layer (`src/macropulse/views/labels.py`, pure and tested)
answers "what am I looking at, how old is it, and how far can I trust
it":

- **Labels legend** (sidebar expander): the quality-badge vocabulary
  with each grade's S07 meaning (including why `preliminary` and
  `estimated` are reserved), the freshness convention and its threshold,
  and the five evidence labels with their true origins — `cached` is
  honestly marked "reserved for the scheduled-refresh layer (not yet
  emitted)".
- **Freshness** is computed, not stored: a sidebar **as-of date**
  (default today UTC) is the only clock read; every state derives from
  it arithmetically — age from the last *observed* period to the
  as-of date, in frequency steps (monthly = 1, quarterly = 3, annual =
  12). `current` below 2 steps, `lagging` at 2+ steps, `no_data` when
  nothing is observed. It is arithmetic on observation dates, not a
  claim about scheduled releases (the release calendar is unpopulated
  by S07 decision, so no expected-release is invented). Negative ages
  (as-of before the last observed period) are shown, not clamped.
  A per-indicator freshness table sits in the country view; the
  comparison view merges freshness states onto the coverage counts
  (a country with no data for the indicator reads `no_data`, never a
  guessed age).
- **Quality badges decorate, never replace**: the grade word always
  travels with its symbol (`● official`, `◌ ungraded`, `↻ revised`,
  `⚠ flagged`, …) in the country and provenance tables; a grade outside
  the closed vocabulary renders `unknown(<grade>)` — visible, never
  silently remapped.
- **Chart captions** state only what the chart shows — economies,
  periods, evidence labels, vintage range, and missing-point count are
  all computed from the observations actually rendered.
- **Provenance on hover**: chart points show value, vintage, evidence
  label, and quality grade in the tooltip, at full precision — tooltips
  match the tables.
- **Indicator methodology and limitations** (country-view expander):
  unit, frequency, seasonal adjustment, fallback status, primary and
  fallback sources, comparability notes, and limitations read from the
  code-level S02 catalog (the same source the S13 methodology
  endpoints read formulas from — static methodology from code, dynamic
  data from the API; the pinned API contract stays unchanged). An
  indicator absent from the catalog renders an explicit
  "no catalog entry" line.

## Failure and empty states

- Service unreachable / degraded → an error with the exact command to
  start the service; no data is shown or invented.
- Empty database → an explicit "no countries/indicators registered yet"
  message; nothing is inferred.
- No observations for a selection → an explicit empty-state message.
- Values are rendered exactly as served (no rounding); missing values
  render as `missing (<reason>)`.

## Caching

Fetches are cached for 60 s (`st.cache_data`) keyed by the API URL and
query parameters, so widget interactions do not re-hit the service.
Caching never masks an error: the first failed call raises and renders
the error state.

## Verification

- `tests/test_views.py` (26 tests): the client is exercised against
  `httpx.MockTransport` (pagination until the announced total, filter
  pass-through, HTTP/transport errors wrapped as `QueryServiceError`,
  refusal of over-delivery) and the assembly functions are tested as
  pure data transformations (missing marking, vintage-chain flagging,
  gap preservation, coverage counting, empty inputs).
- `tests/test_labels.py` (22 tests): badge vocabulary coverage and
  unknown-grade visibility; freshness boundary arithmetic (exactly 2
  steps → lagging, 1.92 → current; quarterly boundaries), observed-only
  measurement, grouping, negative ages not clamped, unknown frequency
  rejected; coverage/freshness merge with `no_data` defaults; chart
  captions (normal, singular, vintage range, missing clause, empty);
  per-point hover provenance parallel to the rendered points.
- `evidence/S14/live-demo-output.txt`: the real dashboard script run
  against the live service via Streamlit's AppTest harness — all three
  views rendering real (evidence_label=real) World Bank data with full
  provenance, view switches, and the empty state.
- `evidence/S15/live-demo-output.txt`: the same harness exercising the
  labels layer — freshness tables, merged coverage+freshness, badges,
  chart captions, limitations from the catalog, and the computed-label
  proof (moving the as-of date to 2028-01-01 flips every comparison
  state from `current` to `lagging`).
