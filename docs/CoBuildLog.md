# Co-Build Log

Append student decisions, AI assistance, manual verification, and learning evidence by unit.

## S01 (2026-08-19)
- Student decisions: selected the balanced global ten-economy panel and confirmed all four research-question lenses (RQ1-RQ4); RQ3 scoped as a case study.
- AI assistance: drafted `src/macropulse/scope.py` (locked scope module), `tests/test_scope.py` (16 tests: normal/boundary/missing/invalid), `docs/ResearchScope.md`, and evidence.
- Manual verification: student reviewed concern list (plaintext API key in local setup scripts, uncommitted .gitignore, broken editable install) before unit start.
- Learning evidence: diagnosed why `python -m macropulse.smoke` failed while pytest passed (Anaconda Python 3.13.14 skips `.pth` files carrying the macOS `hidden` BSD flag; a local process re-applies the flag to `.venv`). Recorded as an E01 defect with `PYTHONPATH=src` workaround.

## S02 (2026-08-19)
- Student decisions: approved moving to S02 after reviewing S01 handover concerns; approved the module/source-system mapping (WB primary cross-panel, FRED US-first, ILOSTAT youth fallback).
- AI assistance: drafted `src/macropulse/catalog.py` (12 indicators + validation), `src/macropulse/catalog_report.py`, `tests/test_catalog.py`, `docs/IndicatorCatalog.md`, evidence.
- Manual verification: catalog report inspected for provenance, verification labels, and claims boundaries; 7 unverified codes surfaced explicitly rather than hidden.
- Learning evidence: the no-whitespace source-code validation rule caught 2 annotated codes mid-unit, demonstrating tests-as-contract; TBD placeholders used instead of inventing uncertain API codes.

## S03 (2026-08-19)
- Student decisions: installed Docker manually (29.7.2); reaffirmed PostgreSQL-only (local Docker + cloud for Vercel target).
- AI assistance: drafted `src/macropulse/db/` (engine/session + 11 ORM entities), Alembic scaffold + initial migration, `src/macropulse/api/schemas.py` contract, 18 tests, `docs/DatabaseContract.md`, evidence.
- Manual verification: `\dt` output inspected (all 11 tables + alembic_version); migration applied and downgrade path documented.
- Learning evidence: governance rules expressed as executable schema constraints (CHECK missing_reason, native enums, unique observation identity) and caught by live-DB integration tests rather than prose-only rules.

## S04 (2026-08-19)
- Student decisions: proceed with S04 in mocked/no-key mode (`.env.local` has placeholder FRED key only).
- AI assistance: drafted `src/macropulse/connectors/{__init__,fred,persist}.py`, 18 tests, shared DB fixture in `tests/conftest.py`, evidence.
- Manual verification: reviewed fixture values are obviously-round and labelled `mocked`; confirmed no test touches the network (MockTransport) and no live API call was claimed.
- Learning evidence: httpx.MockTransport lets live-mode code paths be tested deterministically; "." missingness handling demonstrates "no hidden missingness" as code, not prose.

## S05 (2026-08-19)
- Student decisions: none required this unit (no-key APIs); proceeded with live WB/ILOSTAT verification.
- AI assistance: drafted worldbank.py + ilostat.py connectors, shared connector base, source-generic raw persistence, 24 tests, reproducible audit script; corrected the catalog with live-verified codes.
- Manual verification: live audit output inspected line-by-line (14/14 OK); null-value patterns confirmed for Findex sparse series; dataflow registry consulted for correct ILOSTAT codes.
- Learning evidence: the live audit caught three bugs mocked tests missed (WB date param, ILOSTAT timeout, lowercase ISO3 acceptance) - why live verification beats mocks alone; and the unverified-flag discipline caught a genuinely wrong ILOSTAT code from S02.

