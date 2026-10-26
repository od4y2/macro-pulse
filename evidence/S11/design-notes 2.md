# S11 design notes

## Intended files (stated before editing; as executed)

- NEW `src/macropulse/lenses/digital.py` - the RQ2 lens
- NEW `tests/test_digital_lens.py` - 26 tests
- NEW `docs/DigitalLensMethodology.md`
- NEW `evidence/S11/` (acceptance, live demo + script + raw output, these notes)
- UPDATED `src/macropulse/catalog.py` - Findex coverage correction only
  (waves are 2024, not 2025; verified live) + `ruff format` pass over the
  file (formatting only, no semantic change)
- UPDATED `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`,
  `docs/decisions.md`, `docs/CoBuildLog.md`

## Design decisions

- **Reuse the S10 component-first pattern.** `digital.py` mirrors
  `labor.py`'s shape (Component / Profile / build_profile /
  RELATIONSHIPS / named missingness) instead of inventing a second lens
  architecture. The lens is pure: no DB reads, no clock reads, no
  side effects - persistence of lens output is deliberately out of scope
  (same boundary as S10).

- **Two dimensions, kept separate.** "Reach" (internet, mobile, account
  levels) and "inclusion gaps" (account_internet_gap,
  gender_account_gap) are never combined into a score. The S01
  no-composite-index rule is structural: profiles hold per-component
  identities; `RELATIONSHIPS` documents each relationship's formula and
  its caveats (adults-vs-population denominator mismatch; gender gap as
  conservative proxy vs the un-fetched male series).

- **`account_female` without extending the catalog.** The locked
  catalog's account-ownership fallback source (FX.OWN.TOTL.FE.ZS) is
  repurposed as the gender dimension - a source-level auxiliary, not a
  new catalog indicator. Adding indicators to the locked catalog would
  be out-of-scope for a lens unit.

- **Spearman, not Pearson, and n always returned.** A 10-economy panel
  with non-normal distributions (MEX account 53 vs KOR 96.9) makes rank
  correlation the honest default; `rank_covariation` returns `(rho, n)`
  so no coefficient can be quoted without its sample size. Ties share
  average ranks. Descriptive co-movement only - no causal direction.

- **`measurement_gap` is pure and takes `as_of`.** No clock reads
  inside the lens; the caller supplies the reference year. Never-observed
  dimensions are named, not silently zero. This is RQ2's blind-spot half:
  Findex wave-vs-annual asymmetry, the 2025 internet-vs-2024 everything
  staleness split, and JPN's 2021 alignment constraint all fall out of
  it (see `live-lens-demo.md`).

- **Validation closure.** `validate_lens_catalog` checks the three lens
  indicators exist and are `higher_is_better` - lens-consistent with the
  catalog's S09 direction annotations. The demo's alignment rule
  (intersection of OBSERVED periods) lives in the demo script /
  methodology doc, not the lens: the lens takes one coherent snapshot
  and refuses ambiguity; how a caller picks the snapshot is a caller
  policy, and the demo documents the honest one.

## Test coverage rationale (26 tests)

- Profile assembly: full profile, partial profile (missing components
  named), non-lens keys ignored, `component_not_fetched` for unfetched.
- Relationships: gaps computed, sign conventions, `None` when a needed
  component is missing (never guessed).
- Invariants: NULL requires reason; value must not carry one.
- Invalid inputs: no lens components, multi-period, multi-vintage,
  duplicate keys - all raise `LensError`.
- `rank_covariation`: perfect +/-1, hand-computed mixed case (0.6),
  tie handling, scale invariance, and rejection of length mismatch /
  <2 points / constant series.
- `measurement_gap`: asymmetric staleness, never observed, empty panel,
  frozen `as_of` (purity).
- Catalog consistency: lens keys exactly match the intended indicators.

## Errors found and fixed during the unit (truthful record)

- Mixed-covariation test expected 0.4; hand-recomputation of the rank
  correlation gives 0.6 - the test was wrong, not the code.
- Demo script bugs (caught live, pre-evidence): iterated
  `LENS_INDICATORS` keys vs indicator ids; `build_profile` argument
  order. Fixed; final output captured only after a clean run.
- Live data findings (not code bugs) are documented in
  `live-lens-demo.md`: WB NULL placeholder rows, JPN 2021 alignment,
  Findex 2024 waves.

## Deviations from the prompt

None. Ruff `RUF022` (`__all__` sort) auto-fixed, same as S10; catalog
correction verified against the live source before editing.
