"""S18 live demo: ONE full evidence chain, end to end (output captured to
evidence/S18/live-demo-output.txt).

Against a DISPOSABLE database (macropulse_s18_demo - created, migrated,
and dropped by this script; nothing touches the dev or Neon databases),
with every leg run through its production entry point:

1. INGEST  - scheduled refresh CLI (S17): live World Bank fetch of
   gdp_real_growth for all 10 panel economies into the governed store.
2. DERIVE  - gate -> robust_z standardization -> derived store (S08/S09
   engine, in-process, direction read from the S02 catalog).
3. SERVE   - uvicorn on the demo DB (S13); health; provenance
   BYTE-CHECK: an API-served observation vs the stored row, field by
   field, value compared by exact repr; derived metrics + methodology
   definitions served back.
4. RENDER  - AppTest drives the real app/dashboard.py against the
   service (S14 harness): the S18 visual language asserted on the
   served figure JSON (entity-fixed focus color, context grey, episode
   band + callout, direct label, serif title), the WHO citation caption,
   and the focus switch; figures exported to evidence/S18/.
5. BRIEF   - S16 briefing built from the served facts, adjudicated,
   rendered, banned-phrase-checked, persisted to the demo DB.
6. CASE    - the historical case itself: the observed 2020 panel values
   next to the documented WHO event window (coincidence drawn on a
   chart, never a causal sentence).

Run (no prerequisites beyond the local docker Postgres being up):

    PYTHONPATH=src .venv/bin/python evidence/S18/live-demo-script.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from macropulse.briefing import (
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROMPT_VERSION,
    BriefingFacts,
    adjudicate_all,
    build_claims,
    check_prose,
    record_briefing_run,
    render_briefing,
)
from macropulse.catalog import CATALOG
from macropulse.db.base import make_engine, make_session_factory
from macropulse.db.models import BriefingClaim, BriefingRun
from macropulse.metrics.engine import (
    latest_vintage_records,
    latest_vintage_series,
    observation_id_map,
    persist_derived,
)
from macropulse.metrics.gates import evaluate_gate
from macropulse.metrics.standardize import standardize_series
from macropulse.metrics.transforms import FORMULAS
from macropulse.quality.missingness import missingness_report
from macropulse.scope import COUNTRIES
from macropulse.views.client import QueryServiceClient
from macropulse.views.theme import (
    CONTEXT_GREY,
    COUNTRY_COLORS,
    EPISODE_WASH,
    LINE_WIDTH_FOCUS,
)

REPO = Path(__file__).resolve().parents[2]
DEMO_DB = "macropulse_s18_demo"
DEMO_URL = "postgresql+psycopg://macropulse:macropulse@localhost:5432/" + DEMO_DB
ADMIN_URL = "postgresql+psycopg://macropulse:macropulse@localhost:5432/postgres"
PY = str(REPO / ".venv" / "bin" / "python")
API_PORT = 8801
API_URL = f"http://127.0.0.1:{API_PORT}"
EVIDENCE = REPO / "evidence" / "S18"

WHO_URL = "https://www.who.int/news/item/27-04-2020-who-timeline---covid-19"


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def base_env() -> dict[str, str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = DEMO_URL
    src = str(REPO / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def create_disposable_db() -> None:
    admin = create_engine(ADMIN_URL, future=True, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {DEMO_DB} WITH (FORCE)"))
        conn.execute(text(f"CREATE DATABASE {DEMO_DB}"))
    admin.dispose()

    print("== disposable demo database: alembic upgrade head ==")
    proc = subprocess.run(
        [PY, "-m", "alembic", "upgrade", "head"],
        cwd=REPO,
        env=base_env(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    print(proc.stdout.strip() or proc.stderr.strip())
    if proc.returncode != 0:
        raise SystemExit(f"alembic failed: {proc.stderr}")


def drop_disposable_db() -> None:
    admin = create_engine(ADMIN_URL, future=True, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        # WITH (FORCE) terminates lingering pooled connections (Postgres
        # 13+) so a mid-script failure still cleans up the disposable DB.
        conn.execute(text(f"DROP DATABASE IF EXISTS {DEMO_DB} WITH (FORCE)"))
    admin.dispose()
    print(f"== disposable database {DEMO_DB} dropped ==")


def leg_ingest(log_path: str) -> int:
    step("LEG 1 INGEST: scheduled refresh CLI, live World Bank fetch")
    print(f"$ PYTHONPATH=src python -m macropulse.ops.refresh"
          f" --indicator gdp_real_growth --trigger manual --log-file {log_path}")
    proc = subprocess.run(
        [PY, "-m", "macropulse.ops.refresh",
         "--indicator", "gdp_real_growth", "--trigger", "manual",
         "--log-file", log_path],
        cwd=REPO,
        env=base_env(),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    for line in proc.stderr.splitlines()[:3]:
        print(f"    {line}")
    print(f"-> exit code {proc.returncode} (expected 0: all series are keyless WB)")
    return proc.returncode


def leg_derive() -> dict:
    step("LEG 2 DERIVE: gate -> robust_z5 -> derived store (S08/S09 engine)")
    entry = next(i for i in CATALOG if i.indicator_id == "gdp_real_growth")
    print(f"catalog: direction={entry.direction} frequency={entry.frequency}")
    engine = make_engine(DEMO_URL)
    factory = make_session_factory(engine)
    per_country: dict[str, dict] = {}
    try:
        with factory() as session:
            for country in COUNTRIES:
                iso = country.iso3
                points = latest_vintage_series(session, "gdp_real_growth", iso)
                records = latest_vintage_records(session, "gdp_real_growth", iso)
                report = missingness_report(points, entry.frequency)
                gate = evaluate_gate(f"gdp_real_growth/{iso}", report, records)
                standardized = standardize_series(points, 5, entry.direction, entry.frequency)
                id_map = observation_id_map(session, "gdp_real_growth", iso)
                written = persist_derived(
                    session, "gdp_real_growth.robust_z5", iso, standardized, "robust_z", id_map
                )
                session.commit()
                n_2020 = sum(1 for w in written if w.period == date(2020, 1, 1))
                per_country[iso] = {
                    "points": len(points),
                    "first": points[0].period if points else None,
                    "last": points[-1].period if points else None,
                    "coverage": report.coverage,
                    "published": gate.published,
                    "failed": [c.name for c in gate.checks if not c.passed],
                    "written": len(written),
                    "written_2020": n_2020,
                    "z_2020": next(
                        (w.value for w in written if w.period == date(2020, 1, 1)), None
                    ),
                }
                print(
                    f"   {iso}: {len(points)} pts {per_country[iso]['first']}..{per_country[iso]['last']}"
                    f" coverage={report.coverage:.3f} gate={'published' if gate.published else 'HELD'}"
                    f" -> {len(written)} derived (2020: {'yes' if n_2020 else 'no'})"
                )
                if not gate.published:
                    print(f"      failed checks: {per_country[iso]['failed']}")
    finally:
        engine.dispose()
    return per_country


def leg_serve() -> subprocess.Popen:
    step(f"LEG 3 SERVE: uvicorn on the demo DB (port {API_PORT})")
    # A stale server from an earlier crashed run would still answer /health
    # while the new uvicorn silently fails to bind, serving the wrong data.
    # Refuse to start on an occupied port instead.
    import socket

    probe = socket.socket()
    try:
        probe.bind(("127.0.0.1", API_PORT))
    except OSError as exc:
        raise SystemExit(
            f"port {API_PORT} is already in use; kill the stale service first ({exc})"
        ) from exc
    finally:
        probe.close()
    proc = subprocess.Popen(
        [PY, "-m", "uvicorn", "macropulse.api.main:app",
         "--port", str(API_PORT), "--log-level", "warning"],
        cwd=REPO,
        env=base_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            health = httpx.get(f"{API_URL}/health", timeout=2.0).json()
            if health.get("status") == "ok":
                print(f"health: {health}")
                return proc
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    proc.terminate()
    raise SystemExit(f"service did not become healthy on {API_URL}")


def leg_byte_check(client: QueryServiceClient) -> dict:
    step("LEG 3 SERVE: provenance byte-check (API row vs stored row)")
    engine = create_engine(DEMO_URL, future=True)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT no.value, no.unit, no.vintage, no.evidence_label,"
                " no.quality_grade, sc.system, sc.code"
                " FROM normalized_observations no"
                " JOIN source_catalog sc ON sc.indicator_id = no.indicator_id"
                " AND sc.role = 'primary'"
                " WHERE no.indicator_id = 'gdp_real_growth' AND no.country_iso3 = 'USA'"
                " AND no.period = '2020-01-01'"
                " ORDER BY no.vintage DESC LIMIT 1"
            )
        ).fetchone()
    engine.dispose()
    value, unit, vintage, evidence, grade, system, code = row
    print(f"stored:  USA 2020 value={value!r} unit={unit} vintage={vintage}")
    print(f"         evidence={evidence} grade={grade} source={system}/{code}")

    served = [
        o for o in client.observations(
            indicator_id="gdp_real_growth", country_iso3="USA", latest_vintage=True
        )
        if o["period"] == "2020-01-01"
    ]
    assert len(served) == 1, f"expected one 2020 observation, got {len(served)}"
    obs = served[0]
    print(f"served:  USA 2020 value={obs['value']!r} unit={obs['unit']} vintage={obs['vintage']}")
    print(f"         evidence={obs['evidence_label']} grade={obs['quality_grade']}"
          f" source={obs['source']['system']}/{obs['source']['code']}")

    checks = {
        "value_repr": repr(obs["value"]) == repr(float(value)),
        "unit": obs["unit"] == unit,
        "vintage": obs["vintage"] == str(vintage),
        "evidence": obs["evidence_label"] == evidence,
        "grade": obs["quality_grade"] == grade,
        "source": (obs["source"]["system"], obs["source"]["code"]) == (system, code),
    }
    for name, ok in checks.items():
        print(f"   {name:<12} {'MATCH' if ok else 'MISMATCH'}")
    return checks


def leg_derived_served(client: QueryServiceClient) -> dict:
    step("LEG 3 SERVE: derived metrics + methodology served back")
    metrics = client.metrics(metric_key="gdp_real_growth.robust_z5", country_iso3="USA")
    m2020 = next(m for m in metrics if m["period"] == "2020-01-01")
    print(f"/metrics USA 2020: value={m2020['value']!r} formula_ref={m2020['formula_ref']}"
          f" version={m2020['version']}")

    # Lineage (input observation ids) lives in the DB: the S13 contract is
    # pinned and serves value + formula_ref + version, not the inputs JSON.
    engine = create_engine(DEMO_URL, future=True)
    with engine.connect() as conn:
        stored = conn.execute(
            text(
                "SELECT value, inputs FROM derived_metrics"
                " WHERE metric_key = 'gdp_real_growth.robust_z5'"
                " AND country_iso3 = 'USA' AND period = '2020-01-01'"
            )
        ).fetchone()
        defn = conn.execute(
            text(
                "SELECT version, definition FROM metric_versions mv"
                " JOIN derived_metrics dm ON dm.id = mv.metric_id"
                " WHERE dm.metric_key = 'gdp_real_growth.robust_z5' AND dm.period = '2020-01-01'"
                " AND dm.country_iso3 = 'USA'"
            )
        ).fetchone()
    engine.dispose()
    print(f"stored:            value={stored[0]!r}")
    print(f"lineage (DB side): {stored[1]}")
    print(f"metric_versions:   {defn[0]}: {defn[1][:80]}...")

    defs = client._get("/methodology/metrics/gdp_real_growth.robust_z5", {})
    return {
        "value_repr": repr(m2020["value"]) == repr(float(stored[0])),
        "formula_ref": m2020["formula_ref"] == "robust_z",
        "definition_served": defs[0]["definition"] == FORMULAS["robust_z"],
        "definition_stored": defn[1] == FORMULAS["robust_z"],
        "z_value": float(m2020["value"]),
    }


def collect_figures(at) -> list[dict]:
    """All plotly figure JSONs rendered in the app, in render order.

    ``at.get("plotly_chart")`` searches the whole element tree (charts
    live inside tab blocks, which have no top-level plotly_chart
    accessor); each element's proto carries the full figure spec.
    """
    return [json.loads(el.proto.spec) for el in at.get("plotly_chart")]


def leg_render() -> dict:
    step("LEG 4 RENDER: AppTest drives the real dashboard against the service")
    from streamlit.testing.v1 import AppTest

    os.environ["MACROPULSE_API_URL"] = API_URL
    at = AppTest.from_file(str(REPO / "app" / "dashboard.py"), default_timeout=90)
    at.run()
    assert not at.exception, f"app raised: {[e.value for e in at.exception]}"
    assert not at.error, f"app rendered an error: {[e.value for e in at.error]}"
    print("boot ok; title:", at.title[0].value)
    print("tabs:", [t.label for t in at.tabs])

    # The demo store holds gdp_real_growth only; every widget default is
    # alphabetically-first (account_ownership_pct indicator, BRA country
    # and focus), which honestly renders no_data here. Select the
    # indicator that has data and make USA the focus - exactly what a
    # reader would do, and what the checks below assert explicitly.
    # (set_value takes the RAW widget value - the indicator_id / iso3 -
    # not the format_func display label.)
    at.multiselect[0].set_value(["gdp_real_growth"])
    indicator_box = next(sb for sb in at.selectbox if sb.label == "Indicator")
    indicator_box.set_value("gdp_real_growth")
    next(sb for sb in at.selectbox if sb.label == "Country").set_value("USA")
    next(
        sb for sb in at.selectbox if sb.label.startswith("Focus country")
    ).set_value("USA")
    at.run()
    assert not at.exception, f"app raised: {[e.value for e in at.exception]}"
    assert not at.error, f"app rendered an error: {[e.value for e in at.error]}"

    # What the app rendered on the tabs this leg does not drive: the
    # provenance tab still holds its defaults (BRA / the indicator with
    # no data in this store), and its honest no_data info is itself
    # evidence the boundary works - nothing is inferred, nothing errors.
    print("info messages rendered:", [i.value[:90] for i in at.info])
    print(
        "USA observations served (all indicators, latest vintage):",
        len(QueryServiceClient(API_URL).observations(country_iso3="USA", latest_vintage=True)),
    )

    focus_box = next(
        sb for sb in at.selectbox if sb.label.startswith("Focus country")
    )
    print(f"focus selectbox: {focus_box.label!r} with {len(focus_box.options)} options")

    figures = collect_figures(at)
    assert len(figures) == 2, f"expected country + comparison charts, got {len(figures)}"
    country_fig, comparison_fig = (
        figures if len(figures[0]["data"]) == 1 else (figures[1], figures[0])
    )

    print("\n-- country view (USA, single series) --")
    trace = country_fig["data"][0]
    layout = country_fig["layout"]
    country_checks = {
        "single_trace": len(country_fig["data"]) == 1,
        "entity_color": trace["line"]["color"] == COUNTRY_COLORS["USA"],
        "serif_title": "Spectral" in layout["title"]["font"]["family"],
        "transparent_bg": layout.get("plot_bgcolor") == "rgba(0,0,0,0)",
        "episode_band": (
            len(layout.get("shapes", [])) == 1
            and layout["shapes"][0].get("fillcolor") == EPISODE_WASH
            and layout["shapes"][0].get("x0") == "2020-01-01"
            and layout["shapes"][0].get("x1") == "2020-12-31"
        ),
        "episode_callout": (
            len(layout.get("annotations", [])) == 1
            and "WHO characterizes COVID-19" in layout["annotations"][0].get("text", "")
        ),
    }
    for name, ok in country_checks.items():
        print(f"   {name:<16} {'PASS' if ok else 'FAIL'}")

    print("\n-- comparison view (10 economies, focus USA) --")
    traces = {t["name"]: t for t in comparison_fig["data"]}
    layout = comparison_fig["layout"]
    annotation_texts = [a.get("text", "") for a in layout.get("annotations", [])]
    comparison_checks = {
        "ten_traces": len(traces) == 10,
        "focus_wears_color": (
            traces["USA"]["line"]["color"] == COUNTRY_COLORS["USA"]
            and traces["USA"]["line"]["width"] == LINE_WIDTH_FOCUS
        ),
        "context_wears_grey": (
            all(traces[c]["line"]["color"] == CONTEXT_GREY for c in traces if c != "USA")
        ),
        "one_colored_line": (
            sum(1 for t in traces.values() if t["line"]["color"] != CONTEXT_GREY) == 1
        ),
        "focus_only_in_legend": (
            traces["USA"]["showlegend"] is True
            and all(traces[c].get("showlegend") is False for c in traces if c != "USA")
        ),
        "episode_band": any(
            s.get("fillcolor") == EPISODE_WASH for s in layout.get("shapes", [])
        ),
        "episode_callout": any("WHO characterizes COVID-19" in t for t in annotation_texts),
        "direct_focus_label": "USA" in annotation_texts,
    }
    for name, ok in comparison_checks.items():
        print(f"   {name:<22} {'PASS' if ok else 'FAIL'}")

    captions = [c.value for c in at.caption]
    band_captions = [c for c in captions if "Shaded band" in c]
    print(f"\nband captions rendered: {len(band_captions)}")
    for caption in band_captions:
        print(f"   {caption[:120]}...")
    caption_checks = {
        "who_citation": any(WHO_URL in c for c in band_captions),
        "who_source": any("World Health Organization" in c for c in band_captions),
        "published_date": any("published 2020-04-27" in c for c in band_captions),
        "as_observed": any("drawn as observed" in c for c in band_captions),
    }
    for name, ok in caption_checks.items():
        print(f"   {name:<16} {'PASS' if ok else 'FAIL'}")

    print("\n-- focus switch USA -> CHN (color follows the entity, not the rank) --")
    focus_box = next(
        sb for sb in at.selectbox if sb.label.startswith("Focus country")
    )
    focus_box.set_value("CHN")  # raw widget value, not the display label
    at.run()
    assert not at.exception, f"app raised after focus switch: {[e.value for e in at.exception]}"
    assert not at.error, f"app rendered an error after switch: {[e.value for e in at.error]}"
    figures = collect_figures(at)
    comparison_fig = (
        figures[1] if len(figures[1]["data"]) == 10 else figures[0]
    )
    traces = {t["name"]: t for t in comparison_fig["data"]}
    annotation_texts = [a.get("text", "") for a in comparison_fig["layout"].get("annotations", [])]
    switch_checks = {
        "chn_wears_own_color": traces["CHN"]["line"]["color"] == COUNTRY_COLORS["CHN"],
        "chn_not_usa_hue": traces["CHN"]["line"]["color"] != COUNTRY_COLORS["USA"],
        "usa_now_grey": traces["USA"]["line"]["color"] == CONTEXT_GREY,
        "direct_label_chn": "CHN" in annotation_texts,
    }
    for name, ok in switch_checks.items():
        print(f"   {name:<22} {'PASS' if ok else 'FAIL'}")

    export = {
        "figure-comparison-focus-chn.json": comparison_fig,
    }
    for name, figure in export.items():
        path = EVIDENCE / name
        path.write_text(json.dumps(figure, indent=1))
        print(f"figure exported: evidence/S18/{name}")
    import plotly.graph_objects as go

    go.Figure(comparison_fig).write_html(
        str(EVIDENCE / "figure-comparison-focus-chn.html"),
        include_plotlyjs="cdn",
        full_html=True,
    )
    print("figure exported: evidence/S18/figure-comparison-focus-chn.html")

    return {
        "country": country_checks,
        "comparison": comparison_checks,
        "captions": caption_checks,
        "switch": switch_checks,
    }


def leg_brief(client: QueryServiceClient) -> dict:
    step("LEG 5 BRIEF: S16 briefing from the served facts, persisted")
    observations = client.observations(latest_vintage=True)
    indicators = client.indicators()
    names = {i["indicator_id"]: i["name"] for i in indicators}
    print(f"observations served: {len(observations)}; indicators: {sorted(names)}")

    facts = BriefingFacts.from_observations(observations, names)
    print(
        f"facts: {len(facts.facts)} observations, {len(facts.missing)} missing,"
        f" {len(facts.excluded)} excluded"
    )
    claims = build_claims(facts)
    adjudicated = adjudicate_all(claims, facts)
    n_valid = sum(1 for _, a in adjudicated if a.validated)
    print(f"claims: {len(adjudicated)} built, {n_valid} validated")

    document = render_briefing(facts, adjudicated)
    banned = check_prose(document)
    print(f"banned phrases in rendered document: {banned}")
    assert banned == []

    factory = make_session_factory(make_engine(DEMO_URL))
    with factory() as session:
        run_id = record_briefing_run(
            session,
            model=DETERMINISTIC_MODEL,
            prompt_version=DETERMINISTIC_PROMPT_VERSION,
            adjudicated=adjudicated,
        )
        rows = (
            session.query(BriefingClaim)
            .filter(BriefingClaim.briefing_run_id == run_id)
            .all()
        )
        run = session.get(BriefingRun, run_id)
        print(
            f"persisted run {run_id}: model={run.model!r} status={run.status!r}"
            f" claims={len(rows)}"
            f" ({sum(1 for r in rows if r.validated)} validated,"
            f" {sum(1 for r in rows if not r.validated)} rejected)"
        )
    # One full claim as evidence: every validated claim carries its value,
    # period, source, vintage, evidence label, and quality grade inline.
    # (The briefing reports the CURRENT picture - latest periods - so the
    # 2020 window belongs to LEG 6, not to these claims.)
    example = next(c.text for c, a in adjudicated if a.validated)
    print("example validated claim (provenance inline):")
    print(f"   {example}")
    return {"claims": len(adjudicated), "validated": n_valid}


def leg_case(client: QueryServiceClient) -> list[tuple[str, float | None]]:
    step("LEG 6 CASE: observed 2020 panel values beside the documented window")
    print(
        "The historical case presents the observed 2020 real-GDP-growth values"
        "\nwith the documented WHO event window marked as a band. The band and"
        "\nthe values are shown together; no causal connection is drawn."
    )
    observations = [
        o for o in client.observations(
            indicator_id="gdp_real_growth", latest_vintage=True
        )
        if o["period"] == "2020-01-01"
    ]
    values = [(o["country_iso3"], o["value"]) for o in observations]
    values.sort(key=lambda pair: pair[0])
    for iso, value in values:
        print(f"   {iso}: {value!r}")
    print(
        f"\nepisode: WHO characterizes COVID-19 as a pandemic (11 March 2020)"
        f"\nsource:  World Health Organization, 'Archived: WHO Timeline - COVID-19',"
        f"\n         {WHO_URL}, published 2020-04-27 (live-verified 2026-09-18)"
    )
    return values


def main() -> int:
    os.makedirs(EVIDENCE, exist_ok=True)
    create_disposable_db()
    server: subprocess.Popen | None = None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            code_ingest = leg_ingest(str(Path(tmp) / "refresh.jsonl"))
        derive = leg_derive()
        server = leg_serve()
        client = QueryServiceClient(API_URL)
        byte_checks = leg_byte_check(client)
        derived_checks = leg_derived_served(client)
        render_checks = leg_render()
        brief = leg_brief(client)
        case_values = leg_case(client)

        print("\n=== SUMMARY ===")
        print(f"ingest exit code:        {code_ingest} (expected 0)")
        print(f"series published by gate: {sum(1 for d in derive.values() if d['published'])}/10")
        print(f"derived 2020 rows:       {sum(1 for d in derive.values() if d['written_2020'])}/10")
        print(f"byte-check mismatches:   {[k for k, v in byte_checks.items() if not v]}")
        print(f"derived-serve failures:  {[k for k, v in derived_checks.items() if k != 'z_value' and not v]}")
        for group in ("country", "comparison", "captions", "switch"):
            failed = [k for k, v in render_checks[group].items() if not v]
            print(f"render {group:<11} failures: {failed}")
        print(f"brief claims:            {brief['validated']}/{brief['claims']} validated, banned phrases: none")
        print(f"case 2020 values:        {len(case_values)}/10 economies observed")

        ok = (
            code_ingest == 0
            and all(d["published"] for d in derive.values())
            and all(d["written_2020"] for d in derive.values())
            and all(byte_checks.values())
            and all(v for k, v in derived_checks.items() if k != "z_value")
            and all(all(g.values()) for g in render_checks.values())
            and brief["validated"] == brief["claims"]
            and brief["claims"] > 0
            and len(case_values) == 10
        )
        print(f"\nDEMO {'PASSED' if ok else 'FAILED'}")
        return 0 if ok else 1
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=30)
        drop_disposable_db()


if __name__ == "__main__":
    raise SystemExit(main())