## S05 follow-up: live FRED verification (2026-08-19)
- Student decisions: provided the FRED API key; asked for verification.
- AI assistance: wrote the key into gitignored `.env.local` after the user's manual edit did not land (file still had the placeholder); live-verified all FRED codes; corrected the invalid German GDP mirror code via FRED series search.
- Manual verification: audit output inspected - 18/18 OK including FRED live mode.
- Learning evidence: live verification again caught a wrong code (CLVMNACSCAB1GQ missing the DE suffix) that looked plausible on paper.

## S06: normalization pipeline (2026-08-19)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the rule table (docs/NormalizationRules.md); implemented pure `normalize_series()` + `persist_normalized()`; found and fixed the WB/ILOSTAT vintage=period bug flagged during S05 review; wrote 23 tests including DB roundtrip and duplicate-identity rejection.
- Manual verification: acceptance run inspected - 117/117 tests, ruff clean, smoke passed.
- Learning evidence: the vintage bug showed why "documented semantics" must match code before downstream layers build on them - normalization would have silently produced wrong vintages for two of three sources.

## S07: quality, missingness, vintage control (2026-08-29)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the grade/flag vocabularies and priority rules; implemented assessment/missingness/vintage modules; enabled ALFRED realtime windows in the FRED connector (live-only); rekeyed S06 duplicate semantics to (period, vintage); live-verified realtime queries including a genuine PAYEMS revision chain (-300K on Jan 2023).
- Manual verification: acceptance run inspected - 159/159 tests, ruff clean, smoke passed; live ALFRED output reviewed (vintage stamps track windows; revision deltas computed from real values).
- Learning evidence: the reserved-grade decision (preliminary/estimated never emitted) shows the no-fabrication principle applying to metadata, not just values - a plausible-looking label without source backing is still a fabrication.

## S08: time-series transformations (2026-08-29)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: extended the audit-era transforms starter into the five families (YoY, MoM, pp-change, annualization, rolling mean) with a closed missing-reason vocabulary; built the derived-metric engine on the untouched S03 schema; wrote 40 tests including a full DB vertical slice (normalized -> latest vintage -> yoy -> derived rows with lineage).
- Manual verification: acceptance run inspected - 199/199 tests, ruff clean, smoke passed; lineage and version rows inspected in the DB slice.
- Learning evidence: the zero_base/non_positive_base decision shows missingness policy extending to derived layers - "the number is undefined" must be recorded, not papered over with 0 or inf.

## S09: robust standardization and coverage (2026-08-29)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the robust fixed-window scaling (median/MAD, recorded occupancy, zero_scale as missing), the catalog direction field with policy_rate neutral, ratio-of-sums panel coverage, and condition-based publication gates; added the robust_z formula + latest_vintage_records loader; live manual check on real WB unemployment USA/ZAF.
- Manual verification: acceptance run inspected - 240/240 tests, ruff clean, smoke passed; live scores inspected for semantics (USA -0.47 vs ZAF 0.00 at very different unemployment levels proves the own-history semantics).
- Learning evidence: the policy_rate-is-neutral decision shows the claims boundary applying to presentation conventions - a sign flip is a judgment about what counts as favorable, and judgment belongs to the reader, not the pipeline.

## S10: labor slack and youth transition lens (2026-08-29)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the component-first RQ1 lens (profiles, three documented relationships, enrollment reported-not-combined); implemented build/series/vintage-divergence functions with coherence and missingness rules; live demo on real WB+ILOSTAT data for USA/ZAF/BRA.
- Manual verification: acceptance run inspected - 261/261 tests, ruff clean, smoke passed; live profiles inspected (ZAF gap 28pp vs neet-excess 2.3pp shows why both gap and withdrawal measures matter; misalignment produced honest Nones).
- Learning evidence: the enrollment decision shows the non-claims boundary governing analysis design - the moment a formula encodes "more education means less youth unemployment," the platform has made a causal claim by arithmetic.

