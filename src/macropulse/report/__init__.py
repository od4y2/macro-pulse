"""Research report layer (unit S19): typeset formulas and report QA."""

from macropulse.report.formulas import (
    CODE_SOURCES,
    REGISTRY_SOURCES,
    TYPESET,
    TypesetFormula,
    validate_typeset,
)
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

__all__ = [
    "CODE_SOURCES",
    "REGISTRY_SOURCES",
    "REQUIRED_SECTIONS",
    "TYPESET",
    "TypesetFormula",
    "citation_problems",
    "cited_paths",
    "extract_display_math",
    "formula_problems",
    "prose_problems",
    "qa_problems",
    "render_html",
    "section_problems",
    "validate_typeset",
]
