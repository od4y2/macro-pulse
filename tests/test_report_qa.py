"""S19 tests: report QA machinery (checks + renderer).

The QA layer is what makes the curated report enforceable rather than
aspirational - so the tests mirror the S13/S15/S16 register: each check
must flag a synthetic violation and pass a well-formed synthetic
document, and the REAL report (the unit deliverable) must pass every
check against the real repository.
"""

from __future__ import annotations

from pathlib import Path

from macropulse.report.formulas import TYPESET
from macropulse.report.qa import (
    REQUIRED_SECTIONS,
    citation_problems,
    cited_paths,
    extract_display_math,
    formula_problems,
    prose_problems,
    qa_problems,
    render_html,
    section_problems,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _all_formulas_markdown() -> str:
    """A synthetic document presenting every typeset formula."""
    return "\n\n".join(f"$${entry.latex}$$" for entry in TYPESET.values())


def _well_formed_markdown() -> str:
    """A minimal document that satisfies every check: all sections, all
    formulas, one real citation, no banned phrases."""
    return (
        "# Synthetic report\n\n"
        + "\n\n".join(f"## {section}" for section in REQUIRED_SECTIONS)
        + "\n\n"
        + _all_formulas_markdown()
        + "\n\nMethod recorded in `docs/decisions.md`.\n"
    )


# --- display-math extraction --------------------------------------------------


def test_extract_display_math_normalizes_whitespace() -> None:
    markdown = "$$z_t = \\frac{v_t - m}\n{d}$$\n\n$$w$$"
    assert extract_display_math(markdown) == ["z_t = \\frac{v_t - m} {d}", "w"]


def test_extract_display_math_is_empty_without_math() -> None:
    assert extract_display_math("# No math here\n\nJust prose.") == []


# --- formula presentation ------------------------------------------------------


def test_formula_problems_lists_every_missing_formula() -> None:
    problems = formula_problems("$$g_t = a_t - i_t$$")  # only account_internet_gap
    assert len(problems) == len(TYPESET) - 1
    assert any("robust_z" in p for p in problems)
    assert all(p.startswith("formula not presented in the report:") for p in problems)


def test_formula_problems_passes_when_all_typeset_formulas_are_present() -> None:
    assert formula_problems(_all_formulas_markdown()) == []


def test_formula_problems_matches_across_line_breaks() -> None:
    # the report typesets robust_z over two source lines; the check
    # compares whitespace-normalized text, so this must pass
    multiline = "$$z_t = \\frac{v_t - \\operatorname{median}(W_t)}\n{\\operatorname{MAD}(W_t)}$$"
    assert formula_problems(multiline) == [
        f"formula not presented in the report: {key}"
        for key in TYPESET
        if key != "robust_z"
    ]


# --- citations -----------------------------------------------------------------


def test_cited_paths_finds_repo_paths_in_prose() -> None:
    markdown = "See `evidence/S18/live-demo-output.txt` and docs/Dashboard.md."
    assert cited_paths(markdown) == [
        "evidence/S18/live-demo-output.txt",
        "docs/Dashboard.md",
    ]


def test_cited_paths_strips_trailing_period() -> None:
    assert "docs/decisions.md" in cited_paths("recorded in docs/decisions.md.")


def test_cited_paths_ignores_urls() -> None:
    # the lookbehind keeps https://docs.example.com off the citation list
    assert cited_paths("See https://docs.example.com/x for details.") == []


def test_cited_paths_skips_code_blocks() -> None:
    # scripts/report-qa.py appears ONLY inside the fenced block - a
    # command listing is not a citation
    markdown = (
        "The run script is:\n\n```\npython scripts/report-qa.py\n```\n\n"
        "The prose that follows cites nothing."
    )
    assert cited_paths(markdown) == []


def test_citation_problems_passes_on_real_paths() -> None:
    assert citation_problems("Recorded in `docs/decisions.md`.", REPO_ROOT) == []


def test_citation_problems_reports_missing_paths() -> None:
    markdown = "Recorded in `evidence/S19/not-written-yet.txt`."
    assert citation_problems(markdown, REPO_ROOT) == [
        "cited path does not exist: evidence/S19/not-written-yet.txt"
    ]


# --- structure and claims boundary ---------------------------------------------


def test_section_problems_lists_every_missing_section() -> None:
    assert section_problems("# Just a title\n\nSome prose.") == [
        f"required section missing: {section}" for section in REQUIRED_SECTIONS
    ]


def test_section_problems_passes_on_complete_document() -> None:
    markdown = "\n\n".join(f"## {section}" for section in REQUIRED_SECTIONS)
    assert section_problems(markdown) == []


def test_prose_problems_names_the_banned_pattern_class() -> None:
    assert prose_problems("Unemployment fell because output contracted.") == [
        "banned-phrase pattern: causal_phrase"
    ]
    assert prose_problems("The outlook is good.") == [
        "banned-phrase pattern: forecast_phrase"
    ]
    assert prose_problems("This is the best result.") == [
        "banned-phrase pattern: merit_ranking_phrase"
    ]


def test_prose_problems_passes_on_bounded_scope_language() -> None:
    assert prose_problems(
        "Observed values are stated with citations; no causal statements, "
        "no rankings of merit, no forward-looking statements."
    ) == []


# --- the aggregate ------------------------------------------------------------


def test_qa_problems_aggregates_every_check() -> None:
    markdown = "# A thin document\n\nSome prose."
    assert qa_problems(markdown, REPO_ROOT) == [
        *formula_problems(markdown),
        *citation_problems(markdown, REPO_ROOT),
        *section_problems(markdown),
        *prose_problems(markdown),
    ]


def test_qa_problems_passes_a_well_formed_document() -> None:
    assert qa_problems(_well_formed_markdown(), REPO_ROOT) == []


# --- the renderer ---------------------------------------------------------------


def test_render_html_is_deterministic() -> None:
    markdown = "# Title\n\n$$x + 1$$\n\n- one\n- two\n"
    assert render_html(markdown, "T") == render_html(markdown, "T")


def test_render_html_typesets_display_math_with_mathjax() -> None:
    output = render_html("$$z_t$$", "T")
    assert '<div class="math">$$z_t$$</div>' in output
    assert "mathjax@3" in output
    assert "tex-mml-chtml.js" in output


def test_render_html_joins_multi_line_math() -> None:
    markdown = "$$\nz_t = \\frac{v_t - m}{d}\n$$"
    output = render_html(markdown, "T")
    assert '<div class="math">$$z_t = \\frac{v_t - m}{d}$$</div>' in output


def test_render_html_tolerates_unterminated_math() -> None:
    # an unclosed $$ block must render what exists, not crash
    output = render_html("$$\nz_t = 1\n", "T")
    assert "$$z_t = 1$$" in output


def test_render_html_escapes_markup_and_renders_inline_code() -> None:
    output = render_html(
        "Use `<x>` and **bold** and `a < b` & more.", "A & B"
    )
    assert "<code>&lt;x&gt;</code>" in output
    assert "<strong>bold</strong>" in output
    assert "<code>a &lt; b</code>" in output
    assert "&amp; more" in output
    assert "<title>A &amp; B</title>" in output


def test_render_html_renders_tables_lists_and_code_blocks() -> None:
    markdown = (
        "# H\n\n"
        "| a | b |\n"
        "|---|---|\n"
        "| 1 | 2 |\n\n"
        "- item one\n"
        "- item two\n\n"
        "```python\n"
        "x = 1 < 2\n"
        "```\n"
    )
    output = render_html(markdown, "T")
    assert (
        "<table><thead><tr>\n<th>a</th>\n<th>b</th>\n</tr></thead><tbody>\n"
        "<tr>\n<td>1</td>\n<td>2</td>\n</tr>\n</tbody></table>"
    ) in output
    assert "<ul>\n<li>item one</li>\n<li>item two</li>\n</ul>" in output
    assert "<pre><code>x = 1 &lt; 2</code></pre>" in output


def test_render_html_renders_headings_at_their_level() -> None:
    output = render_html("# One\n\n## Two\n\n### Three", "T")
    assert "<h1>One</h1>" in output
    assert "<h2>Two</h2>" in output
    assert "<h3>Three</h3>" in output


# --- the deliverable acceptance gate --------------------------------------------


def test_real_report_passes_qa() -> None:
    """docs/ResearchReport.md is the unit deliverable: every formula
    presented, every citation resolvable, every required section
    present, and no banned phrase anywhere in the document."""
    report = REPO_ROOT / "docs" / "ResearchReport.md"
    assert report.exists(), "docs/ResearchReport.md is the S19 deliverable"
    problems = qa_problems(report.read_text(), REPO_ROOT)
    assert problems == []