## S11: digital reach and inclusion gap (2026-08-29)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the two-dimensional RQ2 lens on the S10 component-first pattern (reach levels vs inclusion gaps, Findex female source as aux component); implemented build/rank-covariation/measurement-gap with coherence and missingness rules; ran the live 10-economy WB demo with observed-period alignment; corrected the catalog's Findex wave years against the live source.
- Manual verification: acceptance run inspected - 287/287 tests, ruff check + format clean, smoke passed; live panel inspected (MEX -30.1pp account-internet with -5.6pp gender gap - levels alone would not show this; JPN aligned to 2021 shows the stalest-dimension binding).
- Learning evidence: the placeholder-rows finding shows why "returned" and "observed" are different words - an API row with a NULL value looks like data in a response list, and treating returned periods as observations would have fabricated a full panel of nothing.

## S12: payment resilience and healthcare case study (2026-08-29)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the two-part RQ3 implementation (payment profile lens; citation-mandatory case-study package); live-verified four Yunnan medical-insurance platform suspension announcements (verbatim quotes) and extracted China healthcare figures from official PDFs; built the observation-alignment machinery that computes the blind spot; ran the live demo combining WB profiles with the episode registry.
- Manual verification: acceptance run inspected - 346/346 tests, ruff check + format clean, smoke passed; live outputs inspected (the year-end rollover straddling every boundary is visible in the alignment table; the exposure report carries the 2023 record year next to 2024+ episodes).
- Learning evidence: the scanned-PDF exclusion shows the no-fabrication rule's teeth - a 2023 rollover notice exists, everyone knows it happened, but it is not machine-verifiable, so the registry holds four episodes instead of five and the gap is documented instead of filled.

## S13: FastAPI query service (2026-09-01)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the service layout (app factory with injectable session factory, per-request session dependency, data router, methodology router); implemented typed/paginated/filterable endpoints over the normalized store with the S03-pinned response contract unchanged; replaced the starter health stub with a truthful DB-backed health check and upgraded smoke to boot the assembled service; live demo fetching real WB data through the S06 pipeline into a disposable database and querying the running service over HTTP.
- Manual verification: acceptance run inspected - 368/368 tests, ruff check + format clean on unit files, schemas.py pin verified unchanged, smoke passed; live HTTP demo inspected (full provenance on every observation row, closed-vocabulary 422 listing the legal values, X-Total-Count distinguishing "empty page" from "no data", robust_z lineage resolving through /methodology).
- Learning evidence: the `ruff format` incident on the pinned schemas file shows why "the contract is pinned" must be a checkable property, not an intention - tooling that helpfully reformats can silently mutate a contract, and the byte-identity check in the acceptance run is what caught it.

## S14: Streamlit country and comparison views (2026-09-01)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the views layer (typed query-service client with pagination + pure view-model assembly; thin Streamlit rendering); implemented the three views (country current-picture with full provenance columns, comparison chart/matrix/coverage counts, provenance vintage-chain view with latest flags); installed streamlit+plotly (the 10.5 MB wheel needed a curl resume workaround on this network); ran the real dashboard script against the live service through Streamlit's AppTest harness for evidence.
- Manual verification: acceptance run inspected - 394/394 tests (26 new), ruff check + format clean, smoke passed; AppTest run inspected (0 exceptions, 3 tabs, 4 dataframes, 11x10 real-WB comparison matrix, provenance chain with vintage flags, view switches, empty and unreachable-service states).
- Learning evidence: the tab-local st.stop() bug shows Streamlit's execution model biting the governance rules - an empty selection in one view silently deleting the other two views is exactly the "hidden missingness" the contract forbids, achieved by accident rather than intent.

