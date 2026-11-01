"""MacroPulse dashboard (units S14-S18): country, comparison, provenance
views with freshness labels, quality badges, and limitations, rendered
in the editorial visual language (muted validated palette, entity-
colored comparison charts with focus emphasis, documented-episode
bands) with the first-round UI
refinement applied (2026-11-01): ink-blue + cool-white tokens, serif
page title only, centrally managed chrome CSS (views/chrome_css.py).

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
from macropulse.views.chrome_css import dashboard_css
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
from macropulse.views.naming import (
    display_name,
    indicator_help,
    option_label,
    unit_display,
    wrap_title,
)
from macropulse.views.theme import (
    ACCENT,
    INK,
    MARKER_OUTLINE_WIDTH,
    MARKER_SIZE_ISOLATED,
    SURFACE,
    focus_label_point,
    layout_update,
    marker_symbol,
    series_style,
)

st.set_page_config(page_title="MacroPulse", page_icon="🌍", layout="wide")

# Chrome styling is centrally managed: colors come from the views.theme
# tokens, selectors are stable data-testid/data-baseweb hooks only, and
# what config.toml themes natively is not repeated here. The serif
# display face (Spectral - financial-press faces are proprietary and are
# NOT used) is reserved for the page title; it degrades to Georgia
# offline rather than substituting silently. Everything else stays the
# system sans (config.toml pins light mode).
st.markdown(f"<style>{dashboard_css()}</style>", unsafe_allow_html=True)

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
    # Opt-in reading aid (user request, 2026-11-01): straight segments
    # joining each series' OBSERVED points across periods with no value
    # (survey-wave shapes such as Findex). Off by default - gaps-as-gaps
    # is the honest baseline. Display-only either way: connectgaps draws
    # across missing periods without adding a single value, and the
    # charts' captions/notes describe whichever mode is active.
    connect_observed = st.checkbox(
        "Connect observed points (visual aid)",
        value=False,
        help="Draws straight lines between a series' observed points across "
        "periods with no recorded value. A reading aid only: nothing is "
        "interpolated or zero-filled, and the tables are unchanged. Off by "
        "default, so gaps render as gaps.",
    )

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
# Indicator naming is tiered (views.naming): selectors and chart titles
# show the display-name + unit tiers; the FULL served name and internal
# code stay reachable in each widget's native help tooltip (below), in
# the methodology expander, and in every table's indicator_id column.
# Underlying fields, widget keys and query params are untouched.
indicator_by_id = {i["indicator_id"]: i for i in indicators}
option_labels = {
    i["indicator_id"]: option_label(i["indicator_id"], i["name"], i["unit"])
    for i in indicators
}
INDICATOR_HELP = indicator_help(indicators)
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
    connect_observed: bool = False,
) -> go.Figure:
    """One line per country in the editorial visual language.

    Every series wears its entity color and a legend entry, so a
    comparison reads country-by-country on the chart itself (comparison
    fix, 2026-11-01: the earlier one-hue-plus-uniform-grey display left
    non-focus countries indistinguishable on the chart). ``focus`` is
    emphasis, not exclusive color: a heavier line plus a direct label on
    its last observed point. Countries the palette validation flagged
    also carry a hue-independent texture (``RELIEF_DASH`` on the line,
    ``RELIEF_SYMBOL`` on isolated markers - see views.theme). A chart
    with exactly ONE series (Country view, briefing small multiples)
    draws the observation in the brand accent ink blue with no texture
    instead - entity hue and relief carry no information when nothing is
    being compared. Gaps stay gaps (missing periods are never interpolated);
    provenance travels on hover exactly as before (S15). Documented
    episodes overlapping the rendered range draw as neutral bands with
    a citation in the caller's caption (S18).

    ``connect_observed`` (opt-in sidebar toggle, default off) sets
    ``connectgaps`` on the line traces: straight segments join each
    series' observed points across periods with no value - a reading
    aid for survey-wave shapes. It is display-only: connectgaps adds
    no value, interpolates nothing, and the data, tables, hover
    provenance and isolated-point markers are identical either way.

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
    single_series = len(traces) == 1
    for t in traces:
        is_focus = focus is None or t["country"] == focus
        style = series_style(t["country"], is_focus)
        if single_series and is_focus:
            # One country on screen (Country view, briefing small
            # multiples): the observation wears the brand ink blue with
            # no relief texture - the entity hue and its dash/symbol are
            # identity carriers for comparisons and carry no information
            # when nothing is being compared.
            style = {**style, "color": ACCENT, "dash": "solid"}
            symbol = "circle"
        else:
            symbol = marker_symbol(t["country"])
        fig.add_trace(
            go.Scatter(
                x=t["xs"],
                y=t["ys"],
                mode="lines",  # no markers on 60+ point series; hover
                # carries point inspection without visual clutter
                name=t["country"],
                # off (default): missing periods are gaps, never drawn
                # through; on (opt-in toggle): segments join observed
                # points across gaps - a reading aid, not interpolation
                connectgaps=connect_observed,
                line={
                    "color": style["color"],
                    "width": style["width"],
                    "dash": style["dash"],  # relief texture, solid for most
                },
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
                        "symbol": symbol,  # relief shape where no line renders
                        "line": {"color": SURFACE, "width": MARKER_OUTLINE_WIDTH},
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
            first_period = (
                t["xs"][0] if first_period is None else min(first_period, t["xs"][0])
            )
            last_period = (
                t["xs"][-1] if last_period is None else max(last_period, t["xs"][-1])
            )

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
                MACRO_EPISODES,
                date.fromisoformat(first_period),
                date.fromisoformat(last_period),
            ),
        )
    return fig


