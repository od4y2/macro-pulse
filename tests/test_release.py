"""DB integration tests for the S20 release sweep (gate + derive + idempotency)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from macropulse.connectors.base import FetchedPoint, FetchedSeries
from macropulse.db.models import DerivedMetric, NormalizedObservation
from macropulse.metrics.engine import latest_vintage_series
from macropulse.metrics.standardize import standardize_series
from macropulse.ops.release import release_sweep
from macropulse.pipeline.normalize import normalize_series, persist_normalized

RETRIEVAL = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def make_series(points, country_iso3="USA", system="world_bank",
                series_id="NY.GDP.MKTP.KD.ZG"):
    return FetchedSeries(
        system=system,
        series_id=series_id,
        country_iso3=country_iso3,
        evidence_label="real",
        retrieval_time=RETRIEVAL,
        points=tuple(points),
        raw_payload="[]",
    )


def store(session, seeded, points, country_iso3="USA"):
    """Persist points through the governed S06 normalize path."""
    series = make_series(points, country_iso3=country_iso3)
    records = normalize_series(series, "gdp_real_growth", frequency="annual")
    return persist_normalized(session, records, seeded.id)


def annual_points(values, start_year=2015, vintage_year=2026):
    return [
        FetchedPoint(date(start_year + i, 1, 1), v, None, date(vintage_year, 6, 1))
        for i, v in enumerate(values)
    ]


def derived_rows(session, metric_key="gdp_real_growth.robust_z5", country="USA"):
    return (
        session.query(DerivedMetric)
        .filter_by(metric_key=metric_key, country_iso3=country)
        .order_by(DerivedMetric.period)
        .all()
    )


def test_published_series_derives_and_rerun_is_idempotent(session, seeded):
    store(session, seeded, annual_points([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))

    report = release_sweep(
        session, indicator_ids=["gdp_real_growth"], country_iso3s=["USA"]
    )
    assert len(report.series) == 1
    outcome = report.series[0]
    assert outcome.published
    assert outcome.metric_key == "gdp_real_growth.robust_z5"
    # First two windows have occupancy < 3 (MIN_WINDOW_OCCUPANCY) -> the
    # computable outputs are the last 8 of 10 annual points.
    assert outcome.derived_new == 8
    assert outcome.derived_unchanged == 0
    assert outcome.derived_replaced == 0
    rows = derived_rows(session)
    assert len(rows) == 8
    assert rows[0].period == date(2017, 1, 1)
    assert rows[0].formula_ref == "robust_z"
    assert rows[0].inputs["observation_ids"]

    # Re-run: identical inputs -> nothing written, nothing duplicated.
    rerun = release_sweep(
        session, indicator_ids=["gdp_real_growth"], country_iso3s=["USA"]
    )
    assert rerun.series[0].derived_new == 0
    assert rerun.series[0].derived_unchanged == 8
    assert rerun.series[0].derived_replaced == 0
    assert len(derived_rows(session)) == 8


def test_revised_inputs_replace_stale_derived_rows(session, seeded):
    store(session, seeded, annual_points([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
    release_sweep(session, indicator_ids=["gdp_real_growth"], country_iso3s=["USA"])
    before = {r.period: float(r.value) for r in derived_rows(session)}
    assert date(2020, 1, 1) in before

    # A later vintage revises 2020 upward (the S07 revision chain grows).
    store(session, seeded, annual_points([20], start_year=2020, vintage_year=2027))

    rerun = release_sweep(
        session, indicator_ids=["gdp_real_growth"], country_iso3s=["USA"]
    )
    outcome = rerun.series[0]
    assert outcome.derived_replaced >= 1
    assert outcome.derived_new == 0  # no brand-new periods arrived

    # The derived row for 2020 now matches a fresh computation from the
    # revised latest-vintage view - never a second row for the same point.
    entry_points = latest_vintage_series(session, "gdp_real_growth", "USA")
    from macropulse.catalog import CATALOG

    entry = next(i for i in CATALOG if i.indicator_id == "gdp_real_growth")
    fresh = standardize_series(entry_points, 5, entry.direction, entry.frequency)
    expected = {p.period: p.value for p in fresh if p.value is not None}
    after = {r.period: float(r.value) for r in derived_rows(session)}
    assert after == expected
    assert len(after) == len(before)  # same period set; no duplicates


def test_sparse_series_held_with_named_reasons(session, seeded):
    store(session, seeded, annual_points([3.1, 3.2]))

    report = release_sweep(
        session, indicator_ids=["gdp_real_growth"], country_iso3s=["USA"]
    )
    outcome = report.series[0]
    assert not outcome.published
    assert "too_few_observations" in outcome.reasons
    assert outcome.derived_new == 0
    assert derived_rows(session) == []


def test_empty_series_held_within_closed_reason_vocabulary(session, seeded):
    # ZAF is planned (catalog primary covers the whole panel) but has no
    # rows at all: the gate names the conditions, no special case needed.
    report = release_sweep(
        session,
        indicator_ids=["gdp_real_growth"],
        country_iso3s=["USA", "ZAF"],
    )
    zaf = next(s for s in report.series if s.country_iso3 == "ZAF")
    assert not zaf.published
    assert zaf.reasons == ("coverage_below_minimum", "too_few_observations")
    assert zaf.n_observed == 0
    assert zaf.coverage == 0.0
    # Report text keeps the closed vocabulary visible.
    text = report.to_text()
    assert "HOLD    gdp_real_growth/ZAF" in text
    assert "too_few_observations" in text


def test_gate_only_mode_writes_no_derived_rows(session, seeded):
    store(session, seeded, annual_points([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))

    report = release_sweep(
        session,
        derive=False,
        indicator_ids=["gdp_real_growth"],
        country_iso3s=["USA"],
    )
    outcome = report.series[0]
    assert outcome.published
    assert report.derive is False
    assert outcome.derived_new == 0
    assert derived_rows(session) == []


def test_summary_counts_published_and_held_by_reason(session, seeded):
    from macropulse.db.models import Country

    session.add(Country(iso3="BRA", name="Brazil", rationale="test"))
    session.commit()
    store(session, seeded, annual_points([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
    store(session, seeded, annual_points([2.0, 2.1]), country_iso3="BRA")

    report = release_sweep(
        session, indicator_ids=["gdp_real_growth"], country_iso3s=["USA", "BRA"]
    )
    summary = report.summary()
    assert summary["series_total"] == 2
    assert summary["published"] == 1
    assert summary["held"] == 1
    assert summary["held_by_reason"]["too_few_observations"] == 1
    assert summary["derived_new"] == 8


def test_revisions_do_not_touch_normalized_store(session, seeded):
    store(session, seeded, annual_points([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
    release_sweep(session, indicator_ids=["gdp_real_growth"], country_iso3s=["USA"])
    store(session, seeded, annual_points([20], start_year=2020, vintage_year=2027))
    release_sweep(session, indicator_ids=["gdp_real_growth"], country_iso3s=["USA"])

    # Both vintages of the revised period survive the sweep: the release
    # layer materializes derived rows; it never rewrites observations.
    vintages = (
        session.query(NormalizedObservation)
        .filter_by(indicator_id="gdp_real_growth", country_iso3="USA")
        .filter(NormalizedObservation.period == date(2020, 1, 1))
        .all()
    )
    assert len(vintages) == 2