## S15: visual explanation and quality labels (2026-09-03)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the pure label layer (freshness arithmetic in frequency steps with the 2-step convention, badges that decorate never replace, chart captions counted from rendered data, coverage+freshness merge with no_data defaults); wired the dashboard (as-of sidebar control, labels legend, freshness tables in country and comparison views, badge columns, per-point hover provenance, catalog-driven limitations expanders); ran the live AppTest demo including the computed-label proof and captured the acceptance run.
- Manual verification: acceptance run inspected - 416/416 tests (22 new), ruff check + format clean on unit files, pinned schemas.py untouched, smoke passed; AppTest run inspected (0 exceptions; BRA current at 1.67 steps; 10 economies merged coverage+freshness all current; as-of 2028-01-01 flips every state to lagging at 3.0 steps; ungraded badges honestly shown because the S07 grading step has not been run on the dev DB).
- Learning evidence: the ungraded-badge moment in the live demo shows the honest-rendering rule paying off - it would have been trivial to run the S07 grader on the dev DB to make the demo prettier, but that would have been out-of-scope data manipulation for cosmetics; the demo shows `◌ ungraded` because that is what is stored, and the legend explains why.

## S16: structured AI briefing (2026-09-03)
- Student decisions: none this unit (continued per approved plan). Standing directive reconfirmed: full indicator catalog + all provinces/economies at go-live (memory updated).
- AI assistance: designed the briefing layer (validated facts JSON with real/missing/excluded partition; atomic claims with S03-identity citations and a closed 8-reason rejection vocabulary; deterministic prose assembly with a banned-phrase rejection layer; briefing_runs/briefing_claims persistence incl. rejected claims); implemented the no-key deterministic generator (model recorded honestly); ran the live demo over the running service and dev DB.
- Manual verification: acceptance run inspected - 451/451 tests (35 new), ruff check + format clean on unit files, smoke passed; live demo inspected (110 real obs -> 20 validated claims; rendered document passes check_prose with zero findings; tampered value and causal sentence both rejected; run row persisted with 21 claims, 1 rejected, evidence_refs JSON round-tripped).
- Learning evidence: the banned-disclaimer catch shows why the rejection layer must be mechanical - the first footer draft ("no forecasts, no investment advice") violated the unit's own check, and only an unexempted machine check could catch that a well-meaning disclaimer and a violating sentence are textually identical.

## S17: scheduling, logging, and operational recovery (2026-09-10)
- Student decisions: none this unit (continued per approved plan).
- AI assistance: designed the ops layer (revision-diff persistence, stdlib scheduler with the polling-convention disclaimer, closed run/series/failure vocabularies, retry boundary 429/5xx/transport-only, per-series commit isolation, refresh_runs append-only audit with interrupted marking); extended the catalog with structured SourceRef.countries coverage; wrote the CLI (one-shot/cron-able, daemon, dry-run, exit codes 0/1/2) and docs/OpsRunbook.md; ran the live demo on a disposable database and captured the acceptance run.
- Manual verification: acceptance run inspected - 497/497 tests (46 new), ruff clean on unit files, pinned schemas.py untouched (0 diff lines), smoke passed, alembic head c9af6b543047; live demo inspected (run A partial: 10 WB series ok at 66 points each, FRED no_api_key, exit 1; run B recovery with the key from .env.local: FEDFUNDS live, 866 monthly points 1954-07..2026-08, exit 0; run C idempotent: all new_periods=0, exit 1; 1,526 stored rows all labelled real; three audit rows with correct triggers/statuses; demo DB dropped, dev DB untouched).
- Learning evidence: the no_api_key decision shows the layer's honesty rule paying off twice - the easy path was to let the scheduled job use the S04 no-key fixture (it "works" and looks like data), and the demo instead records a failure and proves recovery by re-running with the key; the idempotency proof (run C writing zero rows while re-fetching 660 live points) is the visible consequence of choosing revision-diff persistence over snapshot rewrites.

