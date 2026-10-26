"""S19 tests: the typeset formula registry.

Two groups (the same discipline as the S08 FORMULAS tests):

1. The real registry - sound by construction: closed coverage of every
   text registry, exact anchor text, balanced LaTeX, notation present.
2. The validator on synthetic tampering - drift, missing entries, and
   malformed math must be REPORTED, never silent.
"""

from __future__ import annotations

import pytest

from macropulse.report.formulas import (
    CODE_SOURCES,
    REGISTRY_SOURCES,
    TYPESET,
    TypesetFormula,
    validate_typeset,
)

# --- the real registry -------------------------------------------------------


def test_real_typeset_registry_is_sound() -> None:
    assert validate_typeset() == []


def test_registry_carries_at_least_the_known_formulas() -> None:
    # the eight metric transforms, three labor relationships, two
    # digital relationships, plus the two code-anchored quantities
    assert len(TYPESET) == 14
    for key in ("robust_z", "yoy", "rolling_mean", "spearman_rho", "panel_coverage"):
        assert key in TYPESET


@pytest.mark.parametrize("source_label", sorted(REGISTRY_SOURCES))
def test_every_registry_key_is_typeset(source_label: str) -> None:
    registry = REGISTRY_SOURCES[source_label]
    assert set(registry) <= set(TYPESET)


@pytest.mark.parametrize("entry_key", sorted(TYPESET))
def test_every_entry_is_anchored(entry_key: str) -> None:
    entry = TYPESET[entry_key]
    assert entry.anchors or entry.code_anchors
    assert entry.latex.strip()
    assert entry.notation, "a formula without notation is unreadable"


def test_dual_anchored_entry_matches_both_registries() -> None:
    # youth_headline_gap lives in metrics.FORMULAS AND labor.RELATIONSHIPS
    # with different texts - both anchors must hold
    entry = TYPESET["youth_headline_gap"]
    assert {label for label, _ in entry.anchors} == {
        "metrics.FORMULAS",
        "labor.RELATIONSHIPS",
    }


def test_code_anchors_resolve_to_live_functions() -> None:
    for label, symbol in CODE_SOURCES.items():
        assert callable(symbol), label
    assert TYPESET["spearman_rho"].code_anchors == (
        "macropulse.lenses.digital.rank_covariation",
    )
    assert TYPESET["panel_coverage"].code_anchors == (
        "macropulse.metrics.standardize.panel_coverage",
    )


# --- the validator reports tampering -----------------------------------------


def test_anchor_text_drift_is_reported() -> None:
    original = TYPESET["robust_z"]
    tampered = TypesetFormula(
        key=original.key,
        latex=original.latex,
        notation=original.notation,
        anchors=(("metrics.FORMULAS", "edited registry text"),),  # drift
    )
    TYPESET["robust_z"] = tampered
    try:
        problems = validate_typeset()
    finally:
        TYPESET["robust_z"] = original
    assert any(
        "robust_z" in p and "drifted from metrics.FORMULAS" in p for p in problems
    )


def test_registry_key_without_entry_is_reported() -> None:
    registry = REGISTRY_SOURCES["digital.RELATIONSHIPS"]
    registry["synthetic_relationship"] = "a synthetic registry entry"
    try:
        problems = validate_typeset()
    finally:
        del registry["synthetic_relationship"]
    assert any(
        "digital.RELATIONSHIPS key 'synthetic_relationship' has no typeset entry"
        in p
        for p in problems
    )


def test_unanchored_entry_is_reported() -> None:
    original = TYPESET["spearman_rho"]
    TYPESET["spearman_rho"] = TypesetFormula(
        key="spearman_rho", latex=original.latex, notation=original.notation
    )
    try:
        problems = validate_typeset()
    finally:
        TYPESET["spearman_rho"] = original
    assert any("spearman_rho: no anchor" in p for p in problems)


def test_unknown_code_anchor_is_reported() -> None:
    original = TYPESET["panel_coverage"]
    TYPESET["panel_coverage"] = TypesetFormula(
        key="panel_coverage",
        latex=original.latex,
        notation=original.notation,
        code_anchors=("macropulse.nowhere.missing_function",),
    )
    try:
        problems = validate_typeset()
    finally:
        TYPESET["panel_coverage"] = original
    assert any(
        "panel_coverage: unresolvable code anchor "
        "'macropulse.nowhere.missing_function'" in p
        for p in problems
    )


def test_unbalanced_latex_is_reported() -> None:
    assert "unbalanced braces" in _latex_problems_for(r"\frac{1}{2")
    assert "unbalanced \\left/\\right" in _latex_problems_for(r"\left(1")
    assert "contains its own $ delimiters" in _latex_problems_for("$x$")


def _latex_problems_for(latex: str) -> str:
    original = TYPESET["pp_change"]
    TYPESET["pp_change"] = TypesetFormula(
        key="pp_change",
        latex=latex,
        notation=(("v_t", "value"),),
        anchors=original.anchors,
    )
    try:
        problems = validate_typeset()
    finally:
        TYPESET["pp_change"] = original
    return " ".join(problems)


def test_notation_symbol_absent_from_latex_is_reported() -> None:
    original = TYPESET["youth_ratio"]
    TYPESET["youth_ratio"] = TypesetFormula(
        key="youth_ratio",
        latex=original.latex,
        notation=(("q_t", "a symbol the math never uses"),),
        anchors=original.anchors,
    )
    try:
        problems = validate_typeset()
    finally:
        TYPESET["youth_ratio"] = original
    assert any(
        "youth_ratio: notation symbol 'q_t' not in the latex" in p
        for p in problems
    )


def test_unknown_registry_label_is_reported() -> None:
    original = TYPESET["mom"]
    TYPESET["mom"] = TypesetFormula(
        key="mom",
        latex=original.latex,
        notation=original.notation,
        anchors=(("typo.FORMULAS", "whatever"),),
    )
    try:
        problems = validate_typeset()
    finally:
        TYPESET["mom"] = original
    assert any("mom: unknown registry source 'typo.FORMULAS'" in p for p in problems)
