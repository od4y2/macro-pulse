# S07 design notes

## Prior-state check

- git checkpoint: 0962964 (S06), working tree clean
- baseline: 117/117 tests passing, DB healthy

## Scope decision

Three pure-rule modules + persistence glue, no new tables (S03's schema
already had `data_quality_flags` and the release calendar reserved):

- `quality/assessment.py` - grade assignment + validation flags
  (closed vocabularies, documented priority order)
- `quality/missingness.py` - non-fabricating missingness report
- `quality/vintage.py` - revision history, superseded detection,
  revision deltas, grade/flag persistence

## Rule highlights (full table in docs/QualityGovernance.md)

- Grades: `flagged` > `ungraded` (not real) > `revised` (superseded) >
  `official`. `preliminary`/`estimated` are RESERVED - never emitted
  because no source exposes release-stage metadata; emitting them would
  be fabrication.
- Flags: `missing_value`, `series_gap` (anchored to the latest record
  BEFORE the gap so the FK has a row), `vintage_precedes_period`. Closed
  set; flags are INSERT-only (audit trail), grades are UPDATE (judgement).
- Gap enumeration: frequency steps (1/3/12 months) anchored on the
  series' first period; span is first..last record only (absence before
  the first record is unknown, not missing).
- Missingness report: counts only - no fill/interpolate/ffill path
  exists anywhere in the module (test-asserted by checking the
  dataclass field surface).
- Revision deltas: `relative=None` on zero base or value<->missing
  transitions - never a fabricated infinity.

## ALFRED realtime (deferred from S04, delivered here)

`FredConnector.fetch_series(realtime_start=, realtime_end=)` restricts
the same endpoint to a realtime window. Live-only: without a key it
raises rather than silently mocking (no hidden mocks for vintage data).

This required an S06 semantic fix in-unit: `normalize_series` rejected
duplicate periods, but a vintage chain legitimately repeats periods. The
duplicate check now keys on `(period, vintage)` - the same key as the DB
identity constraint. `infer_frequency` collapses duplicate periods before
gap computation (same-period vintages carry no spacing information).

## Live verification (evidence/S07/live-alfred-verification.md)

- UNRATE realtime windows: vintages track the requested window.
- PAYEMS Jan 2023: first-release 155,073 (Feb 2023 vintage) revised to
  154,773 (Apr 2024 vintage) = -300K benchmark revision, with
  `revision_deltas()` computing abs/rel from real data. This is RQ4's
  revision-transparency requirement demonstrated end-to-end on live data.

## What S07 does NOT claim

- The `release_calendar` table remains unpopulated: none of the three
  APIs expose a per-observation scheduled-release timestamp we can ingest
  today. `release_time` stays the documented retrieval-time proxy.
  Populating a curated release calendar would be future work requiring a
  sourced schedule (not fabricated).

## Results

- 159/159 tests (42 new: 25 quality, 14 vintage-control, 3 normalize
  semantic updates); ruff clean on all unit-intended files; smoke passed.
