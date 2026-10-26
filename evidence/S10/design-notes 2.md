# S10 design notes

## Prior-state check

- git checkpoint: 59bd479 (S09), working tree clean
- baseline: 240/240 tests passing, DB healthy

## Scope decision

New `src/macropulse/lenses/` package: RQ lenses are a distinct layer from
metrics/quality - they consume the machinery and impose research-question
semantics. `lenses/labor.py` is the RQ1 lens:

- `SlackProfile` - the component-first per-(country, period, vintage) view
- `build_profile()` - assembly with coherence rules (one period, one
  vintage per profile)
- `youth_headline_gap_series()` - the divergence series
- `divergence_by_vintage()` - RQ1's vintage-revision question
- `RELATIONSHIPS` - definition texts (traceability), and the
  `youth_headline_gap` formula mirrored into FORMULAS

No DB changes; the lens is pure data assembly + arithmetic over
components. It deliberately has NO persistence of its own: profiles are
views; the components persist through the S03/S08 stores.

## Component-first (the unit's objective)

No index, no composite score, no weights. Each of the four components
(headline, youth, neet, enrollment) keeps its identity; the three
relationships are explicit arithmetic quantities, each documented in
RELATIONSHIPS with a stated reading. Enrollment is reported but NEVER
combined (composition vs welfare separation - combining it would embed a
causal judgment the S01 non-claims boundary forbids).

## Boundary decisions

- Gap AND ratio both reported: 2x ratio and 20pp gap describe different
  labor markets; neither collapses into the other.
- `youth_ratio` on zero headline -> None (2/0 not fabricated).
- Multi-period or multi-vintage components -> LensError (one snapshot per
  profile; vintage analysis compares separate profiles).
- No-vintage callers fall back to the period (documented).
- Non-lens components ignored; zero lens components rejected.
- Unfetched components -> `component_not_fetched` reason (vs the
  connector's own reasons for fetched-but-missing).

## Live demonstration (evidence/S10/live-lens-demo.md)

Full-component profiles on real WB + ILOSTAT data for USA/ZAF/BRA. Two
live findings: (1) ILOSTAT NEET lags WB unemployment by a year ->
alignment to latest common period is caller behavior, done explicitly;
(2) a misaligned assembly produced headline=None and the lens correctly
returned no relationships instead of fabricating - rules held on real data.

## Results

- 261/261 tests (21 new); ruff clean; smoke passed.