def with_badges(rows: list[dict]) -> list[dict]:
    """Decorate the quality_grade column with its badge symbol."""
    return [{**r, "quality_grade": quality_badge(r["quality_grade"])} for r in rows]


# --- table display config (second-round refinement, 2026-11-01) --------------
#
# Display-only: readable header labels and stable column widths for the
# served tables. Underlying field names, values, precision, row order and
# the CSV/JSON downloads are untouched - a column_config label never
# renames the exported field, and NO format strings are used anywhere, so
# no raw observation can be rounded by presentation. Dates stay exactly
# as served (ISO strings); the missing/source distinction stays in the
# value and missing_reason columns, which keep their full content.
_CC = st.column_config

_COUNTRY_TABLE_COLUMNS = {
    "indicator_id": _CC.TextColumn("Indicator code", width="medium"),
    "period": _CC.TextColumn("Period", width="small"),
    "value": _CC.TextColumn("Value", width="medium"),
    "unit": _CC.TextColumn("Unit", width="small"),
    "frequency": _CC.TextColumn("Frequency", width="small"),
    "vintage": _CC.TextColumn("Vintage", width="small"),
    "evidence_label": _CC.TextColumn("Evidence", width="small"),
    "quality_grade": _CC.TextColumn("Quality", width="small"),
    "source": _CC.TextColumn("Source", width="large"),
    "source_role": _CC.TextColumn("Role", width="small"),
    "release_time": _CC.TextColumn("Released", width="medium"),
    "retrieval_time": _CC.TextColumn("Retrieved", width="medium"),
    "missing_reason": _CC.TextColumn("Missing reason", width="medium"),
}

_FRESHNESS_COLUMNS = {
    "country_iso3": _CC.TextColumn("Country", width="small"),
    "indicator_id": _CC.TextColumn("Indicator code", width="medium"),
    "last_observed": _CC.TextColumn("Last observed", width="small"),
    "age_months": _CC.NumberColumn("Age (months)", width="small"),
    "age_steps": _CC.NumberColumn("Age (freq. steps)", width="small"),
    "days_since_retrieval": _CC.NumberColumn("Days since retrieval", width="small"),
    "state": _CC.TextColumn("Freshness", width="small"),
}

_COMPARISON_FRESHNESS_COLUMNS = {
    "country": _CC.TextColumn("Country", width="small"),
    "observed": _CC.NumberColumn("Observed", width="small"),
    "missing": _CC.NumberColumn("Missing", width="small"),
    "source_no_data": _CC.NumberColumn("Source: no value", width="small"),
    "no_record": _CC.NumberColumn("No record", width="small"),
    "total_periods": _CC.NumberColumn("Grid periods", width="small"),
    "last_observed": _CC.TextColumn("Last observed", width="small"),
    "age_steps": _CC.NumberColumn("Age (freq. steps)", width="small"),
    "state": _CC.TextColumn("Freshness", width="small"),
}

