# S18 Design Notes — End-to-End Integration and Historical Case

Unit objective: "Validate one full evidence chain and historical case."
Implementation date: 2026-09-24. All live calls below were made against the
World Bank API and the WHO page on that date; the full chain capture is in
`live-demo-output.txt` (DEMO PASSED, exit 0), produced by
`live-demo-script.py` — the exact script committed in this tree.

## What was built

- `src/macropulse/views/theme.py` — the design-token layer:
  - `COUNTRY_COLORS`: one hue per economy over exactly the S01 panel
    (10 distinct hues, entity-fixed — the map is identity, never rank).
  - `series_style(iso3, focus)`: focus lines wear the entity hue at
    `LINE_WIDTH_FOCUS` (2.5) and appear in the legend; context lines wear
    `CONTEXT_GREY` `#898781` at `LINE_WIDTH_CONTEXT` (1.75) and leave it.
  - `layout_update`: serif (Spectral) left-aligned title at x=0.01,
    transparent paper/plot backgrounds, hairline grid `#e1e0d9`, recessive
    axis ink, exactly one axis (no yaxis2, no overlaying).
  - `focus_label_point`: the last OBSERVED point of the focus series
    (a gap at the tail is never labeled — that would fabricate a position).
- `src/macropulse/case_study/macro_episodes.py` — the documented-episode
  registry: `MacroEpisode` (citation-mandatory construction; closed kind
  vocabulary `global_event|policy_event`; window arithmetic; the evidence
  label is always `external` — an episode is a document about an event,
  never an API observation) + `validate_macro_registry`.
- `src/macropulse/views/annotations.py` — pure overlay builders:
  `episodes_in_range` (overlap filter), `episode_overlays` (band shape in
  `EPISODE_WASH` `#e8e6dd` drawn BELOW the lines, callout anchored inside
  the band; the narrow-band rule — a window under 1% of the rendered range
  gets the wash but no callout, so a label can never claim more window
  than the source documents), band clipping to the rendered range,
  `episode_captions` (full citation: title, window, source name, verbatim
  source title, URL, published date, "drawn as observed"), and
  `assert_no_causal_wording` — a banned-phrase filter ("caused", "led to",
  "due to", "drove", "resulted in", …) run by construction on every
  caption the app renders.
- `app/dashboard.py` — the S18 visual language applied: serif editorial
  template, focus-and-context comparison view ("Focus country (others in
  grey)"), episode bands + callouts + citation captions on both chart
  views, direct label on the focus line's last observed point.
- `.streamlit/config.toml` — light mode pinned + Spectral/Inter fonts.
- `evidence/S18/live-demo-script.py` — the six-leg full-chain harness
  (disposable DB `macropulse_s18_demo`, created/migrated/dropped by the
  script; dev and Neon databases untouched).

## Design decisions

