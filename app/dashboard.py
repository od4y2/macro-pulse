"""MacroPulse dashboard (units S14-S18): country, comparison, provenance
views with freshness labels, quality badges, and limitations, rendered
in the S18 editorial visual language (muted validated palette, serif
display titles, focus-and-context charts, documented-episode bands).

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

Single-process hosts (Streamlit Community Cloud): the service runs on
an in-process thread instead of a standalone uvicorn - see
``macropulse.cloud_runtime``. When that module is absent, the
standalone service above is expected to be running.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import plotly.graph_objects as go
import streamlit as st

try:
    from macropulse.cloud_runtime import boot
except ImportError:
    pass  # not a cloud deployment: the standalone service is expected
else:
    boot()

from macropulse.briefing.prose import display_value
from macropulse.case_study.macro_episodes import MACRO_EPISODES
from macropulse.catalog import CATALOG
from macropulse.views.annotations import (
    apply_overlays,
    episode_captions,
    episode_overlays,
    episodes_in_range,
)
from macropulse.views.assembly import (
    briefing_highlights,
    chart_traces,
    comparison_matrix,
    country_view_rows,
    coverage_counts,
    isolated_point_indices,
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
    missingness_note,
    quality_badge,
)
from macropulse.views.theme import (
    INK,
    MARKER_OUTLINE_WIDTH,
    MARKER_SIZE_ISOLATED,
    PAGE,
    focus_label_point,
    layout_update,
    series_style,
)

st.set_page_config(page_title="MacroPulse", page_icon="🌍", layout="wide")

# Editorial typography: open serif display face for headings (financial-
# press faces are proprietary and are NOT used); degrades to Georgia
# offline rather than substituting silently. Body/data text stays the
# system sans (legibility at small sizes; config.toml pins light mode).
st.markdown(
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Spectral:wght@500;600&display=swap');"
    "h1, h2, h3 {font-family: Spectral, Georgia, serif !important;}"
    ".stCaption {color: #52514e;}"
    "</style>",
    unsafe_allow_html=True,
)

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
    "cached": "reserved: the S17 refresh layer stores real data or "
    "records failure; no cached rows are emitted",
    "external": "document-verified registry entry (case study; a document, "
    "never an API observation)",
}


def line_chart(
    traces: list[dict],
    title: str,
    yaxis_title: str,
    focus: str | None = None,
) -> go.Figure:
    """One line per country in the S18 editorial language.

    Focus-and-context: the ``focus`` country (and every series when
    there is exactly one) wears its entity color; all others wear
    context grey, so a ten-economy comparison never puts ten hues on
    screen. Gaps stay gaps (missing periods are never interpolated);
    provenance travels on hover exactly as before (S15). Documented
    episodes overlapping the rendered range draw as neutral bands with
    a citation in the caller's caption (S18).

    Survey-wave series (e.g. Findex account ownership: five observed
    years, every neighbour a source-recorded gap) would draw NO line at
    all under ``mode="lines"`` + ``connectgaps=False`` - the real
    observations would be invisible. An observed point both of whose
    grid neighbours are missing therefore also gets an explicit marker
    in the series color (``isolated_point_indices``); the gaps around it
    stay gaps, and nothing is interpolated or zero-filled.
    """
    hovertemplate = (
        "%{x}<br>value: %{y}<br>"
        "vintage: %{customdata[0]}<br>"
        "evidence: %{customdata[1]}<br>"
        "quality: %{customdata[2]}"
        "<extra>%{fullData.name}</extra>"
    )
    fig = go.Figure()
    first_period: str | None = None
    last_period: str | None = None
    for t in traces:
        is_focus = focus is None or t["country"] == focus
        style = series_style(t["country"], is_focus)
        fig.add_trace(
            go.Scatter(
                x=t["xs"],
                y=t["ys"],
                mode="lines",  # no markers on 60+ point series; hover
                # carries point inspection without visual clutter
                name=t["country"],
                connectgaps=False,  # missing periods are gaps, not interpolated lines
                line={"color": style["color"], "width": style["width"]},
                showlegend=style["showlegend"] and len(traces) > 1,
                customdata=[
                    [h["vintage"], h["evidence_label"], h["quality_grade"]]
                    for h in t["hover"]
                ],
                hovertemplate=hovertemplate,
            )
        )
        isolated = isolated_point_indices(t["xs"], t["ys"])
        if isolated:
            # Markers only where a line cannot reach: the actual survey
            # years, highlighted; hover provenance identical to the line.
            fig.add_trace(
                go.Scatter(
                    x=[t["xs"][i] for i in isolated],
                    y=[t["ys"][i] for i in isolated],
                    mode="markers",
                    name=t["country"],
                    showlegend=False,  # identity already carried by the line trace
                    marker={
                        "size": MARKER_SIZE_ISOLATED,
                        "color": style["color"],
                        "line": {"color": PAGE, "width": MARKER_OUTLINE_WIDTH},
                    },
                    customdata=[
                        [
                            t["hover"][i]["vintage"],
                            t["hover"][i]["evidence_label"],
                            t["hover"][i]["quality_grade"],
                        ]
                        for i in isolated
                    ],
                    hovertemplate=hovertemplate,
                )
            )
        if t["xs"]:
            first_period = t["xs"][0] if first_period is None else min(first_period, t["xs"][0])
            last_period = t["xs"][-1] if last_period is None else max(last_period, t["xs"][-1])

    fig.update_layout(**layout_update(title, yaxis_title))

    # Direct label on the focus line's last observed point: identity for
    # the colored series without reading a legend (text wears ink, the
    # colored line carries the hue).
    if focus is not None and len(traces) > 1:
        focus_trace = next((t for t in traces if t["country"] == focus), None)
        if focus_trace is not None:
            label_point = focus_label_point(focus_trace["xs"], focus_trace["ys"])
            if label_point is not None:
                fig.add_annotation(
                    x=label_point[0],
                    y=label_point[1],
                    xanchor="left",
                    yanchor="middle",
                    text=focus_trace["country"],
                    showarrow=False,
                    font={"size": 11, "color": INK},
                )

    if first_period is not None and last_period is not None:
        apply_overlays(
            fig,
            episode_overlays(
                MACRO_EPISODES, date.fromisoformat(first_period), date.fromisoformat(last_period)
            ),
        )
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

tab_country, tab_comparison, tab_provenance, tab_briefing = st.tabs(
    ["Country view", "Comparison view", "Provenance view", "AI briefing"]
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
                periods = [o["period"] for o in obs]
                st.plotly_chart(
                    line_chart(
                        chart_traces(obs, [selected_iso3]),
                        indicator_labels[selected_indicators[0]],
                        next(iter(units)),
                    ),
                    width="stretch",
                )
                band_caption = episode_captions(
                    episodes_in_range(
                        MACRO_EPISODES,
                        date.fromisoformat(min(periods)),
                        date.fromisoformat(max(periods)),
                    )
                )
                if band_caption:
                    st.caption(band_caption)
                st.caption(chart_caption(obs))
                note = missingness_note(obs)
                if note:
                    st.caption(note)
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
        # Focus-and-context (S18): the focus country wears its entity
        # color; every other selected country renders in context grey so
        # a ten-economy comparison never puts ten hues on screen. The
        # matrix table below carries the numbers; hover carries
        # per-point provenance on every line.
        comparison_focus = st.selectbox(
            "Focus country (others in grey)",
            comparison_countries,
            index=0,
            format_func=lambda iso3: f"{iso3} — {country_labels[iso3]}",
        )
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
                periods = sorted({o["period"] for o in obs})
                st.plotly_chart(
                    line_chart(
                        traces,
                        indicator_labels[comparison_indicator],
                        traces[0]["unit"],
                        focus=comparison_focus,
                    ),
                    width="stretch",
                )
                band_caption = episode_captions(
                    episodes_in_range(
                        MACRO_EPISODES,
                        date.fromisoformat(periods[0]),
                        date.fromisoformat(periods[-1]),
                    )
                )
                if band_caption:
                    st.caption(band_caption)
                st.caption(chart_caption(obs))
                note = missingness_note(obs)
                if note:
                    st.caption(note)
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
                "Latest vintage per period. The focus country is drawn in "
                "its panel color, other selected countries in grey "
                "(hover any line for per-point provenance; the matrix below "
                "carries every value). Cells without an observation are "
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

# --- AI briefing: on-demand structured document for one country ----------------

with tab_briefing:
    st.caption(
        "On demand, one country at a time: statements derived only from "
        "validated observations (evidence: real), adjudicated claim by claim "
        "against that JSON, and screened for banned phrasing and fabricated "
        "numbers. Every generation appends an audit run. When the LLM prose "
        "source is unavailable or its draft fails a gate, the deterministic "
        "template document is served instead - with a warning naming the "
        "reason. No forecasts, no causal claims, no investment advice."
    )
    briefing_iso3 = st.selectbox(
        "Country (briefing)",
        list(country_labels),
        format_func=lambda iso3: f"{iso3} — {country_labels[iso3]}",
    )
    if st.button("Generate briefing", type="primary"):
        try:
            with st.spinner("Generating briefing (LLM call may take a minute)..."):
                st.session_state["briefing_result"] = QueryServiceClient(
                    API_URL
                ).generate_briefing(briefing_iso3)
        except QueryServiceError as exc:
            st.error(f"Briefing generation failed: {exc}")

    result = st.session_state.get("briefing_result")
    if result is None:
        st.info(
            "No briefing generated yet. Choose a country and press "
            "**Generate briefing** - each press is one real generation "
            "(nothing here is cached or replayed)."
        )
    else:
        result_iso3 = result.get("country_iso3")
        if result_iso3 != briefing_iso3:
            st.warning(
                f"Showing the last generated briefing for {result_iso3} - "
                f"press **Generate briefing** to run {briefing_iso3}."
            )
        if result.get("warning"):
            st.warning(
                f"Served by the deterministic fallback - {result['warning']}"
            )
        st.markdown(result.get("prose", ""))
        st.caption(
            f"model: {result.get('model')} · prompt: "
            f"{result.get('prompt_version')} · status: {result.get('status')} "
            f"· run #{result.get('id')} · country: {result_iso3}"
        )

        # Headline tiles + small multiples, from the same latest-vintage
        # rows the briefing generation used (cached fetch, pure shaping in
        # views.assembly - no value is computed, converted, or zero-filled).
        try:
            tile_obs = fetch_latest(API_URL, None, result_iso3)
        except QueryServiceError as exc:
            tile_obs = []
            st.caption(f"Could not load observations for the visuals: {exc}")
        highlights = briefing_highlights(tile_obs)
        if highlights:
            st.subheader("Headline figures")
            for row_start in range(0, len(highlights), 4):
                cols = st.columns(4)
                for col, h in zip(cols, highlights[row_start : row_start + 4]):
                    with col:
                        st.metric(
                            indicator_labels.get(h["indicator_id"], h["indicator_id"]),
                            f"{display_value(h['value'])} {h['unit']}",
                        )
                        # No st.metric delta: Streamlit draws an arrow glyph
                        # for ANY text delta, and a directionless "from 2.8"
                        # would wear an up-arrow. Direction (house wording),
                        # rounded prior, and prior period go in the caption.
                        if h["direction"] is not None:
                            st.caption(
                                f"{h['period']} · {h['direction']} from "
                                f"{display_value(h['prior_value'])} "
                                f"({h['prior_period']})"
                            )
                        else:
                            st.caption(f"{h['period']} · no consecutive prior period")
            st.caption(
                "Tiles rounded for display (2 decimals); latest-vintage "
                "real-evidence observations exactly as served. A prior is "
                "shown only when the two periods are exactly one frequency "
                "step apart - no comparison across gaps, matching the "
                "briefing's change-claim rule."
            )

            st.subheader("Indicator trends")
            chart_cols = st.columns(2)
            for i, h in enumerate(highlights):
                with chart_cols[i % 2]:
                    obs_i = fetch_latest(API_URL, h["indicator_id"], result_iso3)
                    traces = chart_traces(obs_i, [result_iso3])
                    if traces:
                        st.plotly_chart(
                            line_chart(
                                traces,
                                indicator_labels.get(
                                    h["indicator_id"], h["indicator_id"]
                                ),
                                traces[0]["unit"],
                                focus=result_iso3,
                            ),
                            width="stretch",
                            # Unique per indicator: a loop of plotly_chart
                            # elements with identical auto-generated IDs is a
                            # StreamlitDuplicateElementId error.
                            key=f"briefing-trend-{h['indicator_id']}",
                        )
            st.caption(
                "One chart per indicator: the full latest-vintage series for "
                "this country. Gaps stay gaps (never interpolated, never "
                "zero-filled); provenance on hover; documented episodes as "
                "neutral bands."
            )

        with st.expander("Adjudicated claims"):
            st.dataframe(
                [
                    {
                        "claim_text": c["claim_text"],
                        "validated": c["validated"],
                        "evidence_refs": len(c.get("evidence_refs", [])),
                    }
                    for c in result.get("claims", [])
                ],
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Every candidate claim - passed and rejected - as persisted "
                "with the run; rejected text never reaches the document."
            )

st.divider()
st.caption(
    "MacroPulse InnovationLab · data served by the MacroPulse query service · "
    "evidence vocabulary: real / synthetic / mocked / cached / external"
)
