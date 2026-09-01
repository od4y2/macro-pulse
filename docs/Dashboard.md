# Dashboard (S14)

The Streamlit dashboard serves three views over the S13 query service:
country, comparison, and provenance. All data shaping lives in tested,
pure functions (`src/macropulse/views/assembly.py`); all fetching lives
in the typed client (`src/macropulse/views/client.py`); the Streamlit
script itself is a thin rendering layer.

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
- `evidence/S14/live-demo-output.txt`: the real dashboard script run
  against the live service via Streamlit's AppTest harness — all three
  views rendering real (evidence_label=real) World Bank data with full
  provenance, view switches, and the empty state.
