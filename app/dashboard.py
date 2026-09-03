"""MacroPulse dashboard (units S14-S15): country, comparison, provenance
views with freshness labels, quality badges, and limitations.

Thin Streamlit rendering over the S13 query service; all data shaping
lives in tested, pure functions (``macropulse.views.assembly``), labels
in ``macropulse.views.labels``, and fetching in
``macropulse.views.client``. Static indicator methodology (limitations,
comparability notes) is read from the code-level S02 catalog - the same
source the S13 methodology endpoints read formulas from - so the pinned
API contract stays unchanged.

Run (from the repo root, until the editable install is repaired in E01):

    PYTHONPATH=src .venv/bin/streamlit run app/dashboard.py

Requires the query service to be running:

    PYTHONPATH=src .venv/bin/python -m uvicorn macropulse.api.main:app --port 8000

(or set ``MACROPULSE_API_URL`` to point elsewhere).
"""

from __future__ import annotations

from datetime import UTC, datetime

import plotly.graph_objects as go
import streamlit as st

from macropulse.catalog import CATALOG
from macropulse.views.assembly import (
    chart_traces,
    comparison_matrix,
    country_view_rows,
    coverage_counts,
    provenance_rows,
)
from macropulse.views.client import QueryServiceClient, QueryServiceError
from macropulse.views.labels import (
    FRESHNESS_LAG_STEPS,
    GRADE_MEANINGS,
    QUALITY_BADGES,
    chart_caption,
    freshness_summary,
    merge_freshness,
    quality_badge,
)

st.set_page_config(page_title="MacroPulse", page_icon="🌍", layout="wide")

st.title("MacroPulse")
st.caption(
    "Observed macroeconomic data with full provenance. No forecasts, no causal "
    "claims, no investment advice. Every row carries its evidence label, "
    "vintage, and source; missing values are named, never imputed."
)

client = QueryServiceClient.from_env()
API_URL = client.base_url


@st.cache_data(ttl=60, show_spinner=False)
def fetch_countries(api_url: str) -> list[dict]:
    return QueryServiceClient(api_url).countries()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_indicators(api_url: str) -> list[dict]:
    return QueryServiceClient(api_url).indicators()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_latest(
    api_url: str, indicator_id: str | None, country_iso3: str | None
) -> list[dict]:
    return QueryServiceClient(api_url).observations(
        indicator_id=indicator_id, country_iso3=country_iso3, latest_vintage=True
    )


@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_vintages(
    api_url: str, indicator_id: str, country_iso3: str
) -> list[dict]:
    return QueryServiceClient(api_url).observations(
        indicator_id=indicator_id, country_iso3=country_iso3
    )


with st.sidebar:
    st.subheader("Query service")
    st.code(API_URL, language="text")
    try:
        health = client.health()
    except QueryServiceError as exc:
        st.error(f"Service unreachable: {exc}")
        st.info(
            "Start it with:\n\n"
            "```\n"
            "PYTHONPATH=src .venv/bin/python -m uvicorn "
            "macropulse.api.main:app --port 8000\n"
            "```"
        )
        st.stop()
    if health.get("status") != "ok":
        st.error(f"Service reports {health.get('status')} ({health.get('data_mode')}).")
        st.stop()
    st.caption(f"status: {health.get('status')} · data_mode: {health.get('data_mode')}")
    st.divider()
    # Freshness is computed against this caller-chosen date. The default is
    # today in UTC (a render-layer clock read); every label derives from the
    # value, never from a hidden clock.
    as_of = st.date_input("As-of date (freshness)", value=datetime.now(UTC).date())

try:
    countries = fetch_countries(API_URL)
    indicators = fetch_indicators(API_URL)
except QueryServiceError as exc:
    st.error(f"Could not load panel data: {exc}")
    st.stop()

if not countries or not indicators:
    st.info(
        "The query service has no countries/indicators registered yet - the "
        "database behind it is empty. Nothing is shown rather than inferred."
    )
    st.stop()

country_labels = {c["iso3"]: c["name"] for c in countries}
indicator_labels = {
    i["indicator_id"]: f"{i['name']} [{i['indicator_id']}]" for i in indicators
}
catalog_by_id = {i.indicator_id: i for i in CATALOG}

