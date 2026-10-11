"""Rendered-document QA for the research report (unit S19).

The report is a curated document; this module is the machinery that
keeps it honest, in the same register as S13 (pinned schemas), S15
(captions counted from rendered data) and S16 (banned-phrase filter):

1. **Formula presentation** - every typeset formula in
   ``macropulse.report.formulas`` must appear in the report's display
   math, exactly. A formula that silently vanished from the document
   is a reported problem.
2. **Citations** - every repository path the report cites must exist
   on disk. A cited evidence file that is not there is a fabrication
   vector; this closes it mechanically.
3. **Structure** - the contract sections (scope/claims boundary, data
   provenance, formula presentation, findings, limitations,
   reproducibility appendix) must be present.
4. **Claims boundary** - the S16 banned-phrase filter runs on the
   whole document with NO exemption (the S16 lesson: a disclaimer
   using banned literals is textually identical to a violation).
5. **Rendering** - ``render_html`` turns the markdown into a
   standalone HTML document with MathJax typeset math, for the
   rendered-document QA artifact. Pure and deterministic: no clock
   reads, no network, no I/O.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from macropulse.briefing.prose import check_prose
from macropulse.report.formulas import TYPESET

# The sections the unit contract requires of the report (matched as
# substrings of ATX headings, any level).
REQUIRED_SECTIONS: tuple[str, ...] = (
    "Research scope and claims boundary",
    "Data architecture and provenance",
    "Formula presentation",
    "Findings",
    "Limitations",
    "Reproducibility appendix",
)

_MATH_BLOCK_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]*)`")
# Repository paths the report may cite. The lookbehind keeps this off
# URLs (https://docs/...) and off command fragments.
_CITED_PATH_RE = re.compile(
    r"(?<![\w/])(?:evidence|docs|src|scripts|tests|app|prompts)"
    r"/[A-Za-z0-9_./-]+"
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _normalized(text: str) -> str:
    """Whitespace-collapsed text (LaTeX and prose compare on this)."""
    return " ".join(text.split())


def _compact(text: str) -> str:
    """Whitespace-FREE text. LaTeX math is whitespace-insensitive, so a
    formula wrapped mid-token in the curated document is still presented."""
    return "".join(text.split())


def extract_display_math(markdown: str) -> list[str]:
    """The whitespace-normalized bodies of all ``$$...$$`` blocks."""
    return [_normalized(body) for body in _MATH_BLOCK_RE.findall(markdown)]


def formula_problems(markdown: str) -> list[str]:
    """Typeset formulas missing from the report's display math."""
    rendered = {_compact(body) for body in _MATH_BLOCK_RE.findall(markdown)}
    missing = [
        entry.key for entry in TYPESET.values() if _compact(entry.latex) not in rendered
    ]
    return [f"formula not presented in the report: {key}" for key in missing]


def cited_paths(markdown: str) -> list[str]:
    """Repository paths the prose cites (code blocks excluded)."""
    prose_only = _CODE_BLOCK_RE.sub("", markdown)
    paths = _CITED_PATH_RE.findall(prose_only)
    return [path.rstrip(".") for path in paths]


def citation_problems(markdown: str, repo_root: Path) -> list[str]:
    """Cited paths that do not exist on disk."""
    problems: list[str] = []
    for path in cited_paths(markdown):
        if not (repo_root / path).exists():
            problems.append(f"cited path does not exist: {path}")
    return problems


def section_problems(markdown: str) -> list[str]:
    """Contract sections absent from the document's headings."""
    headings = [
        match.group(2)
        for line in markdown.splitlines()
        if (match := _HEADING_RE.match(line))
    ]
    return [
        f"required section missing: {section}"
        for section in REQUIRED_SECTIONS
        if not any(section in heading for heading in headings)
    ]


def prose_problems(markdown: str) -> list[str]:
    """S16 banned-phrase reasons found anywhere in the document."""
    return [f"banned-phrase pattern: {reason}" for reason in check_prose(markdown)]


def qa_problems(markdown: str, repo_root: Path) -> list[str]:
    """Every QA finding; an empty list means the document passes."""
    return [
        *formula_problems(markdown),
        *citation_problems(markdown, repo_root),
        *section_problems(markdown),
        *prose_problems(markdown),
    ]


# --- rendering ---------------------------------------------------------------


def _escape_inline(text: str) -> str:
    """HTML-escape, then code spans, bold, and italic - in that order
    so markup inside backticks stays literal."""
    parts: list[str] = []
    pieces = _INLINE_CODE_RE.split(text)
    for index, piece in enumerate(pieces):
        if index % 2:  # inside backticks
            parts.append(f"<code>{html.escape(piece)}</code>")
            continue
        piece = html.escape(piece)
        piece = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", piece)
        piece = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", piece)
        parts.append(piece)
    return "".join(parts)


