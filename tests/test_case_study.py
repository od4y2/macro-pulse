"""Tests for the RQ3 case-study machinery (S12).

Two groups:

1. The registry itself - the four real Yunnan episodes and the verified
   China healthcare-geography records must satisfy every governance rule
   (real data is not exempt from validation).
2. The machinery on synthetic episodes/records - normal, boundary,
   missing, and invalid cases, including the observation-alignment
   arithmetic that computes RQ3's blind spot.
"""

from datetime import UTC, date, datetime

import pytest

from macropulse.case_study.china_health import (
    CASE_STUDY_COUNTRIES,
    PROVINCES,
    PROVINCIAL_METRICS,
    VERIFIED_RECORDS,
    ResourceRecord,
    exposure_report,
    recorded_regions,
    unrecorded_provinces,
)
from macropulse.case_study.episodes import (
    CHINA_STANDARD_TIME,
    EPISODE_KINDS,
    EPISODES,
    Episode,
    alignment_report,
    episodes_in_window,
    observation_alignment,
    outage_hours_by_year,
    validate_registry,
)

VINT = date(2026, 8, 29)


def synthetic_episode(**overrides):
    """A valid synthetic scheduled-maintenance episode."""
    params = {
        "episode_id": "test-episode",
        "country_iso3": "CHN",
        "region": "Yunnan",
        "title": "Synthetic test episode",
        "kind": "scheduled_maintenance",
        "start": datetime(2023, 6, 1, 10, 0, tzinfo=CHINA_STANDARD_TIME),
        "end": datetime(2023, 6, 1, 12, 0, tzinfo=CHINA_STANDARD_TIME),
        "payment_system": "test platform",
        "healthcare_scope": "test scope",
        "cause": "test cause",
        "source_name": "Test Bureau",
        "source_title": "测试公告",
        "source_url": "https://example.gov.cn/notice/1",
        "published": date(2023, 5, 30),
    }
    params.update(overrides)
    return Episode(**params)


def synthetic_record(**overrides):
    params = {
        "region": "Yunnan",
        "metric": "beds",
        "value": 1000.0,
        "year": 2023,
        "source_name": "Test Bureau",
        "source_title": "测试公报",
        "source_url": "https://example.gov.cn/report/1",
        "published": date(2024, 8, 26),
    }
    params.update(overrides)
    return ResourceRecord(**params)


# --- the real registry -----------------------------------------------------------


def test_registry_is_valid_and_unique():
    assert validate_registry(EPISODES) == []
    assert len(EPISODES) == 4


def test_real_episodes_are_cited_external_and_scheduled():
    for episode in EPISODES:
        assert episode.evidence_label == "external"
        assert (
            episode.kind
            in EPISODE_KINDS
            == ("scheduled_maintenance", "unplanned_outage")
        )
        assert episode.kind == "scheduled_maintenance"  # all four are announced windows
        assert episode.country_iso3 == "CHN"
        assert episode.region == "Yunnan"
        assert episode.source_url.startswith("https://")
        # scheduled => announced before the window
        assert episode.published <= episode.start.date()


def test_year_end_rollover_is_48_hours():
    for episode_id in ("yn-mi-2024-rollover", "yn-mi-2025-rollover"):
        episode = next(e for e in EPISODES if e.episode_id == episode_id)
        assert episode.duration_hours == 48.0
        assert episode.start.hour == 20
        assert episode.end.hour == 20


def test_outage_hours_by_year():
    hours = outage_hours_by_year(EPISODES)
    assert hours == {2024: 48.0, 2025: 48.0, 2026: 10.0}


def test_duplicate_ids_rejected():
    two = (EPISODES[0], EPISODES[0])
    problems = validate_registry(two)
    assert problems == ["duplicate episode ids: ['yn-mi-2024-rollover']"]


# --- episode governance rules -----------------------------------------------------


@pytest.mark.parametrize("field", ["source_name", "source_title", "source_url"])
def test_missing_citation_rejected(field):
    with pytest.raises(ValueError, match="citation is mandatory"):
        synthetic_episode(**{field: ""})


def test_non_http_url_rejected():
    with pytest.raises(ValueError, match="http"):
        synthetic_episode(source_url="ftp://example.gov.cn/notice/1")


