# S09 live manual check: standardization + gates on real WB data (2026-08-29)

Live World Bank unemployment (SL.UEM.TOTL.ZS, 2000-2025, evidence_label
`real`, external source) standardized with a 5-year trailing robust
window and gated with the default thresholds:

```
USA: 26 points 2000-01-01..2025-01-01 label=real coverage=1.000
  latest 2025-01-01: score=-0.47 (deviation=0.47, occupancy=5)
  gate: published=True reasons=()
ZAF: 26 points 2000-01-01..2025-01-01 label=real coverage=1.000
  latest 2025-01-01: score=-0.00 (deviation=0.00, occupancy=5)
  gate: published=True reasons=()
```

Manual inspection notes (provenance/labels/claims boundaries):

- Both series are `real` (live WB API, no key needed) with full coverage;
  both gates pass with empty reason lists.
- Cross-country comparability works as documented: USA (~4%) and ZAF
  (~32%) unemployment land near zero because each score is relative to
  the country's OWN window median - the score answers "unusual for this
  country", not "high vs. other countries" (docs/StandardizationRules.md).
- USA 2025 reads 0.47 MADs above its own 2021-2025 median -> direction
  adjustment (lower_is_better) makes the score -0.47 (slightly
  unfavorable). No causal or welfare claim is made or implied.
- Points were sorted chronologically before standardizing: the WB API
  returns newest-first, and standardization preserves input order by
  design (the pipeline sorts; direct callers must too).
