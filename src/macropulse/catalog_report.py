"""Print the indicator catalog as a human-auditable table (unit S02).

Usage: PYTHONPATH=src python -m macropulse.catalog_report
"""

from __future__ import annotations

from macropulse.catalog import (
    CATALOG,
    indicators_needing_verification,
    validate_catalog,
)
from macropulse.scope import MODULES


def render_report() -> str:
    lines: list[str] = []
    problems = validate_catalog()
    lines.append("MacroPulse indicator catalog")
    lines.append("=" * 80)
    if problems:
        lines.append("VALIDATION PROBLEMS:")
        lines.extend(f"  - {p}" for p in problems)
    for module in MODULES:
        rows = [i for i in CATALOG if i.module == module]
        if not rows:
            continue
        lines.append("")
        lines.append(f"Module: {module} ({len(rows)} indicators)")
        lines.append("-" * 80)
        for i in rows:
            lines.append(f"{i.indicator_id} | {i.name}")
            lines.append(
                f"  unit={i.unit} freq={i.frequency} seas={i.seasonal_adjustment} "
                f"fallback={i.fallback_status}"
            )
            p = i.primary_source
            lines.append(f"  primary : {p.system}:{p.code} [{p.verified}]")
            lines.append(f"            coverage: {p.coverage}")
            if i.fallback_source is not None:
                f = i.fallback_source
                lines.append(f"  fallback: {f.system}:{f.code} [{f.verified}]")
                lines.append(f"            coverage: {f.coverage}")
            lines.append(f"  comparability: {i.comparability_notes}")
            lines.append(f"  limitations  : {i.limitations}")
    lines.append("")
    unverified = indicators_needing_verification()
    lines.append(f"Source codes awaiting live verification (S04/S05): {len(unverified)}")
    for ind_id, code in unverified:
        lines.append(f"  - {ind_id}: {code}")
    return "\n".join(lines)


def main() -> None:
    print(render_report())
    if validate_catalog():
        raise SystemExit("catalog validation failed")


if __name__ == "__main__":
    main()