def test_end_before_start_rejected():
    with pytest.raises(ValueError, match="after start"):
        synthetic_episode(
            start=datetime(2023, 6, 1, 12, 0, tzinfo=CHINA_STANDARD_TIME),
            end=datetime(2023, 6, 1, 10, 0, tzinfo=CHINA_STANDARD_TIME),
        )


def test_unknown_kind_rejected():
    with pytest.raises(ValueError, match="not in"):
        synthetic_episode(kind="incident")


def test_scheduled_episode_announced_late_rejected():
    with pytest.raises(ValueError, match="scheduled"):
        synthetic_episode(published=date(2023, 6, 5))


def test_wrong_evidence_label_rejected():
    with pytest.raises(ValueError, match="external"):
        synthetic_episode(evidence_label="real")


def test_bad_country_code_rejected():
    with pytest.raises(ValueError, match="ISO3"):
        synthetic_episode(country_iso3="chn")


def test_naive_window_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        synthetic_episode(
            start=datetime(2023, 6, 1, 10, 0),  # noqa: DTZ001 - deliberately naive
            end=datetime(2023, 6, 1, 12, 0),  # noqa: DTZ001 - deliberately naive
        )


def test_mixed_timezone_window_rejected():
    with pytest.raises(ValueError, match="one timezone"):
        synthetic_episode(end=datetime(2023, 6, 1, 12, 0, tzinfo=UTC))


def test_unplanned_episode_may_be_published_after_the_window():
    episode = synthetic_episode(
        kind="unplanned_outage",
        published=date(2023, 6, 5),  # post-incident report
    )
    assert episode.published == date(2023, 6, 5)


# --- window selection ---------------------------------------------------------------


def test_episodes_in_window_overlaps():
    inside = episodes_in_window(
        EPISODES,
        datetime(2025, 12, 1, tzinfo=CHINA_STANDARD_TIME),
        datetime(2026, 4, 1, tzinfo=CHINA_STANDARD_TIME),
    )
    assert [e.episode_id for e in inside] == [
        "yn-mi-2025-rollover",
        "yn-mi-2026-03-maintenance",
    ]


def test_episodes_in_window_empty_when_disjoint():
    assert (
        episodes_in_window(
            EPISODES,
            datetime(2020, 1, 1, tzinfo=CHINA_STANDARD_TIME),
            datetime(2020, 12, 31, tzinfo=CHINA_STANDARD_TIME),
        )
        == []
    )


def test_window_must_be_ordered():
    with pytest.raises(ValueError, match="after start"):
        episodes_in_window(
            EPISODES,
            datetime(2026, 1, 1, tzinfo=CHINA_STANDARD_TIME),
            datetime(2025, 1, 1, tzinfo=CHINA_STANDARD_TIME),
        )


# --- observation alignment (the computed blind spot) ---------------------------------


def test_year_end_rollover_straddles_every_boundary():
    episode = next(e for e in EPISODES if e.episode_id == "yn-mi-2024-rollover")
    annual = observation_alignment(episode, "annual")
    assert annual.periods_spanned == ("2024", "2025")
    assert annual.boundary_straddled
    assert annual.duration_share_of_period == pytest.approx(
        48 / (366 * 24)
    )  # 2024 is a leap year

    monthly = observation_alignment(episode, "monthly")
    assert monthly.periods_spanned == ("2024-12", "2025-01")

    quarterly = observation_alignment(episode, "quarterly")
    assert quarterly.periods_spanned == ("2024-Q4", "2025-Q1")


def test_mid_march_window_straddles_no_catalog_boundary():
    episode = next(e for e in EPISODES if e.episode_id == "yn-mi-2026-03-maintenance")
    for frequency in ("annual", "quarterly", "monthly"):
        alignment = observation_alignment(episode, frequency)
        assert not alignment.boundary_straddled
    assert observation_alignment(episode, "annual").periods_spanned == ("2026",)


def test_share_of_period_arithmetic():
    episode = next(e for e in EPISODES if e.episode_id == "yn-mi-2026-06-maintenance")
    annual = observation_alignment(episode, "annual")
    assert annual.duration_share_of_period == pytest.approx(2 / (365 * 24))
    assert not annual.boundary_straddled


