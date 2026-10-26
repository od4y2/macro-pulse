"""Rendered-document QA runner for the research report (unit S19).

Runs every check in ``macropulse.report.qa`` over the unit deliverable
(``docs/ResearchReport.md``) and records the outcome as evidence:

- ``evidence/S19/qa-run.txt``  - the checks, their scope, and the result
- ``evidence/S19/report.html`` - a deterministic standalone HTML rendering
  of the report (MathJax typesetting)

Truth-only output: the run records what the checks found, including
failures. Exit code 0 when the report passes every check, 1 otherwise, so
the same script is the acceptance command and the evidence generator.

Bootstrap note: the report cites this script's two outputs as artifacts,
so on a fresh clone the first-ever run reports those cited paths missing
until it has materialized them once; the recorded evidence reflects the
re-run against the materialized artifacts.

Run:

    PYTHONPATH=src python scripts/report-qa.py
"""

from __future__ import annotations

import sys

from macropulse.report.formulas import TYPESET, validate_typeset
from macropulse.report.qa import (
    REPO_ROOT,
    citation_problems,
    cited_paths,
    formula_problems,
    prose_problems,
    qa_problems,
    render_html,
    section_problems,
)

REPORT_PATH = REPO_ROOT / "docs" / "ResearchReport.md"
QA_OUTPUT = REPO_ROOT / "evidence" / "S19" / "qa-run.txt"
HTML_OUTPUT = REPO_ROOT / "evidence" / "S19" / "report.html"


def main() -> int:
    if not REPORT_PATH.exists():
        print(f"report not found: {REPORT_PATH}", file=sys.stderr)
        return 1

    markdown = REPORT_PATH.read_text()

    # Each dimension is reported separately so the artifact shows WHAT
    # passed, not just that something did.
    formulas = formula_problems(markdown)
    citations = citation_problems(markdown, REPO_ROOT)
    sections = section_problems(markdown)
    prose = prose_problems(markdown)
    registry = validate_typeset()
    problems = qa_problems(markdown, REPO_ROOT)

    lines = [
        "S19 rendered-document QA run",
        "=============================",
        f"document: {REPORT_PATH.relative_to(REPO_ROOT)}",
        f"typeset formulas expected: {len(TYPESET)}",
        f"cited repository paths: {len(cited_paths(markdown))}",
        "",
        "checks (each empty = pass):",
        f"  formula presentation : {formulas or 'PASS'}",
        f"  citations resolvable : {citations or 'PASS'}",
        f"  required sections    : {sections or 'PASS'}",
        f"  banned phrases       : {prose or 'PASS'}",
        f"  typeset registry     : {registry or 'PASS'}",
        "",
        f"aggregate: {problems or 'PASS'}",
        "exit status: " + ("PASS" if not problems else "FAIL"),
    ]

    QA_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    QA_OUTPUT.write_text("\n".join(lines) + "\n")
    HTML_OUTPUT.write_text(render_html(markdown, "MacroPulse Research Report"))

    print("\n".join(lines))
    print(f"\nwrote: {QA_OUTPUT.relative_to(REPO_ROOT)}")
    print(f"wrote: {HTML_OUTPUT.relative_to(REPO_ROOT)}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