_PROVENANCE_COLUMNS = {
    "period": _CC.TextColumn("Period", width="small"),
    "vintage": _CC.TextColumn("Vintage", width="small"),
    "value": _CC.TextColumn("Value", width="medium"),
    "is_latest_vintage": _CC.CheckboxColumn("Latest vintage", width="medium"),
    "quality_grade": _CC.TextColumn("Quality", width="small"),
    "evidence_label": _CC.TextColumn("Evidence", width="small"),
    "source": _CC.TextColumn("Source", width="large"),
    "release_time": _CC.TextColumn("Released", width="medium"),
    "retrieval_time": _CC.TextColumn("Retrieved", width="medium"),
    "missing_reason": _CC.TextColumn("Missing reason", width="medium"),
}

_BRIEFING_CLAIM_COLUMNS = {
    "claim_text": _CC.TextColumn("Claim", width="large"),
    "validated": _CC.CheckboxColumn("Validated", width="small"),
    "evidence_refs": _CC.NumberColumn("Evidence refs", width="small"),
}


def _matrix_columns(countries: list[str]) -> dict:
    """Comparison-matrix columns: narrow period column plus one narrow
    value column per selected country (ISO3 headers already identify the
    entity; widths keep a 10-economy matrix from crowding)."""
    cols: dict = {"period": _CC.TextColumn("Period", width="small")}
    for iso3 in countries:
        cols[iso3] = _CC.TextColumn(iso3, width="small")
    return cols


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
        list(option_labels),
        default=list(option_labels)[:1],
        format_func=option_labels.get,
        help=INDICATOR_HELP,
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
                meta = indicator_by_id[selected_indicators[0]]
                st.plotly_chart(
                    line_chart(
                        chart_traces(obs, [selected_iso3]),
                        wrap_title(display_name(meta["indicator_id"], meta["name"])),
                        unit_display(next(iter(units))),
                        connect_observed=connect_observed,
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
                st.caption(chart_caption(obs, connect_observed=connect_observed))
                note = missingness_note(obs)
                if note:
                    st.caption(note)
            elif len(units) > 1:
                st.warning(
                    "Several indicators selected with different units "
                    f"({', '.join(sorted(unit_display(u) for u in units))}) - a "
                    "shared chart axis would mislead, so only the table is shown."
                )
            st.dataframe(
                with_badges(country_view_rows(obs)),
                width="stretch",
                hide_index=True,
                column_config=_COUNTRY_TABLE_COLUMNS,
            )
            st.dataframe(
                freshness_summary(obs, as_of),
                width="stretch",
                hide_index=True,
                column_config=_FRESHNESS_COLUMNS,
            )
            st.caption(
                "**Tables** latest vintage per period, exactly as served "
                "(no rounding).  \n"
                "**Missing** values are named with their reason - never "
                "imputed.  \n"
                f"**Freshness** computed against {as_of.isoformat()}."
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
        "Indicator",
        list(option_labels),
        format_func=option_labels.get,
        help=INDICATOR_HELP,
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
        # Entity color per country (S18 palette): every selected country
        # is distinguishable on the chart and named in the legend (fix
        # 2026-11-01 - uniform context grey made non-focus countries
        # unreadable). The focus country adds a heavier line and a
        # direct end label. The matrix table below carries the numbers;
        # hover carries per-point provenance on every line.
        comparison_focus = st.selectbox(
            "Focus country (heavier line + direct label)",
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
                meta = indicator_by_id.get(comparison_indicator, {})
                st.plotly_chart(
                    line_chart(
                        traces,
                        wrap_title(
                            display_name(
                                comparison_indicator,
                                meta.get("name", comparison_indicator),
                            )
                        ),
                        unit_display(traces[0]["unit"]),
                        focus=comparison_focus,
                        connect_observed=connect_observed,
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
                st.caption(chart_caption(obs, connect_observed=connect_observed))
                note = missingness_note(obs)
                if note:
                    st.caption(note)
            st.dataframe(
                comparison_matrix(obs, comparison_countries),
                width="stretch",
                hide_index=True,
                column_config=_matrix_columns(comparison_countries),
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
                column_config=_COMPARISON_FRESHNESS_COLUMNS,
            )
            st.caption(
                "**Reading the chart** every country wears its fixed panel "
                "color and a legend entry; the focus country adds a heavier "
                "line and a direct end label, and ZAF/MEX also a dash and "
                "marker shape (palette relief). Hover any line for per-point "
                "provenance; the matrix carries every value.  \n"
                "**Tables** latest vintage per period. Cells without an "
                "observation are named missing (with reason when recorded) "
                "- never blank, zero, or interpolated; "
                + (
                    # describe what the chart actually draws, per the toggle
                    "connector lines (sidebar option, on) join observed "
                    "points across unobserved periods as a reading aid - "
                    "still nothing interpolated or zero-filled."
                    if connect_observed
                    else "the chart leaves gaps rather than drawing "
                    "through missing periods."
                )
                + "  \n"
                f"**Freshness** computed against {as_of.isoformat()}."
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
        list(option_labels),
        format_func=option_labels.get,
        help=INDICATOR_HELP,
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
        st.dataframe(
            with_badges(rows),
            width="stretch",
            hide_index=True,
            column_config=_PROVENANCE_COLUMNS,
        )
        st.caption(
            "**Rows** every stored vintage, sorted by period then vintage; "
            "the newest vintage per period is flagged.  \n"
            "**Revisions** superseded vintages are retained for "
            "transparency (RQ4) - nothing is overwritten."
        )

# --- AI briefing: on-demand structured document for one country ----------------

with tab_briefing:
    st.caption(
        "On demand, one country at a time.  \n"
        "**Data basis** validated observations (evidence: real) only.  \n"
        "**Checks** every claim is adjudicated against that data and "
        "screened for banned phrasing and fabricated numbers; each "
        "generation appends an audit run.  \n"
        "**If generation fails** the deterministic template document is "
        "served instead, with a warning naming the reason.  \n"
        "No forecasts, no causal claims, no investment advice."
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
            st.warning(f"Served by the deterministic fallback - {result['warning']}")
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
                        meta = indicator_by_id.get(h["indicator_id"])
                        st.metric(
                            display_name(
                                h["indicator_id"],
                                meta["name"] if meta else h["indicator_id"],
                            ),
                            f"{display_value(h['value'])} {unit_display(h['unit'])}",
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
                "**Values** tiles rounded for display (2 decimals); the "
                "observations behind them are latest-vintage, "
                "real-evidence, exactly as served.  \n"
                "**Priors** shown only when the two periods are exactly "
                "one frequency step apart - no comparison across gaps, "
                "matching the briefing's change-claim rule."
            )

            st.subheader("Indicator trends")
            chart_cols = st.columns(2)
            for i, h in enumerate(highlights):
                with chart_cols[i % 2]:
                    obs_i = fetch_latest(API_URL, h["indicator_id"], result_iso3)
                    traces = chart_traces(obs_i, [result_iso3])
                    if traces:
                        meta = indicator_by_id.get(h["indicator_id"])
                        st.plotly_chart(
                            line_chart(
                                traces,
                                wrap_title(
                                    display_name(
                                        h["indicator_id"],
                                        meta["name"] if meta else h["indicator_id"],
                                    )
                                ),
                                unit_display(traces[0]["unit"]),
                                focus=result_iso3,
                                connect_observed=connect_observed,
                            ),
                            width="stretch",
                            # Unique per indicator: a loop of plotly_chart
                            # elements with identical auto-generated IDs is a
                            # StreamlitDuplicateElementId error.
                            key=f"briefing-trend-{h['indicator_id']}",
                        )
            st.caption(
                "One chart per indicator: the full latest-vintage series for "
                "this country. "
                + (
                    "Connector lines (sidebar option, on) join observed "
                    "points across unobserved periods - a reading aid; "
                    "still never interpolated, never zero-filled."
                    if connect_observed
                    else "Gaps stay gaps (never interpolated, never zero-filled)."
                )
                + " Provenance on hover; documented episodes as "
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
                column_config=_BRIEFING_CLAIM_COLUMNS,
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