## S18: end-to-end integration and historical case (2026-09-24)
- Student decisions: the visual refresh is FT-REFERENCED, not cloned ("no need to mimic the whole style, just refer to its modern and professional look-and-feel") - adopted serif headline/hairline grid/recessive ink/whitespace/direct labels, rejected the newsroom palette and dark mode; folded into S18 by the student's instruction.
- AI assistance: built the token layer (entity-fixed ten-hue palette with unknown-country rejection, focus/context styling, serif left-aligned one-axis layout, last-observed-point labels) and validated the palette with the dataviz validator script (WARNs disposed under the relief rule, documented with the failed darker-amber iteration); pinned light mode; built the episode registry (citation-mandatory, always external, live-verified WHO 2020 window) and the pure overlay builders with the render-time causal-wording filter; applied the language to the dashboard (focus-and-context comparison view, episode bands/callouts/captions); wrote and debugged the six-leg full-chain harness on a disposable database and captured the acceptance run.
- Manual verification: acceptance run inspected - 545/545 tests (48 new), ruff clean on src/tests/app/evidence, pinned schemas.py untouched (0 diff lines vs 63d867f), smoke passed; live demo inspected all six legs (ingest exit 0 with 66 live points x 10 economies; all 10 gates published with 63 derived points each and a 2020 row each; byte-check 6/6 fields with the value compared by exact repr; the AppTest-driven dashboard passing all 22 render checks including the USA->CHN focus switch and both citation captions; 30/30 briefing claims validated with zero banned phrases; 10/10 observed 2020 values printed beside the documented WHO window with the no-causal-connection sentence); the exported comparison figure inspected field by field (CHN sole colored line in its own teal, nine grey context lines, wash band below the lines, ink-only annotation text); demo DB dropped, dev and Neon DBs untouched.
- Learning evidence: the 0-figures mystery is the unit's engineering lesson - the manual test and the harness ran the same widget sequence with opposite results, and the eventual diagnosis came from instrumenting the harness to print what the app actually rendered (info messages, dataframes) instead of reasoning about it; the root causes were invisible assumptions (widget defaults are alphabetically-first, and st.stop() paths raise no AppTest exception), and both fixes are guards in the harness now (explicit USA/indicator selection, at.error assertion after every run) so neither failure mode can masquerade as "the chart didn't render" again.

## S19: research report and methodology publication (2026-10-11)
- Student decisions: none inside the unit boundary (the report's structure came from the unit contract); mid-unit, the student chose the two deployment decisions by question prompt - a curated deploy branch so curriculum material stays out of the public GitHub repo, and the in-process service thread over a repository-module rewire.
- AI assistance: built the typeset formula registry (14 entries, bidirectional registry anchoring, code anchors for the two registry-less quantities, structural LaTeX checks, notation-presence checks); built the four-dimension QA layer and the deterministic MathJax HTML renderer; wrote both test files (registry soundness + tamper reporting; QA dimensions + renderer structure + the real-report acceptance gate); re-verified every Findings number against its cited evidence file before writing the report; wrote the report, the QA runner, and the session's deployment fix (orphan deploy branch, secrets bridge, in-process service) outside the unit's file boundary on the deploy branch only.
- Manual verification: acceptance run inspected - 598/598 tests (53 new), the deliverable gate `test_real_report_passes_qa` green, smoke passed, ruff clean on src/tests/app + unit files (pre-existing INIT/S03-era findings left untouched and recorded); QA run inspected - all five checks PASS (14/14 formulas, 52/52 citations resolve, six sections, zero banned phrases, registry validator clean); the rendered HTML structurally verified (14 math divs, 15 tables, correct heading counts, MathJax present) and opened in the browser; two QA runs compared (the first run's citation + banned-phrase findings vs the re-run's clean PASS, both preserved in the design notes).
- Learning evidence: the unit re-taught the S16 lesson on new text - the report's own NON_CLAIMS restatement used the banned literal "investment advice" and was caught by the very check the report documents; the fix is not an exemption but bounded wording, and the document now explains its own wording choice. Second lesson: `ruff --fix --unsafe-fixes` silenced an unused-variable finding by leaving the expression behind as dead code - read the diff, not just the exit code. Third: the QA machinery caught three wording violations in its author's prose before any human reviewer would have - the checks police their own author, which is the point of making them machinery.
