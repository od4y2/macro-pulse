"""S20 demo rehearsal: the production stack, end to end (output captured to
evidence/S20/demo-rehearsal.txt).

Unlike the S18 demo (which proved the chain on a DISPOSABLE database),
this rehearsal exercises what go-live actually serves: the PRODUCTION
Neon database, loaded by the S20 release pass (full-catalog refresh +
release sweep). Every leg runs through its production entry point:

1. SERVE   - uvicorn on production Neon (S13); health; the FULL-CATALOG
   probe: every catalog indicator served with its observation count, and
   the release-sweep derived metrics served back through /metrics.
2. RENDER  - AppTest drives the real app/dashboard.py against the
   production service: full 12-indicator selector, gdp_real_growth /
   USA focus render, no exceptions, honest states elsewhere.
3. BRIEF   - S16 briefing from the served production facts, adjudicated,
   banned-phrase-checked, and PERSISTED to production (the audit row is
   part of the rehearsal; the briefing layer is a site feature).
4. CASE    - the documented historical case (observed 2020 values beside
   the WHO window) plus the China case-study registry coverage after the
   S20 provincial expansion.

Run (production URL supplied via env, never hardcoded):

    NEON="$(grep '^NEON_DATABASE_URL=' .env.local | cut -d= -f2- | tr -d '"')"
    DATABASE_URL="${NEON/#postgresql:\/\//postgresql+psycopg://}" \
    PYTHONPATH=src .venv/bin/python evidence/S20/demo-rehearsal.py \
        | tee evidence/S20/demo-rehearsal.txt
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

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
from macropulse.case_study.china_health import (
    PROVINCES,
    VERIFIED_RECORDS,
    recorded_regions,
    unrecorded_provinces,
)
from macropulse.catalog import CATALOG
from macropulse.db.base import make_engine, make_session_factory
from macropulse.scope import COUNTRIES
from macropulse.views.client import QueryServiceClient

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / ".venv" / "bin" / "python")
API_PORT = 8802
API_URL = f"http://127.0.0.1:{API_PORT}"
WHO_URL = "https://www.who.int/news/item/27-04-2020-who-timeline---covid-19"


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def base_env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(REPO / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def leg_serve() -> subprocess.Popen:
    step(f"LEG 1 SERVE: uvicorn on PRODUCTION Neon (port {API_PORT})")
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
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            health = httpx.get(f"{API_URL}/health", timeout=5.0).json()
            if health.get("status") == "ok":
                print(f"health: {health}")
                return proc
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    proc.terminate()
    raise SystemExit(f"service did not become healthy on {API_URL} (Neon cold start?)")


def leg_full_catalog(client: QueryServiceClient) -> dict:
    step("LEG 1 SERVE: full-catalog probe (12 indicators, 10 economies)")
    countries = client.countries()
    indicators = client.indicators()
    print(f"countries served: {len(countries)}; indicators served: {len(indicators)}")

    served = {}
    for ind in CATALOG:
        rows = client.observations(
            indicator_id=ind.indicator_id, latest_vintage=True
        )
        economies = len({r["country_iso3"] for r in rows})
        observed = sum(1 for r in rows if r["value"] is not None)
        served[ind.indicator_id] = {
            "rows": len(rows),
            "economies": economies,
            "observed": observed,
        }
        print(
            f"   {ind.indicator_id:<28} rows={len(rows):>5}"
            f" economies={economies} observed={observed}"
        )

    derived = client.metrics(metric_key="gdp_real_growth.robust_z5", country_iso3="USA")
    print(
        f"/metrics gdp_real_growth.robust_z5 USA: {len(derived)} rows"
        f" ({derived[0]['period']}..{derived[-1]['period']})"
    )
    return {
        "countries": len(countries),
        "indicators": len(indicators),
        "catalog_indicators_served": len(served),
        "derived_served": len(derived),
    }


def leg_render() -> dict:
    step("LEG 2 RENDER: AppTest drives the dashboard against production")
    from streamlit.testing.v1 import AppTest

    os.environ["MACROPULSE_API_URL"] = API_URL
    at = AppTest.from_file(str(REPO / "app" / "dashboard.py"), default_timeout=120)
    at.run()
    assert not at.exception, f"app raised: {[e.value for e in at.exception]}"
    assert not at.error, f"app rendered an error: {[e.value for e in at.error]}"
    print("boot ok; title:", at.title[0].value)

    indicator_box = next(sb for sb in at.selectbox if sb.label == "Indicator")
    print(f"indicator options in production: {len(indicator_box.options)}")
    next(sb for sb in at.selectbox if sb.label == "Country").set_value("USA")
    indicator_box.set_value("gdp_real_growth")
    next(
        sb for sb in at.selectbox if sb.label.startswith("Focus country")
    ).set_value("USA")
    at.run()
    assert not at.exception, f"app raised: {[e.value for e in at.exception]}"
    assert not at.error, f"app rendered an error: {[e.value for e in at.error]}"

    figures = [
        json.loads(el.proto.spec)
        for el in at.get("plotly_chart")
    ]
    print(f"figures rendered on the tabs this leg drives: {len(figures)}")

    # The provenance tab on production data: the revision chain is live.
    prov_obs = QueryServiceClient(API_URL).observations(
        indicator_id="gdp_real_growth", country_iso3="USA"
    )
    periods = {o["period"] for o in prov_obs}
    with_revisions = sum(
        1 for p in periods if sum(1 for o in prov_obs if o["period"] == p) > 1
    )
    print(f"provenance view (USA gdp_real_growth): {len(prov_obs)} vintage rows,"
          f" {with_revisions} periods with >1 vintage (RQ4 chain)")
    return {
        "indicator_options": len(indicator_box.options),
        "figures": len(figures),
        "revision_periods": with_revisions,
    }


def leg_brief(client: QueryServiceClient) -> dict:
    step("LEG 3 BRIEF: S16 briefing from production facts, persisted")
    observations = client.observations(latest_vintage=True)
    indicators = client.indicators()
    names = {i["indicator_id"]: i["name"] for i in indicators}
    print(f"observations served: {len(observations)}; indicators: {len(names)}")

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

    factory = make_session_factory(make_engine(os.environ["DATABASE_URL"]))
    with factory() as session:
        run_id = record_briefing_run(
            session,
            model=DETERMINISTIC_MODEL,
            prompt_version=DETERMINISTIC_PROMPT_VERSION,
            adjudicated=adjudicated,
        )
        print(f"persisted production briefing run: id={run_id}")
    example = next(c.text for c, a in adjudicated if a.validated)
    print("example validated claim (provenance inline):")
    print(f"   {example}")
    return {"claims": len(adjudicated), "validated": n_valid, "run_id": run_id}


def leg_case(client: QueryServiceClient) -> dict:
    step("LEG 4 CASE: 2020 observed values + China registry coverage")
    observations = [
        o for o in client.observations(
            indicator_id="gdp_real_growth", latest_vintage=True
        )
        if o["period"] == "2020-01-01"
    ]
    values = sorted((o["country_iso3"], o["value"]) for o in observations)
    for iso, value in values:
        print(f"   {iso}: {value!r}")
    print(
        f"\nepisode: WHO characterizes COVID-19 as a pandemic (11 March 2020)"
        f"\nsource:  World Health Organization, 'Archived: WHO Timeline - COVID-19',"
        f"\n         {WHO_URL}, published 2020-04-27 (live-verified 2026-09-18)"
    )

    recorded = recorded_regions(VERIFIED_RECORDS)
    unrecorded = unrecorded_provinces(VERIFIED_RECORDS)
    print(
        f"\nChina case-study registry after the S20 provincial expansion:"
        f"\n   provinces with verified records: {len(recorded)}/{len(PROVINCES)}"
    )
    if unrecorded:
        print(f"   still unrecorded (named, not imputed): {', '.join(unrecorded)}")
    else:
        print("   no unrecorded provinces remain")
    per_year = {}
    for record in VERIFIED_RECORDS:
        per_year.setdefault(record.year, 0)
        per_year[record.year] += 1
    print(f"   records by data year: {dict(sorted(per_year.items()))}")
    return {
        "economies_2020": len(values),
        "provinces_recorded": len(recorded),
        "provinces_total": len(PROVINCES),
    }


def main() -> int:
    if "neon" not in (os.environ.get("DATABASE_URL") or ""):
        raise SystemExit(
            "refusing to run: DATABASE_URL does not point at the production"
            " Neon database (this rehearsal exercises production, not dev)"
        )
    server = None
    try:
        server = leg_serve()
        client = QueryServiceClient(API_URL)
        serve = leg_full_catalog(client)
        render = leg_render()
        brief = leg_brief(client)
        case = leg_case(client)

        print("\n=== SUMMARY ===")
        print(f"countries served:          {serve['countries']}/10")
        print(f"indicators served:         {serve['indicators']}/12")
        print(f"catalog indicators probed: {serve['catalog_indicators_served']}/12")
        print(f"derived rows served (USA): {serve['derived_served']}")
        print(f"dashboard indicator opts:  {render['indicator_options']}")
        print(f"brief claims:              {brief['validated']}/{brief['claims']} validated")
        print(f"case 2020 values:          {case['economies_2020']}/10 economies")
        print(
            f"case-study provinces:      {case['provinces_recorded']}"
            f"/{case['provinces_total']} recorded"
        )

        ok = (
            serve["countries"] == len(COUNTRIES)
            and serve["indicators"] == len(CATALOG)
            and serve["catalog_indicators_served"] == len(CATALOG)
            and serve["derived_served"] > 0
            and render["indicator_options"] == len(CATALOG)
            and brief["validated"] == brief["claims"]
            and brief["claims"] > 0
            and case["economies_2020"] == len(COUNTRIES)
        )
        print(f"\nREHEARSAL {'PASSED' if ok else 'FAILED'}")
        return 0 if ok else 1
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=30)


if __name__ == "__main__":
    sys.exit(main())