def render_html(markdown: str, title: str) -> str:
    """A standalone HTML rendering of the report's markdown subset.

    Supports: ATX headings, ``$$`` display math, fenced code blocks,
    pipe tables, bullet lists, and paragraphs. Deterministic - a pure
    function of its inputs, no clock reads, no network. MathJax
    (CDN) typesets the display math client-side, mirroring the S18
    figure-HTML precedent.
    """
    lines = markdown.splitlines()
    body: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]

        if line.startswith("```"):
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1  # closing fence
            body.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            continue

        if line.startswith("$$"):
            math_lines = [line[2:]]
            if not math_lines[0].endswith("$$"):
                index += 1
                while index < len(lines) and not lines[index].endswith("$$"):
                    math_lines.append(lines[index])
                    index += 1
                if index < len(lines):
                    math_lines.append(lines[index][:-2])
            else:
                math_lines[0] = math_lines[0][:-2]
            index += 1
            tex = "\n".join(math_lines).strip()
            body.append(f'<div class="math">$${html.escape(tex)}$$</div>')
            continue

        if _HEADING_RE.match(line):
            match = _HEADING_RE.match(line)
            assert match is not None
            level = len(match.group(1))
            body.append(
                f"<h{level}>{_escape_inline(match.group(2))}</h{level}>"
            )
            index += 1
            continue

        if line.startswith("|"):
            table: list[str] = []
            while index < len(lines) and lines[index].startswith("|"):
                table.append(lines[index])
                index += 1
            cells = [
                [cell.strip() for cell in row.strip().strip("|").split("|")]
                for row in table
                if not re.match(r"^\|[\s:|-]+\|$", row)
            ]
            if cells:
                head, *rows = cells
                body.append("<table><thead><tr>")
                body.extend(f"<th>{_escape_inline(c)}</th>" for c in head)
                body.append("</tr></thead><tbody>")
                for row in rows:
                    body.append("<tr>")
                    body.extend(f"<td>{_escape_inline(c)}</td>" for c in row)
                    body.append("</tr>")
                body.append("</tbody></table>")
            continue

        if line.startswith("- "):
            items: list[str] = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append(lines[index][2:])
                index += 1
            body.append("<ul>")
            body.extend(f"<li>{_escape_inline(item)}</li>" for item in items)
            body.append("</ul>")
            continue

        if not line.strip():
            index += 1
            continue

        paragraph: list[str] = []
        while index < len(lines) and lines[index].strip() and not (
            lines[index].startswith(("#", "|", "- ", "```", "$$"))
        ):
            paragraph.append(lines[index])
            index += 1
        body.append("<p>" + _escape_inline(" ".join(paragraph)) + "</p>")

    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        f"<title>{html.escape(title)}</title>\n"
        "<script src=\"https://cdn.jsdelivr.net/npm/mathjax@3/es5/"
        "tex-mml-chtml.js\"></script>\n"
        "<style>\n"
        "body { background: #fdfdfc; color: #0b0b0b; max-width: 46rem;\n"
        "  margin: 3rem auto; padding: 0 1.5rem;\n"
        "  font-family: Inter, 'Helvetica Neue', Arial, sans-serif;\n"
        "  font-size: 1.05rem; line-height: 1.65; }\n"
        "h1, h2, h3, h4 { font-family: Spectral, Georgia, 'Times New Roman',\n"
        "  serif; line-height: 1.25; }\n"
        "h1 { font-size: 2rem; margin-bottom: 0.25rem; }\n"
        "h2 { border-bottom: 1px solid #e1e0d9; padding-bottom: 0.3rem; }\n"
        ".math { margin: 1.2rem 0; overflow-x: auto; }\n"
        "table { border-collapse: collapse; margin: 1rem 0; font-size: 0.95rem; }\n"
        "th, td { border: 1px solid #e1e0d9; padding: 0.35rem 0.7rem;\n"
        "  text-align: left; }\n"
        "th { background: #f2f1ec; }\n"
        "code, pre { font-family: 'SF Mono', Menlo, monospace; font-size: 0.9em; }\n"
        "pre { background: #f6f5f0; padding: 0.8rem; overflow-x: auto; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n" + "\n".join(body) + "\n"
        "</body>\n"
        "</html>\n"
    )


# Repo root for callers that pass a default (tests, evidence scripts).
REPO_ROOT = Path(__file__).resolve().parents[3]
