"""S15 label tests: freshness states, quality badges, chart captions,
coverage/freshness merge, and the hover provenance added to chart traces.

All inputs are synthetic fixtures (test payloads, never observations).
"""

from __future__ import annotations

from datetime import date

import pytest

from macropulse.views.assembly import chart_traces
from macropulse.views.labels import (
    FRESHNESS_LAG_STEPS,
    FRESHNESS_STATES,
    GRADE_MEANINGS,
    QUALITY_BADGES,
    chart_caption,
    freshness_summary,
    merge_freshness,
    quality_badge,
)


def obs(**overrides: object) -> dict:
    """One observation record shaped like the service's ObservationOut."""
    base: dict[str, object] = {
        "indicator_id": "gdp_real_growth",
        "country_iso3": "USA",
        "period": "2025-01-01",
        "value": 2.5,
        "unit": "percent_per_year",
        "frequency": "annual",
        "seasonal_adjustment": "varies",
        "source": {
            "system": "world_bank",
            "code": "NY.GDP.MKTP.KD.ZG",
            "role": "primary",
            "verified": "confirmed",
            "coverage": "test",
        },
        "release_time": "2026-01-25T13:30:00Z",
        "retrieval_time": "2026-01-25T14:00:00Z",
        "vintage": "2026-01-25",
        "evidence_label": "real",
        "quality_grade": "official",
        "missing_reason": None,
    }
    base.update(overrides)
    return base


# --- quality badges --------------------------------------------------------------


def test_badge_covers_the_closed_grade_vocabulary() -> None:
    grades = ("ungraded", "official", "preliminary", "revised", "estimated", "flagged")
    for grade in grades:
        assert grade in QUALITY_BADGES
        assert grade in GRADE_MEANINGS
        badge = quality_badge(grade)
        assert badge == f"{QUALITY_BADGES[grade]} {grade}"


def test_badge_unknown_grade_is_visible_not_remapped() -> None:
    assert quality_badge("excellent") == "unknown(excellent)"
    assert quality_badge("") == "unknown()"


def test_badge_symbol_and_word_travel_together() -> None:
    # The badge decorates the grade word; it never replaces it.
    assert "official" in quality_badge("official")


# --- freshness ------------------------------------------------------------------


def test_freshness_current_within_two_steps() -> None:
    # Last observed 2025-01-01 (annual); as_of 2026-12-31 -> 23 months = 1.92 steps
    rows = freshness_summary([obs()], date(2026, 12, 31))
    assert rows == [
        {
            "country_iso3": "USA",
            "indicator_id": "gdp_real_growth",
            "last_observed": "2025-01-01",
            "age_months": 23,
            "age_steps": 23 / 12,
            "days_since_retrieval": (date(2026, 12, 31) - date(2026, 1, 25)).days,
            "state": "current",
        }
    ]


def test_freshness_boundary_exactly_two_steps_is_lagging() -> None:
    # as_of 2027-01-01 -> 24 months = exactly 2.0 steps -> lagging (>= rule)
    rows = freshness_summary([obs()], date(2027, 1, 1))
    assert rows[0]["age_steps"] == 2.0
    assert rows[0]["state"] == "lagging"


def test_freshness_just_below_boundary_is_current() -> None:
    # as_of 2026-12-31 -> 1.92 steps (current) vs 2027-01-01 -> 2.0 (lagging)
    assert freshness_summary([obs()], date(2026, 12, 31))[0]["state"] == "current"
    assert freshness_summary([obs()], date(2027, 1, 1))[0]["state"] == "lagging"


def test_freshness_quarterly_step_boundary() -> None:
    # Quarterly: last observed 2026-04-01; 2 steps = 6 months; as_of 2026-09-30
    # -> 5 months = 1.67 steps (current); as_of 2026-10-01 -> 6 months = 2.0 (lagging)
    quarterly = obs(period="2026-04-01", frequency="quarterly")
    assert freshness_summary([quarterly], date(2026, 9, 30))[0]["state"] == "current"
    assert freshness_summary([quarterly], date(2026, 10, 1))[0]["state"] == "lagging"


def test_freshness_no_data_when_nothing_observed() -> None:
    rows = freshness_summary(
        [obs(value=None, missing_reason="not_observed_at_period")],
        date(2027, 1, 1),
    )
    assert rows[0]["state"] == "no_data"
    assert rows[0]["last_observed"] is None
    assert rows[0]["age_steps"] is None
    assert rows[0]["days_since_retrieval"] is None


def test_freshness_uses_last_observed_period_across_rows() -> None:
    rows = freshness_summary(
        [obs(period="2023-01-01"), obs(period="2025-01-01"), obs(period="2024-01-01")],
        date(2026, 12, 31),
    )
    assert len(rows) == 1  # one (country, indicator) group
    assert rows[0]["last_observed"] == "2025-01-01"


def test_freshness_missing_rows_do_not_extend_the_observed_tail() -> None:
    rows = freshness_summary(
        [
            obs(period="2025-01-01"),
            obs(
                period="2026-01-01", value=None, missing_reason="not_observed_at_period"
            ),
        ],
        date(2026, 12, 31),
    )
    assert rows[0]["last_observed"] == "2025-01-01"