1. **FT-referenced, not cloned** (per the user's directive: "no need to
   mimic the whole style, just refer to its modern and professional
   look-and-feel"). Adopted: serif headline type over a sans body, hairline
   grid and recessive non-data ink, generous whitespace, one story per
   chart, direct labels over legend boxes, warm paper-white surface. Not
   adopted: the pink/claret brand palette (our hues are entity-fixed and
   CVD-validated — see `palette-validation.txt`), dark mode, and any
   layout chrome tied to a newsroom front page.
2. **Light mode pinned.** One mode rendered right beats two rendered
   approximately; the palette is validated against the light surface and
   the pin prevents an automatic dark flip from silently invalidating it.
3. **Color follows the entity, never its rank.** The focus switch
   (USA→CHN) repaints nothing: CHN keeps its teal, USA falls to grey.
   Proved in the render leg (`switch` checks).
4. **Episodes are data, not code comments.** The 2020 WHO window lives
   in a validated registry row with a live-verified citation
   (`live-verification.md`: the archived WHO timeline page, published
   2020-04-27, quote captured 2026-09-24). The caption template runs the
   causal-wording filter in production, so a wording regression raises
   at render time, not in review.
5. **The band is drawn as observed; no causal sentence exists.** The
   historical case shows the 2020 panel values and the documented window
   side by side (LEG 6) — juxtaposition on a chart, with the caption and
   the case text both stating that no causal connection is drawn.
6. **Palette WARNs are disposed by the relief rule, not dismissed.**
   The validator run (light surface) passes lightness, chroma, and the
   normal-vision floor; the protan 7.7 (amber↔green) and sub-3:1 contrast
   pairs sit in the legal floor band because every chart ships secondary
   encoding (direct label + legend + the comparison-matrix table view)
   and at most ONE colored line renders at a time. A darker amber was
   tried and made the pair worse (protan 4.9 — hard fail), so the
   lighter amber is the optimum.

## Manual inspection (provenance, labels, claims boundaries)

- **Provenance byte-check (LEG 3):** the API-served USA 2020 observation
  matches the stored row on all six fields — value by exact repr
  (`-2.081375977796`), unit `percent_per_year`, vintage `2026-09-24`,
  evidence `real`, grade `ungraded`, source `world_bank/NY.GDP.MKTP.KD.ZG`.
  Derived `gdp_real_growth.robust_z5` USA 2020 serves back exactly the
  stored `-8.91953625571653` with `formula_ref=robust_z`; its lineage
  (observation_ids `[6,7,8,9,10]`) prints DB-side only — the S13 pinned
  contract has no `inputs` field on MetricOut, so lineage is verified at
  the store, not through a schema change.
- **The exported comparison figure** (`figure-comparison-focus-chn.json`,
  focus CHN, inspected directly): Spectral serif title at x=0.01 in ink
  `#0b0b0b`; transparent plot/paper; hairline `#e1e0d9` grid; CHN in its
  entity teal `#0e95a6` width 2.5 — the only colored line, the only legend
  entry; the other nine economies in `#898781` width 1.75; the 2020 band
  as a `#e8e6dd` wash drawn below the lines; annotations are the direct
  label "CHN" in ink and the WHO callout in secondary ink — no text wears
  a series color. 66 points per trace, 1960–2025.
- **Labels:** the harness's undriven provenance tab (defaults BRA /
  account_ownership_pct — no data for that indicator in the demo store)
  renders the honest no-data info, not an empty chart: nothing inferred,
  nothing errored.
- **Claims boundaries:** the S16 briefing leg builds 30 claims from the
  served facts, all 30 validated, banned phrases in the rendered document:
  none. Example claim (provenance inline): "Real GDP growth (annual %)
  [gdp_real_growth] for BRA in 2025-01-01: 2.2857464902475
  percent_per_year (source: world_bank NY.GDP.MKTP.KD.ZG; vintage:
  2026-09-24; evidence: real; quality: ungraded)". The briefing reports
  the CURRENT picture (latest periods); the 2020 window is the case
  study's subject, not the briefing's.
- **The historical case (LEG 6):** all 10 economies' observed 2020
  real-GDP-growth values (USA −2.08, GBR −10.05, CHN +2.34 …) printed
  beside the WHO episode with its full citation and the sentence "The
  band and the values are shown together; no causal connection is drawn."

## Verification

- Tests: 48 new (theme 14, macro-episodes 15, annotations 19) — full
  suite **545 passed** (497 baseline + 48), 1 pre-existing third-party
  warning. Smoke: `python -m macropulse.smoke` OK. Ruff: clean
  (src, tests, app, evidence/S18).
- Live demo, six legs, all through production entry points, DEMO PASSED
  (exit 0): ingest (refresh CLI, live WB, 66 pts/series, exit 0) →
  derive (all 10 gates published, 63 derived pts each, 2020 row in all
  10) → serve (byte-check 6/6, derived + methodology served back) →
  render (22 checks on the served figure JSON: country 6/6, comparison
  8/8, captions 4/4, focus-switch 4/4) → brief (30/30 validated,
  persisted run 1) → case (10/10 economies observed).
- AppTest lessons that future units inherit: widgets take RAW values in
  `set_value()` (format_func labels crash the serialization); charts are
  found tree-wide via `at.get("plotly_chart")` with the full figure JSON
  in `el.proto.spec`; and every `at.run()` is followed by an `at.error`
  guard — `st.stop()` paths (service unreachable) do not raise an
  AppTest exception and would otherwise read as "0 charts".

## Not done / deferred (honest boundaries)

- The registry holds exactly ONE episode (the 2020 WHO window). More
  episodes are added when a unit needs them — none were invented to fill
  the registry.
- The demo chain runs the 10 S01 panel economies with gdp_real_growth
  only; full catalog/panel coverage (incl. 31 China provinces) remains
  the go-live directive, not this unit's.
- Dark mode: intentionally not implemented (decision 2).
- The figure export is the comparison chart only; the country chart is
  asserted in-harness and inspectable via the dashboard itself.