EVIDENCE_LABEL_MEANINGS = {
    "real": "live-retrieved from the provider API",
    "mocked": "deterministic no-key fixture (connector fixture mode)",
    "synthetic": "test fixture - never presented as observed",
    "cached": "reserved for the scheduled-refresh layer (not yet emitted)",
    "external": "document-verified registry entry (case study; a document, "
    "never an API observation)",
}


def line_chart(traces: list[dict], title: str, yaxis_title: str) -> go.Figure:
    """One line per country; gaps for missing periods; provenance on hover."""
    fig = go.Figure()
    for t in traces:
        fig.add_trace(
            go.Scatter(
                x=t["xs"],
                y=t["ys"],
                mode="lines+markers",
                name=t["country"],
                connectgaps=False,  # missing periods are gaps, not interpolated lines
                customdata=[
                    [h["vintage"], h["evidence_label"], h["quality_grade"]]
                    for h in t["hover"]
                ],
                hovertemplate=(
                    "%{x}<br>value: %{y}<br>"
                    "vintage: %{customdata[0]}<br>"
                    "evidence: %{customdata[1]}<br>"
                    "quality: %{customdata[2]}"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
    fig.update_layout(title=title, yaxis_title=yaxis_title)
    return fig


def with_badges(rows: list[dict]) -> list[dict]:
    """Decorate the quality_grade column with its badge symbol."""
    return [{**r, "quality_grade": quality_badge(r["quality_grade"])} for r in rows]


with st.expander("Labels legend"):
    badge_lines = [
        f"- {quality_badge(grade)} — {GRADE_MEANINGS[grade]}"
        for grade in QUALITY_BADGES
    ]
    st.markdown("**Quality badges** (S07 closed vocabulary)")
    st.markdown("\n".join(badge_lines))
    st.markdown(
        f"**Freshness** (presentation convention, computed against the "
        f"as-of date in the sidebar): *current* = last observed period is "
        f"fewer than {FRESHNESS_LAG_STEPS} frequency steps old; *lagging* = "
        f"{FRESHNESS_LAG_STEPS} steps or more; *no_data* = nothing observed. "
        "Arithmetic on observation dates - the release calendar is "
        "unpopulated, so no expected-release claim is made."
    )
    st.markdown("**Evidence labels** (S01 vocabulary)")
    st.markdown(
        "\n".join(
            f"- {name} — {meaning}" for name, meaning in EVIDENCE_LABEL_MEANINGS.items()
        )
    )

tab_country, tab_comparison, tab_provenance = st.tabs(
    ["Country view", "Comparison view", "Provenance view"]
)

# --- Country view: the current picture of one country ------------------------

with tab_country:
    selected_iso3 = st.selectbox(
        "Country",
        list(country_labels),
        format_func=lambda iso3: f"{iso3} — {country_labels[iso3]}",
    )
    selected_indicators = st.multiselect(
        "Indicators (one for the chart; several for the table)",
        list(indicator_labels),
        default=list(indicator_labels)[:1],
        format_func=indicator_labels.get,
    )
    if not selected_indicators:
        st.info("Select at least one indicator.")
    else:
        obs = [
            o
            for o in fetch_latest(API_URL, None, selected_iso3)
            if o["indicator_id"] in selected_indicators
        ]
        if not obs:
            st.info(
                f"No observations for {selected_iso3} under the selected indicators."
            )
        else:
            units = {o["unit"] for o in obs}
            if len(selected_indicators) == 1 and len(units) == 1:
                st.plotly_chart(
                    line_chart(
                        chart_traces(obs, [selected_iso3]),
                        indicator_labels[selected_indicators[0]],
                        next(iter(units)),
                    ),
                    width="stretch",
                )
                st.caption(chart_caption(obs))
            elif len(units) > 1:
                st.warning(
                    "Several indicators selected with different units "
                    f"({', '.join(sorted(units))}) - a shared chart axis "
                    "would mislead, so only the table is shown."
                )
            st.dataframe(
                with_badges(country_view_rows(obs)), width="stretch", hide_index=True
            )
            st.dataframe(
                freshness_summary(obs, as_of), width="stretch", hide_index=True
            )
            st.caption(
                "Latest vintage per period, exactly as served (no rounding). "
                "Missing values are named with their reason; freshness is "
                f"computed against {as_of.isoformat()}."
            )
            with st.expander("Indicator methodology and limitations"):
                for indicator_id in selected_indicators:
                    entry = catalog_by_id.get(indicator_id)
                    if entry is None:
                        st.markdown(
                            f"**{indicator_id}** — no catalog entry "
                            "(unknown indicator)."
                        )
                        continue
                    st.markdown(f"**{entry.name}** [{entry.indicator_id}]")
                    st.markdown(f"- unit: {entry.unit}")
                    st.markdown(f"- frequency: {entry.frequency}")
                    st.markdown(f"- seasonal adjustment: {entry.seasonal_adjustment}")
                    st.markdown(f"- fallback status: {entry.fallback_status}")
                    st.markdown(
                        f"- primary source: {entry.primary_source.system} "
                        f"`{entry.primary_source.code}` "
                        f"({entry.primary_source.verified})"
                    )
                    if entry.fallback_source is not None:
                        st.markdown(
                            f"- fallback source: {entry.fallback_source.system} "
                            f"`{entry.fallback_source.code}` "
                            f"({entry.fallback_source.verified})"
                        )
                    st.markdown(f"- comparability: {entry.comparability_notes}")
                    st.markdown(f"- limitations: {entry.limitations}")

# --- Comparison view: one indicator across countries --------------------------

with tab_comparison:
    comparison_indicator = st.selectbox(
        "Indicator", list(indicator_labels), format_func=indicator_labels.get
    )
    comparison_countries = st.multiselect(
        "Countries",
        list(country_labels),
        default=list(country_labels),
        format_func=lambda iso3: f"{iso3} — {country_labels[iso3]}",
    )
    if not comparison_countries:
        st.info("Select at least one country.")
    else:
        obs = [
            o
            for o in fetch_latest(API_URL, comparison_indicator, None)
            if o["country_iso3"] in comparison_countries
        ]
        if not obs:
            st.info(
                f"No observations for {comparison_indicator} under the "
                "selected countries."
            )
        else:
            traces = chart_traces(obs, comparison_countries)
            if traces:
                st.plotly_chart(
                    line_chart(
                        traces,
                        indicator_labels[comparison_indicator],
                        traces[0]["unit"],
                    ),
                    width="stretch",
                )
                st.caption(chart_caption(obs))
            st.dataframe(
                comparison_matrix(obs, comparison_countries),
                width="stretch",
                hide_index=True,
            )
            freshness_rows = [
                f
                for f in freshness_summary(obs, as_of)
                if f["indicator_id"] == comparison_indicator
            ]
            st.dataframe(
                merge_freshness(
                    coverage_counts(obs, comparison_countries), freshness_rows
                ),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Latest vintage per period. Cells without an observation are "
                "named missing (with reason when recorded) - never blank, "
                "zero, or interpolated; the chart leaves gaps rather than "
                "drawing through missing periods. Freshness is computed "
                f"against {as_of.isoformat()}."
            )

# --- Provenance view: the vintage chain behind one series --------------------

with tab_provenance:
    prov_iso3 = st.selectbox(
        "Country (provenance)",
        list(country_labels),
        format_func=lambda iso3: f"{iso3} — {country_labels[iso3]}",
    )
    prov_indicator = st.selectbox(
        "Indicator (provenance)",
        list(indicator_labels),
        format_func=indicator_labels.get,
    )
    obs = fetch_all_vintages(API_URL, prov_indicator, prov_iso3)
    if not obs:
        st.info(f"No observations (any vintage) for {prov_iso3} / {prov_indicator}.")
    else:
        rows = provenance_rows(obs)
        periods = {r["period"] for r in rows}
        with_revisions = sum(
            1 for p in periods if sum(1 for r in rows if r["period"] == p) > 1
        )
        st.metric("Rows (all vintages)", len(rows))
        st.metric("Periods with >1 vintage", with_revisions)
        st.dataframe(with_badges(rows), width="stretch", hide_index=True)
        st.caption(
            "Every stored vintage, sorted by period then vintage; the newest "
            "vintage per period is flagged. Superseded vintages are retained "
            "for revision transparency (RQ4) - nothing is overwritten."
        )

st.divider()
st.caption(
    "MacroPulse InnovationLab · data served by the MacroPulse query service · "
    "evidence vocabulary: real / synthetic / mocked / cached / external"
)
