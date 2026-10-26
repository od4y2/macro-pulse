"""Presentation labels for the dashboard (unit S15): freshness, quality
badges, chart captions.

Everything here is a deterministic function of the served observations
plus a caller-supplied ``as_of`` date - no clock reads, no I/O - so label
semantics are tested as data, like the rest of the view layer.

Conventions (documented, consistent with S09's direction and S12's
resolvable rule - presentation conventions live in code and tests, not
in reviewer memory):

- Freshness is measured from the last OBSERVED period to ``as_of``, in
  frequency steps (FREQUENCY_STEP_MONTHS). ``current`` when the age is
  fewer than FRESHNESS_LAG_STEPS steps - one full publication interval
  of slack, since e.g. an annual 2025 observation legitimately publishes
  during 2026 - ``lagging`` at FRESHNESS_LAG_STEPS steps or more,
  ``no_data`` when nothing is observed. It is arithmetic on observation
  dates, not a claim about scheduled releases: the release calendar is
  unpopulated by S07 decision, so no "expected release" is invented.
- Quality badges decorate the closed S07 grade vocabulary. A grade
  outside that vocabulary renders as ``unknown(<grade>)`` - visible,
  never silently mapped to something real.
"""

from __future__ import annotations

from datetime import date, datetime

from macropulse.metrics.transforms import FREQUENCY_STEP_MONTHS

FRESHNESS_STATES = ("current", "lagging", "no_data")

# Presentation convention: age (in frequency steps) at which a series
# reads "lagging". Documented in the module docstring and the legend.
FRESHNESS_LAG_STEPS = 2

# S07 grade semantics, one line each (rendered in the legend).
GRADE_MEANINGS = {
    "flagged": "a data-quality flag is attached to the observation",
    "ungraded": "evidence label is not 'real' (mocked/synthetic/cached data)",
    "revised": "a newer vintage exists for the same period",
    "official": "real evidence, latest vintage, no flags",
    "preliminary": "reserved (S07): no source exposes release-stage metadata",
    "estimated": "reserved (S07): no source exposes estimation metadata",
}

# Badge symbol per grade. Symbols are decoration; the grade word always
# travels with them (see quality_badge), so a badge never replaces the
# label it decorates.
QUALITY_BADGES = {
    "flagged": "⚠",
    "ungraded": "◌",
    "revised": "↻",
    "official": "●",
    "preliminary": "◐",
    "estimated": "◑",
}


def quality_badge(grade: str) -> str:
    """``"● official"`` for a known grade; ``"unknown(<grade>)"`` otherwise."""
    if grade in QUALITY_BADGES:
        return f"{QUALITY_BADGES[grade]} {grade}"
    return f"unknown({grade})"


def freshness_summary(observations: list[dict], as_of: date) -> list[dict]:
    """Per (country, indicator) freshness rows, computed from ``as_of``.

    ``age_months`` is calendar arithmetic (year/month difference), so it
    is exact for annual/quarterly steps; ``age_steps`` divides by the
    series' frequency step. Ages are reported as computed - a negative
    age (as_of before the last observed period) is shown, not clamped:
    it signals out-of-order as_of use rather than being hidden.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for o in observations:
        groups.setdefault((o["country_iso3"], o["indicator_id"]), []).append(o)

    rows: list[dict] = []
    for (country, indicator), obs_list in sorted(groups.items()):
        observed = [o for o in obs_list if o["value"] is not None]
        if not observed:
            rows.append(
                {
                    "country_iso3": country,
                    "indicator_id": indicator,
                    "last_observed": None,
                    "age_months": None,
                    "age_steps": None,
                    "days_since_retrieval": None,
                    "state": "no_data",
                }
            )
            continue
        last = max(observed, key=lambda o: o["period"])
        frequency = last["frequency"]
        if frequency not in FREQUENCY_STEP_MONTHS:
            raise ValueError(
                f"unknown frequency {frequency!r} for {indicator}; "
                f"expected one of {sorted(FREQUENCY_STEP_MONTHS)}"
            )
        last_period = date.fromisoformat(last["period"])
        age_months = (as_of.year - last_period.year) * 12 + (
            as_of.month - last_period.month
        )
        age_steps = age_months / FREQUENCY_STEP_MONTHS[frequency]
        last_retrieval = max(
            datetime.fromisoformat(o["retrieval_time"]) for o in observed
        )
        rows.append(
            {
                "country_iso3": country,
                "indicator_id": indicator,
                "last_observed": last["period"],
                "age_months": age_months,
                "age_steps": age_steps,
                "days_since_retrieval": (as_of - last_retrieval.date()).days,
                "state": ("current" if age_steps < FRESHNESS_LAG_STEPS else "lagging"),
            }
        )
    return rows


def merge_freshness(
    coverage_rows: list[dict], freshness_rows: list[dict]
) -> list[dict]:
    """Join freshness states onto coverage counts (comparison view).

    ``coverage_rows`` come from ``assembly.coverage_counts`` (key
    ``country``); ``freshness_rows`` from ``freshness_summary`` filtered
    to one indicator (key ``country_iso3``). A country with no
    freshness row gets ``state="no_data"`` and ``None`` fields - never
    a guessed age.
    """
    by_country = {f["country_iso3"]: f for f in freshness_rows}
    merged = []
    for c in coverage_rows:
        f = by_country.get(c["country"])
        merged.append(
            {
                **c,
                "last_observed": f["last_observed"] if f else None,
                "age_steps": f["age_steps"] if f else None,
                "state": f["state"] if f else "no_data",
            }
        )
    return merged


def chart_caption(observations: list[dict]) -> str:
    """One-line provenance summary for a chart, built from the data shown.

    Counts (economies, periods, missing points), evidence labels, and
    the vintage range all come from the observations rendered - the
    caption cannot claim anything the chart does not show.
    """
    if not observations:
        return "No observations."
    countries = sorted({o["country_iso3"] for o in observations})
    periods = sorted({o["period"] for o in observations})
    evidence = sorted({o["evidence_label"] for o in observations})
    vintages = sorted({o["vintage"] for o in observations})
    missing = sum(1 for o in observations if o["value"] is None)
    parts = [
        f"{len(countries)} economy"
        if len(countries) == 1
        else f"{len(countries)} economies",
        f"{len(periods)} periods ({periods[0]} to {periods[-1]})",
        f"evidence: {', '.join(evidence)}",
        f"vintage: {vintages[0]}"
        if len(vintages) == 1
        else f"vintages: {vintages[0]} to {vintages[-1]}",
    ]
    if missing:
        parts.append(
            f"{missing} missing point"
            f"{'' if missing == 1 else 's'} (gaps, named in tables)"
        )
    return " · ".join(parts)
