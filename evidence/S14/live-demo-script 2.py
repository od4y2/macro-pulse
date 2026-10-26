"""S14 live demo: the dashboard rendered against the live query service.

Uses Streamlit's AppTest harness (``streamlit.testing.v1.AppTest``) to
execute the real ``app/dashboard.py`` script against the real running
service (``http://127.0.0.1:8000``) and inspect the rendered elements -
the same runtime a browser session would drive, without a browser.

Prerequisites (both running against the dev DB seeded with the live WB
fetch):

    PYTHONPATH=src .venv/bin/python -m uvicorn macropulse.api.main:app --port 8000
    # dev DB seeded: 10 economies x 11 years gdp_real_growth, evidence_label=real

Run:

    PYTHONPATH=src .venv/bin/python evidence/S14/live-demo-script.py
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

DASHBOARD = str(Path(__file__).resolve().parents[2] / "app" / "dashboard.py")


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def run_app() -> AppTest:
    at = AppTest.from_file(DASHBOARD, default_timeout=60)
    at.run()
    assert not at.exception, f"app raised: {[e.value for e in at.exception]}"
    return at


def main() -> None:
    step("boot the dashboard (default view)")
    at = run_app()
    print("exceptions:", len(at.exception))
    print("title:", at.title[0].value)
    print("claims caption:", at.caption[0].value)
    print("tabs:", [t.label for t in at.tabs])

    step("country view: USA, all provenance columns, real WB values")
    country_df = at.dataframe[0].value
    print("columns:", list(country_df.columns))
    print(country_df.head(3).to_string())

    step("comparison view: 10-economy matrix + coverage counts")
    matrix = at.dataframe[1].value
    print("matrix shape:", matrix.shape)
    print(matrix.head(3).to_string())
    coverage = at.dataframe[2].value
    print("coverage:", coverage.to_dict("records")[:2], "...")

    step("provenance view: full vintage chain")
    prov = at.dataframe[3].value
    print("shape:", prov.shape)
    print(prov.head(2).to_string())
    print("metrics:", [(m.label, m.value) for m in at.metric])

    step("view switch: provenance -> CHN, comparison -> ZAF only")
    at.selectbox[2].set_value([o for o in at.selectbox[2].options if o.startswith("CHN")][0])
    at.run()
    assert not at.exception
    print("provenance CHN rows:", len(at.dataframe[3].value))
    at.multiselect[1].set_value(["ZAF"])
    at.run()
    assert not at.exception
    print("comparison ZAF matrix rows:", len(at.dataframe[1].value))
    print("comparison ZAF coverage:", at.dataframe[2].value.to_dict("records"))

    step("empty state: no indicators selected")
    at.multiselect[0].set_value([])
    at.run()
    assert not at.exception
    print("info:", [i.value for i in at.info])

    step("demo complete - all views render real data with provenance")


if __name__ == "__main__":
    main()
