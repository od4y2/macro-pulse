# Normalization Rules (S06)

How fetched connector series (`FetchedSeries` from `connectors/base.py`)
become governed `NormalizedObservation` rows. Implementation:
`src/macropulse/pipeline/normalize.py`. Tests: `tests/test_normalize.py`.

Normalization is **pure and deterministic**: same input series in, same
records out, no network, no clock reads (all timestamps come from the
series' own `retrieval_time`).

## Rule table

| Dimension | Rule | Failure mode |
|---|---|---|
| Country | `series.country_iso3` must be in the locked S01 panel (10 economies). No case-folding or aliasing at this layer — connectors already emit ISO3. | `NormalizationError` if outside panel |
| Period | Taken verbatim from the connector point. Connectors already unify dates (annual → Jan 1 of year; FRED monthly/quarterly → period start). | — |
| Unit | The catalog indicator's unit is canonical; values pass through **unchanged**. No unit conversion happens here (index→YoY etc. is S08 derived-metric territory and must be labelled). | — |
| Frequency | Inferred from the **median month-gap** between consecutive distinct periods: 1 -> `monthly`, 3 -> `quarterly`, 12 -> `annual`. Caller may pass explicitly (must be a legal `FREQUENCIES` value). Duplicate periods are collapsed before gap computation - a vintage chain (same period under multiple vintages, e.g. ALFRED realtime queries) legitimately repeats periods. | Error if < 2 distinct periods and not given; error if median gap is not 1/3/12 |
| Period identity | True duplicates are the same `(period, vintage)` pair twice. | Error on duplicate (period, vintage) |
| Seasonal adjustment | Caller-supplied, defaulting to the catalog indicator's value. Sources differ (e.g. FRED CPI is SA while WB CPI is NSA), so the *applied* value is stored per observation. | Error if not a legal `SEASONAL_ADJUSTMENTS` value |
| Vintage | Per-point: FRED points carry `realtime_start`; WB/ILOSTAT points carry the retrieval date (snapshot semantics — the APIs serve only the current revision). | — |
| Release time | `retrieval_time` of the fetch, stored per record. **Documented proxy**: none of the three endpoints expose a per-observation release timestamp. Refined in S07 (release calendar / vintage control). | — |
| Missingness | `value=None` passes through with its connector `missing_reason`. Never imputed, interpolated, filled, or dropped. | Error if value is None with no reason (hidden missingness); error if a value carries a reason |
| Evidence label | Passed through from the series (`real` / `mocked` / …); validated against the S01 evidence vocabulary. | Error if invalid |
| Quality grade | `ungraded` at this stage. Grading is S07's responsibility. | — |
| Source | `source_system` + `source_code` recorded from the series; DB rows reference `source_catalog.id` via `persist_normalized`. | — |

## Frequency inference rationale

Median (not minimum or mode) gap is used so that a **single** missing
period inside an otherwise regular series does not break inference — e.g.
gaps `[3, 3, 6]` still infer `quarterly`. The gap itself is *preserved*
as missingness upstream; normalization never repairs it. A median gap
outside {1, 3, 12} (e.g. mixed-frequency data, or a 4.5-month median from
irregular spacing) is an error rather than a guess — the caller must pass
frequency explicitly or fix the fetch.

## Vintage semantics per source (connector-enforced)

- **FRED**: `vintage = realtime_start` per observation (true first-release
  vintage where the API provides it).
- **World Bank / ILOSTAT**: these APIs serve only the current snapshot; the
  connectors (S06 fix) stamp every point `vintage = retrieval date`. The
  observation identity `(indicator, country, period, vintage, source)`
  therefore changes per refetch, which is exactly the behavior the RQ4
  revision-transparency design requires.

## Persistence

`persist_normalized(session, records, source_id)` writes
`NormalizedObservation` rows. Duplicate
`(indicator_id, country_iso3, period, vintage, source_id)` identities are
rejected by the `uq_observation_identity` unique constraint; a NULL value
without `missing_reason` is rejected by `ck_missing_requires_reason`.

## Known limitations (forward-referenced, not hidden)

- FRED pagination (>1000 observations per series) is not yet handled; long
  histories may be truncated at fetch time (connector-level follow-up).
- ILOSTAT SDMX filtering is client-side; the full dataflow is downloaded
  (performance follow-up, correctness unaffected).
- `release_time` is a retrieval-time proxy; S07 adds vintage control and
  grading but per-observation release timestamps still require the release
  calendar (S03 table, not yet populated) - see docs/QualityGovernance.md.
