"""S15 live demo: freshness labels, quality badges, provenance hover, and
limitations rendered by the real dashboard against the live service.

Runs ``app/dashboard.py`` via Streamlit's AppTest harness (the same runtime
a browser drives) against the running query service; the dev DB holds the
live-fetched WB panel (10 economies x 11 years, evidence_label=real).

Run:

    PYTHONPATH=src .venv/bin/python evidence/S15/live-demo-script.py
"""

from __future__ import annotations

from datetime import date
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
    step("boot the dashboard (labels layer active)")
    at = run_app()
    print("exceptions:", len(at.exception))
    print("tabs:", [t.label for t in at.tabs])
    print("date_input label:", at.date_input[0].label)
    print("as-of default:", at.date_input[0].value)

    step("labels legend: badges, freshness convention, evidence vocabulary")
    markdowns = [m.value for m in at.markdown]
    badge_in_legend = any("● official" in m for m in markdowns)
    print("legend shows quality badges:", badge_in_legend)
    fresh_in_legend = any(
        "*current*" in m or "current" in m and "frequency steps" in m for m in markdowns
    )
    print("legend shows freshness convention:", fresh_in_legend)
    print("legend shows evidence vocabulary:", any("external" in m for m in markdowns))

    step("country view: freshness table + quality badges + chart caption")
    # dataframes: [0] country rows, [1] freshness
    country_rows = at.dataframe[0].value
    print(
        "country view table quality column:",
        country_rows["quality_grade"].unique().tolist(),
    )
    freshness = at.dataframe[1].value
    print("freshness columns:", list(freshness.columns))
    print(freshness.to_string())
    print("chart caption:", next(c.value for c in at.caption if "economy" in c.value))

    step("comparison view: coverage merged with freshness states")
    merged = at.dataframe[3].value
    print("merged columns:", list(merged.columns))
    print(merged[["country", "last_observed", "age_steps", "state"]].to_string())

    step("provenance view: badges on the vintage chain")
    at.selectbox[2].set_value(
        next(o for o in at.selectbox[2].options if o.startswith("CHN"))
    )
    at.run()
    assert not at.exception
    prov = at.dataframe[4].value
    print("provenance quality column:", prov["quality_grade"].unique().tolist())

    step("freshness reacts to the as-of date (the label is computed, not stored)")
    # Move as-of to 2028-01-01: last observed 2025-01-01 annual -> 24 months
    # = exactly 2 steps -> every state must flip to lagging.
    at.date_input[0].set_value(date(2028, 1, 1))
    at.run()
    assert not at.exception
    merged = at.dataframe[3].value
    print("as-of 2028-01-01 states:", merged["state"].unique().tolist())
    freshness = at.dataframe[1].value
    print("country-view freshness at 2028-01-01:")
    print(
        freshness[["indicator_id", "last_observed", "age_steps", "state"]].to_string()
    )

    step("limitations expander renders catalog methodology")
    markdowns = [m.value for m in at.markdown]
    print("limitations rendered:", any("limitations:" in m for m in markdowns))
    print("comparability rendered:", any("comparability:" in m for m in markdowns))

    step("demo complete - labels are computed from data + the supplied as-of")


if __name__ == "__main__":
    main()
