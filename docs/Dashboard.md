# Dashboard (S14–S18)

The Streamlit dashboard serves three views over the S13 query service:
country, comparison, and provenance. All data shaping lives in tested,
pure functions (`src/macropulse/views/assembly.py`); presentation labels
(freshness, badges, captions) in `src/macropulse/views/labels.py`; the
S18 visual language (design tokens, focus-and-context, episode overlays)
in `src/macropulse/views/theme.py` and
`src/macropulse/views/annotations.py`; all fetching lives in the typed
client (`src/macropulse/views/client.py`); the Streamlit script itself is
a thin rendering layer.

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

**Survey-wave series are visible, not blank.** For an indicator whose
observed points are isolated — every grid neighbour a recorded gap (the
Global Findex shape: five survey years, e.g. 2011/2014/2017/2021/2024,
the years between source-confirmed empty) — a line-only trace with
`connectgaps=False` would draw *nothing at all*. An observed point both
of whose neighbours are missing therefore also renders as an explicit
marker in the series color (`isolated_point_indices`, pure and tested):
the actual survey years stand out, the gaps around them stay gaps, and
nothing is interpolated or zero-filled. A **missingness note** under the
chart separates the two kinds of absence: periods the source itself
reports no value for (named with their `missing_reason` — non-survey
years of a survey series, *not* retrieval omissions) vs. grid periods
with no record at all (*expected but missing* — a retrieval/recording
gap). Observed periods are listed by name when there are ≤10 of them,
counted otherwise.

### Comparison view
One indicator across selected countries: a focus-and-context line chart
(one **focus country** wears its entity hue; every other economy renders
in context grey — at most one colored line at a time), a
periods × countries matrix, and per-country coverage counts (observed /
missing / total periods, first and last observed). The matrix names
missing cells — never blank, zero, or interpolated; the chart leaves
gaps (`connectgaps=False`) rather than drawing lines through missing
periods, with markers on isolated observed points and the missingness
note exactly as in the country view. The coverage counts split
`missing` into `source_no_data` (a row exists with a NULL value — the
provider was asked and reported nothing) and `no_record` (the grid has
the period but the country has no row at all); the split always sums
back to `missing`.

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
  honestly marked "reserved: the S17 refresh layer stores real data or
  records failure; no cached rows are emitted" (the layer exists as of
  S17 and still emits nothing labelled `cached`; verified again when the
  legend was reworded).
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
- **Missingness note** (`missingness_note`, pure and tested): under
  every chart, a second caption separates *source-confirmed gaps* (rows
  with NULL values, named with their recorded `missing_reason` — e.g.
  the non-survey years of a survey series; retrieval happened, the
  source itself has no value) from *unrecorded grid periods* (no row at
  all where the shared grid expects one — expected but missing). It
  lists the observed periods by name when few (survey waves) and always
  ends with "Nothing is interpolated or zero-filled." Absent when
  nothing is missing.
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

## Visual language (S18)

An editorial look-and-feel, referenced from the Financial Times's modern
presentation (adopted: serif headline type, hairline grid, recessive
non-data ink, generous whitespace, direct labels; NOT adopted: the
newsroom palette and dark mode). Light mode is **pinned** in
`.streamlit/config.toml` — the palette is validated against the light
surface and an automatic dark flip would invalidate it. One mode,
rendered right.

- **Design tokens** (`src/macropulse/views/theme.py`, pure and tested):
  an entity-fixed ten-hue palette covering exactly the S01 panel. Color
  follows the **entity, never its rank** — switching the focus country
  repaints nothing; the new focus keeps its own hue and the old focus
  falls back to context grey. An unknown country raises rather than
  defaulting to a hue (identity is never fabricated). The palette is
  validator-run (`evidence/S18/palette-validation.txt`); the floor-band
  WARNs are legal only under the relief rule — every chart ships
  secondary encoding (direct label + legend + the matrix table view)
  and at most one colored line renders at a time.
- **Focus-and-context**: the focus series wears its entity hue at focus
  width and is the only legend entry; context series wear grey at a
  lighter width with no legend entry. A direct label names the focus
  series at its last *observed* point — a gap at the tail is never
  labeled.
- **Documented episode bands**
  (`src/macropulse/case_study/macro_episodes.py` +
  `src/macropulse/views/annotations.py`): validated registry entries —
  citation is a constructor rule, the evidence label is always
  `external` (an episode is a document about an event, never an API
  observation), and the URL is live-verified. The 2020 WHO pandemic
  window renders as a wash drawn *below* the lines, clipped to the
  rendered range, with a callout anchored inside the band (a window
  under 1% of the rendered range gets the wash but no callout). The
  caption carries the full citation and states the band is *drawn as
  observed*; a causal-wording filter runs at render time, so no
  caption can claim the event caused the values.

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

- `tests/test_views.py` (38 tests): the client is exercised against
  `httpx.MockTransport` (pagination until the announced total, filter
  pass-through, HTTP/transport errors wrapped as `QueryServiceError`,
  refusal of over-delivery) and the assembly functions are tested as
  pure data transformations (missing marking, vintage-chain flagging,
  gap preservation, coverage counting with the `source_no_data` /
  `no_record` split summing to `missing`, isolated-point detection for
  survey-wave series — all-isolated, dense, edge, single-gap, run
  interior, empty inputs).
- `tests/test_labels.py` (29 tests): badge vocabulary coverage and
  unknown-grade visibility; freshness boundary arithmetic (exactly 2
  steps → lagging, 1.92 → current; quarterly boundaries), observed-only
  measurement, grouping, negative ages not clamped, unknown frequency
  rejected; coverage/freshness merge with `no_data` defaults; chart
  captions (normal, singular, vintage range, missing clause, empty);
  the missingness note (survey years listed and source gaps named with
  their reason, unrecorded grid periods flagged as expected-but-missing,
  count-not-list above 10 observed periods, `None` when nothing is
  missing, reason-less NULL still a source gap, no zero-fill);
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
- `tests/test_theme.py` (14), `tests/test_macro_episodes.py` (15),
  `tests/test_annotations.py` (19): the token layer (panel-exact palette,
  unknown-country rejection, focus/context styling, serif-left one-axis
  layout, last-observed-point labels), the episode registry
  (citation-mandatory construction, closed kinds, window arithmetic,
  registry uniqueness), and the overlay builders (causal-wording
  filter, range filtering, band/callout specs, narrow-band rule,
  clipping, application to real figures, full-citation captions).
- `evidence/S18/live-demo-output.txt` (DEMO PASSED, exit 0): the full
  six-leg chain on a disposable database — live ingest through the
  refresh CLI, gate + standardization, the service with a served-vs-
  stored byte-check, the AppTest-driven dashboard asserting the S18
  visual language on the served figure JSON (including the USA→CHN
  focus switch), the S16 briefing, and the historical case (2020 panel
  values beside the documented WHO window).
