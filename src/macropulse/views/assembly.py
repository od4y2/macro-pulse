"""Pure view-model builders for the dashboard (unit S14).

Everything here is a deterministic function from API response records to
display structures - no I/O, no clock reads, so every view can be tested
as data. Rendering (Streamlit/Plotly) stays in ``app/dashboard.py`` and
stays thin.

Governance carried into display structures:

- values are never rounded, converted, or imputed; a missing value is
  marked ``missing`` with its reason, never blank or zero;
- every observation keeps its provenance (source, vintage, evidence
  label, quality grade, release/retrieval times);
- chart series keep ``None`` for missing points so charts render gaps,
  never interpolated lines.
"""

from __future__ import annotations

MISSING = "missing"


def _fmt_value(value: float | None, missing_reason: str | None) -> str:
    """Full-precision value; missing is named, never blank or zero."""
    if value is None:
        reason = missing_reason or "no reason recorded"
        return f"{MISSING} ({reason})"
    return repr(value)


def country_view_rows(observations: list[dict]) -> list[dict]:
    """Country-view rows: latest-vintage observations with full provenance.

    Input is the client's ``observations(..., latest_vintage=True)``
    payload for one country (any indicators). Rows are sorted by
    indicator, then period; every provenance field the service serves is
    carried through to a column.
    """
    rows = [
        {
            "indicator_id": o["indicator_id"],
            "period": o["period"],
            "value": _fmt_value(o["value"], o["missing_reason"]),
            "unit": o["unit"],
            "frequency": o["frequency"],
            "vintage": o["vintage"],
            "evidence_label": o["evidence_label"],
            "quality_grade": o["quality_grade"],
            "source": f"{o['source']['system']} · {o['source']['code']}",
            "source_role": o["source"]["role"],
            "release_time": o["release_time"],
            "retrieval_time": o["retrieval_time"],
            "missing_reason": o["missing_reason"] or "",
        }
        for o in observations
    ]
    rows.sort(key=lambda r: (r["indicator_id"], r["period"]))
    return rows


def provenance_rows(observations: list[dict]) -> list[dict]:
    """Provenance view: ALL vintages for one country + indicator.

    Rows are sorted by period then vintage so a revision reads top-down
    as a chain; a superseded vintage is visible next to the one that
    replaced it. The latest vintage per period is flagged - the flag is
    computed by period, not by row order.
    """
    newest_by_period: dict[str, str] = {}
    for o in observations:
        p = o["period"]
        if p not in newest_by_period or o["vintage"] > newest_by_period[p]:
            newest_by_period[p] = o["vintage"]
    rows = [
        {
            "period": o["period"],
            "vintage": o["vintage"],
            "value": _fmt_value(o["value"], o["missing_reason"]),
            "is_latest_vintage": o["vintage"] == newest_by_period[o["period"]],
            "quality_grade": o["quality_grade"],
            "evidence_label": o["evidence_label"],
            "source": f"{o['source']['system']} · {o['source']['code']}",
            "release_time": o["release_time"],
            "retrieval_time": o["retrieval_time"],
            "missing_reason": o["missing_reason"] or "",
        }
        for o in observations
    ]
    rows.sort(key=lambda r: (r["period"], r["vintage"]))
    return rows


def comparison_matrix(observations: list[dict], country_order: list[str]) -> list[dict]:
    """Comparison table: one row per period, one column per country.

    The period grid is the union of observed periods across the
    (latest-vintage, one-indicator) selection. Values are full-precision;
    a cell without an observation is named missing (with reason when the
    row carries one) - never blank, never zero. Countries outside
    ``country_order`` are ignored.
    """
    values: dict[tuple[str, str], dict] = {}
    for o in observations:
        values[(o["period"], o["country_iso3"])] = o
    periods = sorted({p for p, _ in values})
    rows = []
    for period in periods:
        row: dict[str, str] = {"period": period}
        for country in country_order:
            o = values.get((period, country))
            if o is None:
                row[country] = MISSING
            else:
                row[country] = _fmt_value(o["value"], o["missing_reason"])
        rows.append(row)
    return rows


def chart_traces(observations: list[dict], country_order: list[str]) -> list[dict]:
    """Plotly-ready traces: one per country, ``None`` y for missing points.

    Values stay raw (no rounding); missing periods carry ``None`` so the
    dashboard renders them as gaps - an interpolated line through a
    missing period would fabricate data.
    """
    by_country: dict[str, list[dict]] = {c: [] for c in country_order}
    for o in observations:
        by_country.setdefault(o["country_iso3"], []).append(o)
    traces = []
    for country in country_order:
        obs = sorted(by_country.get(country, []), key=lambda o: o["period"])
        if not obs:
            continue
        traces.append(
            {
                "country": country,
                "xs": [o["period"] for o in obs],
                "ys": [o["value"] for o in obs],  # raw values, None for missing
                "unit": obs[0]["unit"],
            }
        )
    return traces


def coverage_counts(observations: list[dict], country_order: list[str]) -> list[dict]:
    """Per-country observed/missing counts over the shared period grid.

    The grid is the union of periods across the (latest-vintage,
    one-indicator) selection; a country with no observation for a period
    counts as missing there. This is a count, not a coverage judgment -
    S09's gate thresholds are not applied here.
    """
    periods = sorted({o["period"] for o in observations})
    period_set = set(periods)
    by_country: dict[str, set[str]] = {c: set() for c in country_order}
    for o in observations:
        if o["value"] is not None:
            by_country.setdefault(o["country_iso3"], set()).add(o["period"])
    rows = []
    for country in country_order:
        observed_periods = by_country.get(country, set())
        observed = observed_periods & period_set
        rows.append(
            {
                "country": country,
                "observed": len(observed),
                "missing": len(period_set) - len(observed),
                "total_periods": len(periods),
                "first_observed": min(observed) if observed else None,
                "last_observed": max(observed) if observed else None,
            }
        )
    return rows
