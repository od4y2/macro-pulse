# S19 design notes - Research Report and Methodology Publication (2026-10-11)

Unit objective: complete report, formula presentation, limitations, and
reproducibility appendix, with the report enforceable by machinery rather
than by reviewer attention.

## 1. The third face of every formula (`src/macropulse/report/formulas.py`)

The platform already records each formula twice: as code (the computing
function) and as registry text (the dicts the S13 methodology endpoints
serve). S19 adds the third face a research report needs - typeset math -
under the same governance as every other layer:

- **Anchoring, both directions.** Registry-backed entries carry the
  registry's EXACT current text; `validate_typeset()` compares against the
  live registries, so a registry edit that leaves the typeset layer behind
  is a reported problem, never silent drift. The coverage check is closed:
  every key in `metrics.FORMULAS`, `labor.RELATIONSHIPS`, and
  `digital.RELATIONSHIPS` must have a typeset entry. `youth_headline_gap`
  is deliberately dual-anchored (its text differs between the metric and
  labor registries; both must hold).
- **Code anchors for quantities without a registry.** `spearman_rho` and
  `panel_coverage` have no registry text, so their entries anchor to the
  computing functions by import (`CODE_SOURCES`) - the entry cannot outlive
  the code it documents. An unresolvable anchor is a reported problem.
- **No invented math.** The LaTeX restates what the registry text and
  docstrings state. Structural checks: balanced braces, balanced
  `\left`/`\right`, no embedded `$` delimiters, and every notation symbol
  must appear in the math (a notation row nothing reads is a lie about the
  formula). Guard conditions (window occupancy >= 3, zero MAD -> missing,
  positive non-zero base, 12 % L == 0, full rolling windows) live in the
  notation tables and captions, never as silent constants inside the math.

14 entries: 8 metric transforms (S08/S09), 3 labor relationships (S10),
2 digital relationships (S11), plus the 2 code-anchored quantities.

## 2. The QA layer (`src/macropulse/report/qa.py`)

The report is a curated document; four mechanical checks keep it honest
(the same register as S13's pinned schemas, S15's counted captions, and
S16's banned-phrase filter):

1. **Formula presentation** - every typeset formula must appear in the
   report's display math. Comparison is whitespace-COMPACT (all
   whitespace removed): LaTeX is whitespace-insensitive, so a formula the
   document wraps mid-token is still present. (The first implementation
   compared whitespace-normalized text and failed on the two-source-line
   `robust_z`; the compact comparison is the fix and a test pins it.)
2. **Citations** - every repository path the prose cites must exist on
   disk. A cited evidence file that is not there is a fabrication vector;
   the check closes it mechanically. URLs are excluded (lookbehind), code
   blocks are excluded (a command listing is not a citation), trailing
   periods are stripped.
3. **Structure** - the six contract sections must be present as ATX
   headings.
4. **Claims boundary** - the S16 banned-phrase check runs over the WHOLE
   document with NO exemption, re-learning the S16 lesson in S19's own
   text (see honest notes).

`render_html` produces a standalone deterministic HTML document (MathJax 3
CDN for the display math, the S18 figure-HTML precedent): pure function of
its inputs - no clock reads, no network, no I/O.

## 3. The deliverable (`docs/ResearchReport.md`)

Six contract sections; all 14 formulas presented verbatim in `$$` display
math with notation tables; 52 cited repository paths (all resolving);
findings drawn ONLY from numbers verified in evidence files in this
session or earlier units (S07 revision chain, S10 youth divergence, S11
digital gaps and the NULL-row finding, S12 Yunnan episodes and 29/31
unrecorded provinces, S16 claim validation, S17 idempotent refresh, S18
byte-check end-to-end); limitations that name the panel size, the
point-in-time record, documented missingness, and the derivation guards;
and a reproducibility appendix with the measured toolchain pointer,
commands in fenced blocks, and this unit's own QA gates.

## 4. Honest notes (things that went wrong, and what they taught)

- **The scope restatement tripped its own filter.** The report quoted the
  S01 NON_CLAIMS boundary verbatim, which includes the literal
  "investment advice" - banned by the very filter the report is checked
  with. Per the S16 rule (no exemption for good intentions), the
  restatement is now worded in bounded language, and the report says why.
  The first QA run also caught "because" (twice) in my own framing
  sentences. All three findings were machine-caught, fixed, and re-run to
  PASS - the QA layer demonstrably polices its own author.
- **Bootstrap citations.** The report cites this unit's own QA artifacts
  (`evidence/S19/qa-run.txt`, `evidence/S19/report.html`), which the QA
  script itself writes - so the first-ever run on a fresh clone reports
  those two cited paths missing until the script has materialized them
  once. The recorded evidence reflects the re-run. This property is
  documented in `scripts/report-qa.py`.
- **Two QA runs, both recorded truthfully.** Run 1 (exit 1): citation
  findings for the two not-yet-written artifacts + three banned-phrase
  findings. Run 2 after the prose fixes (exit 0, recorded in
  `qa-run.txt`): all five checks PASS.
- **Ruff autofix lesson.** `ruff --fix --unsafe-fixes` parenthesized 14
  implicitly-concatenated anchor strings (value-identical; the registry
  equality tests re-prove the anchor texts) and removed an unused `labels`
  variable - but it left the set-comprehension as a dead expression
  statement. Caught by inspection, removed by hand, suite re-run. Lesson:
  an autofix that silences a lint finding can leave its corpse behind;
  read the diff, not just the exit code.
- **Scoped lint, honestly reported.** Unit acceptance runs ruff on
  src/tests/app (+ the unit's new files) - all clean. Repo-wide
  `ruff check .` still reports pre-existing findings in files outside
  S19's scope (INIT/S03-era `scripts/validate_structure.py`,
  `alembic/env.py` + migration file, and evidence live-demo scripts frozen
  at their unit's acceptance - never edited after acceptance). Recorded
  here rather than silently fixed out of scope.

## 5. Session context recorded for the record

During this unit the user hit a Streamlit Community Cloud deployment
blocker (the deployed app showed the prepared starter). The diagnosis and
fix were executed as the local half of the Option B go-live rehearsal:
the deployed GitHub repo's main contains only the starter (no S01-S18 work
was ever pushed there), cloud secrets land in `st.secrets` rather than
`os.environ`, and Community Cloud hosts one process while the dashboard
expects a separate FastAPI host. Fix (user decisions via question prompt):
a curated ORPHAN `deploy` branch (no parent history, so curriculum
material never becomes public; commit 6bc8c44, pushed to origin/deploy)
carrying platform code plus `src/macropulse/cloud_runtime.py` - which
bridges st.secrets -> os.environ["DATABASE_URL"], normalizes the scheme
to `postgresql+psycopg://`, and boots the S13 FastAPI app on a daemon
thread in-process (uvicorn >= 0.30 skips signal handlers on non-main
threads) - and `pool_pre_ping=True` in the deploy copy of `db/base.py`
(Neon autosuspend). Verified locally with two smokes (secrets-bridge run
against Neon: status ok, 10 economies, 66 USA rows; AppTest dashboard
render: no errors, charts present). The cloud half (user redeploys the
Community Cloud app against branch `deploy`, main file `app/dashboard.py`,
secrets `DATABASE_URL` = the Neon neondb connection string, then verify
on the live URL) remains open and is recorded in SESSION_STATE for S20.
Main-branch files were left untouched by the deploy work; the local demo
stack (uvicorn :8000 on docker Postgres, streamlit :8130) was restored
after the branch excursion.