def test_freshness_groups_by_country_and_indicator_sorted() -> None:
    rows = freshness_summary(
        [
            obs(country_iso3="ZAF", indicator_id="b_ind"),
            obs(country_iso3="USA", indicator_id="a_ind"),
            obs(country_iso3="USA", indicator_id="b_ind"),
        ],
        date(2026, 12, 31),
    )
    assert [(r["country_iso3"], r["indicator_id"]) for r in rows] == [
        ("USA", "a_ind"),
        ("USA", "b_ind"),
        ("ZAF", "b_ind"),
    ]


def test_freshness_negative_age_is_reported_not_clamped() -> None:
    # as_of before the last observed period: negative age is shown (it
    # signals out-of-order as_of use, not hidden).
    rows = freshness_summary([obs(period="2025-01-01")], date(2024, 1, 1))
    assert rows[0]["age_months"] == -12
    assert rows[0]["age_steps"] == -1.0
    assert rows[0]["state"] == "current"  # below the lag threshold


def test_freshness_unknown_frequency_rejected() -> None:
    with pytest.raises(ValueError, match="unknown frequency"):
        freshness_summary([obs(frequency="weekly")], date(2026, 12, 31))


def test_freshness_states_vocabulary_is_closed() -> None:
    assert FRESHNESS_STATES == ("current", "lagging", "no_data")
    assert FRESHNESS_LAG_STEPS == 2


# --- coverage + freshness merge ----------------------------------------------------


def test_merge_freshness_joins_on_country() -> None:
    coverage = [
        {
            "country": "USA",
            "observed": 11,
            "missing": 0,
            "total_periods": 11,
            "first_observed": "2015-01-01",
            "last_observed": "2025-01-01",
        },
        {
            "country": "ZAF",
            "observed": 5,
            "missing": 6,
            "total_periods": 11,
            "first_observed": "2015-01-01",
            "last_observed": "2019-01-01",
        },
        {
            "country": "JPN",
            "observed": 0,
            "missing": 11,
            "total_periods": 11,
            "first_observed": None,
            "last_observed": None,
        },
    ]
    freshness = [
        {
            "country_iso3": "USA",
            "indicator_id": "gdp_real_growth",
            "last_observed": "2025-01-01",
            "age_months": 23,
            "age_steps": 23 / 12,
            "days_since_retrieval": 340,
            "state": "current",
        },
        {
            "country_iso3": "ZAF",
            "indicator_id": "gdp_real_growth",
            "last_observed": "2019-01-01",
            "age_months": 95,
            "age_steps": 95 / 12,
            "days_since_retrieval": 999,
            "state": "lagging",
        },
    ]
    merged = merge_freshness(coverage, freshness)
    by_country = {r["country"]: r for r in merged}
    assert by_country["USA"]["state"] == "current"
    assert by_country["USA"]["age_steps"] == 23 / 12
    assert by_country["ZAF"]["state"] == "lagging"
    assert by_country["JPN"]["state"] == "no_data"
    assert by_country["JPN"]["age_steps"] is None
    assert by_country["JPN"]["last_observed"] is None
    # coverage fields survive the merge untouched
    assert by_country["ZAF"]["observed"] == 5
    assert by_country["JPN"]["missing"] == 11


def test_merge_freshness_empty_inputs() -> None:
    assert merge_freshness([], []) == []


# --- chart captions -----------------------------------------------------------------


def test_chart_caption_normal_case() -> None:
    caption = chart_caption(
        [
            obs(),
            obs(country_iso3="ZAF", period="2024-01-01", value=0.7),
            obs(country_iso3="ZAF"),
        ]
    )
    assert "2 economies" in caption
    assert "2 periods (2024-01-01 to 2025-01-01)" in caption
    assert "evidence: real" in caption
    assert "vintage: 2026-01-25" in caption
    assert "missing" not in caption  # no missing points -> no missing claim


def test_chart_caption_singular_and_vintage_range() -> None:
    caption = chart_caption([obs(), obs(period="2024-01-01", vintage="2025-01-26")])
    assert "1 economy" in caption
    assert "vintages: 2025-01-26 to 2026-01-25" in caption


def test_chart_caption_names_missing_points() -> None:
    caption = chart_caption(
        [
            obs(),
            obs(
                period="2024-01-01", value=None, missing_reason="not_observed_at_period"
            ),
        ]
    )
    assert "1 missing point (gaps, named in tables)" in caption


def test_chart_caption_empty_input() -> None:
    assert chart_caption([]) == "No observations."


# --- hover provenance on chart traces (assembly, S15 addition) ------------------------


def test_chart_traces_carry_per_point_hover_provenance() -> None:
    traces = chart_traces(
        [
            obs(period="2024-01-01", quality_grade="preliminary"),
            obs(period="2025-01-01", quality_grade="revised", vintage="2026-06-15"),
        ],
        ["USA"],
    )
    hover = traces[0]["hover"]
    assert len(hover) == 2
    assert hover[0] == {
        "vintage": "2026-01-25",
        "evidence_label": "real",
        "quality_grade": "preliminary",
        "missing_reason": None,
    }
    assert hover[1]["vintage"] == "2026-06-15"
    assert hover[1]["quality_grade"] == "revised"


def test_chart_traces_hover_parallel_to_points() -> None:
    points = [
        obs(period="2023-01-01"),
        obs(period="2024-01-01", value=None, missing_reason="series_gap"),
        obs(period="2025-01-01"),
    ]
    traces = chart_traces(points, ["USA"])
    assert len(traces[0]["xs"]) == len(traces[0]["hover"]) == 3
    assert traces[0]["hover"][1]["missing_reason"] == "series_gap"