def test_year_end_rollover_unresolvable_at_every_catalog_frequency():
    episode = next(e for e in EPISODES if e.episode_id == "yn-mi-2025-rollover")
    for frequency in ("annual", "quarterly", "monthly"):
        assert not observation_alignment(episode, frequency).resolvable


def test_mid_march_resolvable_only_monthly():
    episode = next(e for e in EPISODES if e.episode_id == "yn-mi-2026-03-maintenance")
    assert observation_alignment(episode, "monthly").resolvable
    assert not observation_alignment(episode, "quarterly").resolvable
    assert not observation_alignment(episode, "annual").resolvable


def test_unknown_frequency_rejected():
    episode = EPISODES[0]
    with pytest.raises(ValueError, match="frequency"):
        observation_alignment(episode, "weekly")


def test_alignment_report_covers_all_episodes_and_frequencies():
    report = alignment_report(EPISODES)
    assert set(report) == {e.episode_id for e in EPISODES}
    assert set(report["yn-mi-2024-rollover"]) == {"monthly", "quarterly", "annual"}


# --- China healthcare geography records ----------------------------------------------


def test_verified_records_are_valid_and_cited():
    assert len(VERIFIED_RECORDS) == 8
    for record in VERIFIED_RECORDS:
        assert record.evidence_label == "external"
        assert record.source_url.startswith("http")
        assert record.metric in PROVINCIAL_METRICS
        assert record.year == 2023


def test_verified_regions():
    assert recorded_regions(VERIFIED_RECORDS) == ["Beijing", "Yunnan"]


def test_unrecorded_provinces_are_named():
    unrecorded = unrecorded_provinces(VERIFIED_RECORDS)
    assert len(unrecorded) == len(PROVINCES) - 2
    assert "Guangdong" in unrecorded
    assert "Yunnan" not in unrecorded


def test_province_vocabulary_is_31_and_unique():
    assert len(PROVINCES) == 31
    assert len(set(PROVINCES)) == 31


def test_case_study_subset_is_china_only():
    assert CASE_STUDY_COUNTRIES == ("CHN",)


@pytest.mark.parametrize("field", ["source_name", "source_title", "source_url"])
def test_record_missing_citation_rejected(field):
    with pytest.raises(ValueError, match="citation is mandatory"):
        synthetic_record(**{field: ""})


def test_record_unknown_region_rejected():
    with pytest.raises(ValueError, match="unknown region"):
        synthetic_record(region="Catalonia")


def test_national_region_allowed():
    record = synthetic_record(region="CHN")
    assert record.region == "CHN"


def test_record_unknown_metric_rejected():
    with pytest.raises(ValueError, match="metric"):
        synthetic_record(metric="doctors_per_1000")


def test_record_nonpositive_value_rejected():
    with pytest.raises(ValueError, match="positive"):
        synthetic_record(value=0)


def test_record_implausible_year_rejected():
    with pytest.raises(ValueError, match="year"):
        synthetic_record(year=1999)


def test_record_wrong_evidence_label_rejected():
    with pytest.raises(ValueError, match="external"):
        synthetic_record(evidence_label="real")


# --- exposure ---------------------------------------------------------------------------


def test_exposure_report_for_yunnan_episode():
    episode = EPISODES[0]
    report = exposure_report(episode)
    assert report.episode_id == "yn-mi-2024-rollover"
    assert report.region == "Yunnan"
    assert report.institutions == 28_765
    assert report.beds == 359_900
    # the record year is carried, never implied to be the episode year
    assert report.record_year == 2023
    assert report.record_sources


def test_exposure_report_for_unrecorded_region_is_named_missing():
    episode = synthetic_episode(region="Guangdong")
    report = exposure_report(episode)
    assert report.institutions is None
    assert report.beds is None
    assert report.record_year is None
    assert report.record_sources == ()


def test_exposure_uses_latest_verified_year():
    records = (
        synthetic_record(year=2022, value=100.0),
        synthetic_record(year=2023, value=200.0),
    )
    report = exposure_report(EPISODES[0], records)
    assert report.record_year == 2023
    assert report.beds == 200
