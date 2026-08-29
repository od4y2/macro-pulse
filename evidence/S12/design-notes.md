# S12 design notes

## Intended files (stated before editing; as executed)

- NEW `src/macropulse/lenses/payment.py` - the RQ3 profile lens
- NEW `src/macropulse/case_study/__init__.py`
- NEW `src/macropulse/case_study/episodes.py` - episode registry (4
  live-verified Yunnan episodes) + observation-alignment machinery
- NEW `src/macropulse/case_study/china_health.py` - verified China
  healthcare-geography records + exposure reports
- NEW `tests/test_payment_lens.py` (18 tests)
- NEW `tests/test_case_study.py` (41 tests)
- NEW `docs/PaymentResilienceCaseStudy.md`
- NEW `evidence/S12/` (acceptance-run.txt, live-verification.md,
  pdf-extraction.txt, live-demo-script.py, live-demo-output.txt, these
  notes)
- UPDATED `TASKS.md`, `STATUS.md`, `SESSION_STATE.md`,
  `docs/decisions.md`, `docs/CoBuildLog.md`
- No catalog or schema changes: both RQ3 indicators
  (`digital_payments_made_pct`, `health_expenditure_pct_gdp`) were
  locked in S02 and live-confirmed in S05.

## Design decisions

- **Two modules for two kinds of truth.** The payment PROFILE is
  statistical (lens layer, same pattern as S10/S11); the EPISODES are
  documents (new `case_study` package). Episodes carry the `external`
  evidence label, never `real` - an announcement is not an API
  observation, and blurring that would mislabel provenance.

- **Citation as a constructor rule.** An `Episode`/`ResourceRecord`
  cannot be instantiated without source organization, verbatim source
  title, URL, and publication date. "No fabrication" moves from review
  discipline to type-system enforcement - an uncited episode cannot
  exist.

- **No arithmetic between payment prevalence and health spending**
  (`COMBINATION_POLICY`, tested by asserting the profile has no
  properties at all). RQ3's relationships live at the episode level;
  combining the two levels would embed a dependence claim.

- **The blind spot is computed where it can be, stated where it cannot.**
  `observation_alignment` computes pure arithmetic (periods spanned,
  boundary straddle, duration share) - this catches the strongest
  finding: the recurring year-end 48h rollover straddles every catalog
  frequency boundary and is unresolvable at every frequency. The
  construct gap (no indicator measures operational continuity) is a
  fact about the indicator LIST, not arithmetic, so it is documented in
  the methodology rather than faked as a "computed" check.

- **Timezone-aware windows.** The announcements state local (Beijing)
  time; naive datetimes would be ambiguous, so the registry stamps China
  Standard Time (UTC+8, no DST) and rejects naive or mixed-timezone
  windows. DTZ001 surfaced this during linting - the honest fix was the
  timezone, not a noqa.

- **Scheduled vs unplanned is kind-dependent validation.** A
  `scheduled_maintenance` episode must have been announced on/before its
  window (that is what "scheduled" means); an `unplanned_outage` may be
  published after the window (post-incident report). A blanket
  "published before end" rule would have rejected legitimate
  post-incident citations.

- **Named missingness at the registry level.** 29 of 31 provinces have
  no verified record and are listed explicitly by
  `unrecorded_provinces()`; the exposure report carries the record year
  (2023) next to figures for 2024+ episodes; Yunnan's per-1,000 rate is
  absent because no verified population denominator was obtained.

- **Measure comparability pinned per record.** Beijing's authorized
  beds (编制) vs the national total-bed count are recorded with notes;
  they are not pooled into one comparison.

## Live findings (2026-08-29)

1. The Yunnan medical-insurance platform's 48-hour year-end suspension
   is RECURRING (2024 and 2025 windows verified; a 2023 notice exists
   but is a scanned image - excluded, not machine-verifiable).
2. WB live data: CHN `g20.any` has a 2024 wave (88.72% adults) while
   `SH.XPD.CHEX.GD.ZS` stops at 2023 - the demo shows BOTH alignments
   (common-period 2021 profile; latest-wave 2024 profile with health
   expenditure named `not_observed_at_period`) instead of silently
   picking one.
3. Four of six attempted source verifications failed mechanically
   (scanned PDF, HTML-instead-of-PDF, TLS mismatches) - each failure is
   recorded in `live-verification.md` with its consequence (source not
   recorded). Excluded data is named, not imputed.

## Errors found and fixed during the unit (truthful record)

- `duration_share_of_period` was rounded to 6 decimals, breaking exact
  test arithmetic - rounding removed; the raw ratio is reported.
- First `resolvable` definition treated boundary-straddling as
  "resolvable" (len(periods) > 1); straddling splits the event across
  two observations, making it LESS visible - semantics inverted to
  straddle => not resolvable.
- Blanket `published <= end` rule would have rejected post-incident
  reports of unplanned outages - replaced with the kind-dependent rule.
- `dir(PaymentProfile)` in a test returned no public names (dataclass
  fields are instance attributes, not class attributes) - the
  no-relationship test now checks `vars()` for property objects.
- C408/DTZ001/RUF022 etc. from ruff - fixed (dict literals, timezone
  awareness, sorted `__all__`).

## Deviations from the prompt

None. `pypdf` was pip-installed into the project venv for PDF text
extraction (a read-only verification tool, not a runtime dependency;
pyproject dependencies unchanged).
