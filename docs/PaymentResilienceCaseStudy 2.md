# Payment Resilience Case Study Methodology (S12, RQ3)

RQ3: *What do payment-outage episodes reveal about resilience
measurement in digitized healthcare systems, for the case-study subset
of the panel?*

Implementation: profile lens `src/macropulse/lenses/payment.py`; case
machinery `src/macropulse/case_study/` (episodes, China healthcare
geography). Tests: `tests/test_payment_lens.py`,
`tests/test_case_study.py`. Live verification:
`evidence/S12/live-verification.md`; live demo:
`evidence/S12/live-demo-script.py` (+ raw output).

## The two halves of RQ3

1. **The payment profile** (`lenses/payment.py`) - observed
   payment-digitization levels with macro context. Component-first
   (S10/S11 pattern): a `PaymentProfile` holds
   `digital_payments_made_pct` (WB Findex `g20.any`, % of adults, survey
   waves) and `health_expenditure_pct_gdp` (WB `SH.XPD.CHEX.GD.ZS`, % of
   GDP) each with its own identity, period, vintage, and named
   missingness. **No arithmetic relationship is defined between them**
   (see `COMBINATION_POLICY`): payment prevalence and health spending
   are different constructs with different denominators; a ratio or gap
   would embed a dependence claim the evidence does not support
   (S01 non-claims). The catalog itself marks health expenditure
   "macro context for the case study only; not a resilience measure
   itself."

2. **The bounded China healthcare geography case** (`case_study/`) -
   what the profile's levels cannot see: officially documented outage
   episodes and the healthcare-resource exposure they suspend.

The case-study subset is `("CHN",)` (`CASE_STUDY_COUNTRIES`) - RQ3 goes
deep on one economy, not wide on ten.

## Episode governance (`case_study/episodes.py`)

An **episode** is a documented window during which a payment system used
by healthcare providers was unavailable. Episodes are documents, not
statistical observations:

- Every episode carries the `external` evidence label (the S01
  vocabulary's "approved file or third-party source outside the primary
  APIs") - **never `real`**; the constructor rejects any other label.
- Citation is mandatory: source organization, **verbatim document title
  in the original language**, URL, publication date. An uncited episode
  fails construction - an episode without a source is a fabrication.
- Closed kind vocabulary: `scheduled_maintenance` vs `unplanned_outage`.
  A scheduled episode must have been announced on or before its window
  starts (that is what makes it scheduled); an unplanned episode may be
  published after the window (post-incident reports).
- Windows are timezone-aware - the sources state local time, so the
  registry stamps China Standard Time (UTC+8, no DST). A naive window is
  ambiguous and rejected.

Registry contents (verified live 2026-08-29, quotes in
`live-verification.md`): four Yunnan announcements - two recurring
48-hour year-end rollover suspensions of the provincial
medical-insurance information platform (2024-12-31 -> 2025-01-02 and
2025-12-31 -> 2026-01-02, both 20:00->20:00), an 8-hour upgrade window
(2026-03-24 22:00 -> 03-25 06:00), and a 2-hour upgrade window
(2026-06-12 23:00 -> 06-13 01:00). A 2023-dated rollover notice exists
but is a scanned PDF with no text layer - not machine-verifiable, so
not recorded.

## The computed blind spot (`observation_alignment`)

RQ3's measurement question is answered with arithmetic, not assertion.
For each episode and each catalog frequency (`monthly`, `quarterly`,
`annual`), the alignment report computes:

- **periods spanned** - which observation periods the window touches;
- **boundary straddled** - whether the window crosses a period boundary
  (splitting the event across two observations);
- **duration share of period** - episode hours / period hours;
- **resolvable** - false if the window straddles a boundary OR occupies
  under 1% of a period. The 1% threshold is a documented presentation
  convention: an event shorter than 1% of an observation period cannot
  plausibly move a level aggregate beyond its own measurement noise.

Findings on the verified registry:

- The two 48-hour year-end rollovers straddle **every** catalog
  frequency boundary (Dec/Jan, Q4/Q1, year) and occupy 0.55% of an
  annual period - **unresolvable at every catalog frequency**. The
  recurring suspension is precisely timed to fall in the crack between
  statistical periods.
- The 8-hour March window is resolvable only against the monthly grid
  (1.08% of a month); the 2-hour June window is unresolvable at every
  frequency.

Layered on this mechanical fact, the **construct gap** (stated here,
not computed, because it is a fact about the indicator list): no
catalog indicator measures payment-system operational continuity at
all - the 12 indicators are levels, flows, and prices. Resilience to
payment outages is systematically invisible to official statistical
series; the only records are non-statistical government announcements.

## China healthcare geography (`case_study/china_health.py`)

Resource records quantify what a provincial platform suspension
suspends. Same governance as episodes: citation mandatory, `external`
label, closed metric vocabulary (`institutions`, `beds`,
`beds_per_1000`), measure definitions pinned in per-record notes.

Verified records (2026-08-29, PDF text extraction where noted):

| Region | Institutions (2023) | Beds (2023) | Beds/1,000 | Source |
|---|---|---|---|---|
| CHN national | 1,070,785 | 10,174,000 | 7.23 | NHC 2023 bulletin (PDF extraction) |
| Beijing | 12,518 | 149,971 (authorized) | 6.87 (authorized) | Beijing 2023 bulletin (PDF extraction) |
| Yunnan | 28,765 | 359,900 | - (not verified) | Yunnan Daily, 2024-09-25 |

Comparability caveats are recorded, never smoothed over:

- Beijing reports **authorized** beds (编制床位, 149,971; actual 实有
  138,825) while the national figure counts total institution beds -
  different measures, not pooled into one comparison.
- Yunnan's per-1,000 rate was not directly verified and is not recorded
  (the population denominator is not in any verified source here);
  29 of 31 provinces are explicitly listed as unrecorded
  (`unrecorded_provinces`) - named missingness, never imputed.
- The exposure report (`exposure_report`) carries the record year next
  to the figures: the verified Yunnan records (2023) predate the
  episodes (2024+), and the report says so rather than implying
  at-episode-year values.

## Claims boundary (S01)

- Episodes are **reported events** from official announcements - no
  claim about healthcare outcomes during the windows, no causal link
  between digitization level and resilience.
- The alignment report describes where events land on observation grids;
  it does not claim any indicator *should* have moved.
- Exposure (institutions/beds) describes scale, not harm: no inference
  that patients were denied care (the announcements themselves describe
  manual-reimbursement workarounds).
- The profile's levels are descriptive; nothing ranks countries by
  resilience.
