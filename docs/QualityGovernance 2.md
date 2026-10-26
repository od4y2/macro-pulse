# Quality Governance (S07)

How normalized observations are graded, flagged, and tracked across
vintages. Implementation: `src/macropulse/quality/` (`assessment.py`,
`missingness.py`, `vintage.py`). Tests: `tests/test_quality.py`,
`tests/test_vintage_control.py`.

## Quality grades

Closed vocabulary, imported from the S03 API contract
(`macropulse.api.schemas.QUALITY_GRADES`) so schema and pipeline cannot
drift:

| Grade | Meaning | Assigned when |
|---|---|---|
| `flagged` | a validation flag fired | any flag on the record (outranks everything) |
| `ungraded` | not eligible for grading | evidence label is not `real` |
| `revised` | a newer vintage exists for this period | superseded identity, no flags |
| `official` | current, clean, real | otherwise |
| `preliminary` / `estimated` | **reserved** | never emitted - no source exposes release-stage metadata; assigning it would be fabrication |

Grade priority: `flagged` > `ungraded` > `revised` > `official`.

## Validation flags

Closed set, stored in `data_quality_flags` (append-only audit trail):

| Flag | Trigger |
|---|---|
| `missing_value` | value is NULL (explicit missingness surfaced, never filled) |
| `series_gap` | a period the frequency requires is absent; flagged on the latest record **before** the gap so the flag has a traceable row |
| `vintage_precedes_period` | vintage < period (impossible release chronology) |

Gap enumeration uses the frequency step (monthly 1 / quarterly 3 / annual 12
months) anchored on the series' first period - expected periods are
enumerated, never interpolated. The span is first..last record only: absence
before the first record is unknown, not missing.

## Missingness report (non-fabrication rules)

`missingness_report(records, frequency)` counts; it never fills, carries
forward, or interpolates:

- `n_observed` / `n_missing` / `n_gaps` / `n_expected` - direct counts
- `coverage = n_observed / n_expected` over the series' own span
- `missing_reasons` - reason histogram (every NULL carries a reason,
  enforced upstream by `ck_missing_requires_reason` and the S06 pipeline)
- Boundary: empty series -> `n_expected=0`, `coverage=0.0` (no division by
  zero, no silent 1.0)

## Vintage control and revision history (RQ4)

Observation identity is `(indicator, country, period, vintage, source)` -
a revision is a NEW row, never an update:

- `revision_history(session, indicator, country)` - all stored vintages per
  period, oldest first (read-only).
- `superseded_identities(...)` - identities with a newer vintage; those
  records grade `revised`.
- `revision_deltas(history)` - pure function; per period, the change
  between consecutive vintages. `absolute = to - from`;
  `relative = absolute / from` **only** when both values exist and the base
  is non-zero - a zero base yields `relative=None`, never a fabricated
  infinity. A value<->missing transition yields `absolute=None`.
- `apply_assessment(...)` - grades are UPDATEd (a judgement, not identity);
  flags are INSERTed (audit trail - re-running appends, history is never
  deleted). Flags insert only; there is no flag-deletion path.

### FRED / ALFRED realtime queries

`FredConnector.fetch_series(realtime_start=..., realtime_end=...)` restricts
the same endpoint to a realtime window: values as known during that window.
Repeated queries build a vintage chain - the same period under multiple
vintages - which S06 normalization now accepts (duplicate detection keys on
`(period, vintage)`, not period alone). Realtime queries are live-only:
requesting one without an API key raises rather than silently mocking.

## Traceability of rules

Every rule above is implemented in `src/macropulse/quality/` with the same
wording and is covered by tests; no magic constants (the only numbers are
the frequency steps, which are definitional).
