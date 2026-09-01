"""MacroPulse dashboard (unit S14): country, comparison, provenance views.

Thin Streamlit rendering over the S13 query service; all data shaping
lives in tested, pure functions (``macropulse.views.assembly``), and all
fetching in ``macropulse.views.client``.

Run (from the repo root, until the editable install is repaired in E01):

    PYTHONPATH=src .venv/bin/streamlit run app/dashboard.py

Requires the query service to be running:

    PYTHONPATH=src .venv/bin/python -m uvicorn macropulse.api.main:app --port 8000

(or set ``MACROPULSE_API_URL`` to point elsewhere).
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from macropulse.views.assembly import (
    chart_traces,
    comparison_matrix,
    country_view_rows,
    coverage_counts,
    provenance_rows,
)
from macropulse.views.client import QueryServiceClient, QueryServiceError

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


def line_chart(traces: list[dict], title: str, yaxis_title: str) -> go.Figure:
    """One line per country; missing periods render as gaps, never bridges."""
    fig = go.Figure()
    for t in traces:
        fig.add_trace(
            go.Scatter(
                x=t["xs"],
                y=t["ys"],
                mode="lines+markers",
                name=t["country"],
                connectgaps=False,  # missing periods are gaps, not interpolated lines
            )
        )
    fig.update_layout(title=title, yaxis_title=yaxis_title)
    return fig


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
            elif len(units) > 1:
                st.warning(
                    "Several indicators selected with different units "
                    f"({', '.join(sorted(units))}) - a shared chart axis "
                    "would mislead, so only the table is shown."
                )
            st.dataframe(country_view_rows(obs), width="stretch", hide_index=True)
            st.caption(
                "Latest vintage per period, exactly as served (no rounding). "
                "Missing values are named with their reason."
            )

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
            st.dataframe(
                comparison_matrix(obs, comparison_countries),
                width="stretch",
                hide_index=True,
            )
            st.dataframe(
                coverage_counts(obs, comparison_countries),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Latest vintage per period. Cells without an observation are "
                "named missing (with reason when recorded) - never blank, "
                "zero, or interpolated; the chart leaves gaps rather than "
                "drawing through missing periods."
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
        st.dataframe(rows, width="stretch", hide_index=True)
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
