# S15 design notes

## Intended files (stated before editing; as executed)

- NEW `src/macropulse/views/labels.py` — freshness states, quality
  badges, chart captions, coverage/freshness merge (all pure)
- UPDATED `src/macropulse/views/assembly.py` — `chart_traces` gained a
  per-point `hover` provenance record (additive key; S14 tests untouched
  and passing)
- UPDATED `src/macropulse/views/__init__.py` — label exports
- UPDATED `app/dashboard.py` — as-of control, freshness tables, badge
  columns, provenance hover on charts, chart captions, labels legend +
  indicator limitations expanders
- NEW `tests/test_labels.py` (22 tests)
- UPDATED `docs/Dashboard.md`
- NEW `evidence/S15/` (acceptance-run.txt, design-notes.md,
  live-demo-script.py, live-demo-output.txt, these notes)
- UPDATED `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`,
  `docs/decisions.md`, `docs/CoBuildLog.md`

## Design decisions

- **Freshness is arithmetic, not a release-schedule claim.** The state
  (current / lagging / no_data) is age measured from the last OBSERVED
  period to a caller-supplied as-of date, in frequency steps
  (FREQUENCY_STEP_MONTHS). The S07 decision keeps the release calendar
  unpopulated - no API exposes scheduled-release timestamps - so any
  "expected release" framing would be fabrication. The 2-step lag
  threshold is a documented presentation convention (an annual 2025
  observation legitimately publishes during 2026), same standing as
  S09's direction rule and S12's resolvable rule.
- **`as_of` is a sidebar control, not a hidden clock.** The pure
  functions take the date as a parameter; only the UI default reads the
  clock (`datetime.now(UTC).date()`, DTZ-clean). The demo proves the
  label is computed: setting as-of to 2028-01-01 flips every state to
  `lagging` (3.0 steps).
- **Negative ages are shown, not clamped.** An as-of before the last
  observed period yields a negative age - that signals out-of-order as-of
  use and hiding it would be silent sanitization.
- **Badges decorate, never replace.** `quality_badge` returns
  `"● official"` - the grade word always travels with the symbol. An
  unknown grade renders `unknown(<grade>)` rather than being silently
  mapped to something real.
- **Freshness measures OBSERVED periods only.** A NULL placeholder row
  for a newer period does not extend the observed tail (tested).
- **Limitations come from the code-level catalog, not a new API field.**
  `IndicatorOut` is S03-pinned (S13 decision: implemented unchanged);
  extending it would reopen a locked contract for a display-only need.
  The dashboard reads `macropulse.catalog` - the same pattern as the S13
  methodology endpoints reading `FORMULAS` from code: static methodology
  from code, dynamic data from the API. An indicator served but absent
  from the catalog renders an explicit "no catalog entry" line.
- **The legend is a governance surface.** Quality badges (S07
  vocabulary + semantics incl. why preliminary/estimated are reserved),
  freshness (the convention + threshold), and the five evidence labels
  (each with its true origin - cached honestly marked "not yet emitted")
  are all rendered once in an expander. `cached` was verified by grep:
  no emitter exists outside vocabulary definitions.
- **Chart captions cannot overclaim.** `chart_caption` counts
  economies, periods, evidence labels, vintages, and missing points
  FROM the observations actually rendered; a missing-points clause
  appears only when there are missing points.
- **Hover carries provenance.** Chart points now show vintage,
  evidence label, and quality grade on hover (customdata), at full
  precision - tooltips match what the tables show.

## Live-demo notes (live-demo-output.txt)

- Real dashboard script via AppTest against the running service and the
  live-fetched WB panel: 0 exceptions; freshness table (BRA current,
  1.67 steps); merged coverage+freshness for all 10 economies (current);
  badges in country and provenance tables; chart caption with evidence
  and vintage; limitations and comparability rendered from the catalog.
- The stored dev-DB rows are grade `ungraded` (normalize's default) -
  the S07 grading step has not been run on the dev database, so the
  demo honestly shows `◌ ungraded` badges. The other badge forms are
  proven in unit tests; no grading was run out of unit scope to
  cosmetically enrich the demo.
- As-of 2028-01-01: all 10 states flip to `lagging` at 3.0 steps - the
  computed-label proof.
- The duplicate streamlit launch in the acceptance run exited
  ("Port 8130 is not available"): a leftover server process from the
  previous session still holds 8130. That server re-executes
  `app/dashboard.py` from disk per session, so the HTTP 200 check hit
  the S15 code; the AppTest run is the independent verification.

## Errors found and fixed during the unit (truthful record)

- DTZ011 (`date.today()`) on the as-of default → replaced with
  `datetime.now(UTC).date()` (explicit timezone; UTC default for a
  global dashboard).
- Leftover unused `date` import after that fix → removed.
- Demo script indexed dataframes by S14's layout; the country tab now
  renders two tables, shifting the comparison/provenance indices
  ([2]/[3] → [3]/[4]) → fixed.
- First demo run also printed the comparison MATRIX at index [2] where
  the merged coverage table was expected - same indexing cause.
- FINAL-VERIFICATION catch: the committed-shaped demo script still had
  2x RUF015 (single-element slice → `next(...)`) and a `ruff format`
  rewrap; fixed, the demo re-run, and the acceptance run regenerated
  from the final file states - the mid-unit "ruff clean" had been
  scoped to an earlier version of the demo script. Recorded here so the
  acceptance-run.txt header ("regenerated after final ruff fixes")
  stays honest.

## Deviations from the prompt

None.
