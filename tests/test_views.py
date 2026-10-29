"""S14 dashboard view tests: query-service client + view-model assembly.

The client is exercised against an ``httpx.MockTransport`` (no live
service, no live network); assembly functions are tested as pure data
transformations with synthetic payloads (test fixtures, never
observations).
"""

from __future__ import annotations

import json

import httpx
import pytest

from macropulse.views.assembly import (
    chart_traces,
    comparison_matrix,
    country_view_rows,
    coverage_counts,
    isolated_point_indices,
    provenance_rows,
)
from macropulse.views.client import (
    BRIEFING_TIMEOUT,
    REQUEST_TIMEOUT,
    QueryServiceClient,
    QueryServiceError,
)

# --- client -------------------------------------------------------------------


def _page(rows: list[dict], total: int) -> httpx.Response:
    response = httpx.Response(200, json=rows)
    response.headers["X-Total-Count"] = str(total)
    return response


def test_client_paginates_until_announced_total() -> None:
    served = ["a", "b", "c"]

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        limit = int(request.url.params.get("limit", "500"))
        assert limit == 2
        return _page(served[offset : offset + limit], 3)

    client = QueryServiceClient(
        "http://test", transport=httpx.MockTransport(handler), page_size=2
    )
    assert client.countries() == ["a", "b", "c"]


def test_client_single_page_when_total_fits() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert int(request.url.params.get("limit", "0")) == 500
        assert int(request.url.params.get("offset", "0")) == 0
        return _page([{"iso3": "USA"}], 1)

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    assert client.countries() == [{"iso3": "USA"}]


def test_client_stops_on_empty_page_without_total_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        response = httpx.Response(200, json=[])
        # no X-Total-Count header at all
        return response

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    assert client.countries() == []


def test_client_refuses_more_rows_than_announced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _page([{"a": 1}, {"b": 2}, {"c": 3}], 2)  # 3 rows, 2 announced

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    with pytest.raises(QueryServiceError, match="more rows"):
        client.countries()


def test_client_passes_observation_filters_through() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _page([], 0)

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    client.observations(
        indicator_id="gdp_real_growth",
        country_iso3="USA",
        period_start="2020-01-01",
        period_end="2023-01-01",
        vintage="2024-01-25",
        evidence_label="real",
        quality_grade="official",
        missing=True,
        latest_vintage=True,
    )
    params = captured[0].url.params
    assert params["indicator_id"] == "gdp_real_growth"
    assert params["country_iso3"] == "USA"
    assert params["period_start"] == "2020-01-01"
    assert params["period_end"] == "2023-01-01"
    assert params["vintage"] == "2024-01-25"
    assert params["evidence_label"] == "real"
    assert params["quality_grade"] == "official"
    assert params["missing"] == "true"
    assert params["latest_vintage"] == "true"


def test_client_wraps_http_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    with pytest.raises(QueryServiceError, match="HTTP 500"):
        client.health()


def test_client_wraps_transport_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    with pytest.raises(QueryServiceError, match="unreachable"):
        client.countries()


def test_client_rejects_invalid_page_size() -> None:
    with pytest.raises(ValueError, match="page_size"):
        QueryServiceClient(page_size=501)


def test_client_health_decodes_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok", "data_mode": "database"})

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    assert client.health() == {"status": "ok", "data_mode": "database"}


# --- briefing endpoints ---------------------------------------------------------


def test_client_generate_briefing_posts_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/briefing"
        assert json.loads(request.content) == {"country_iso3": "USA"}
        # Nested timeout budget: the client outwaits the service's LLM call.
        assert request.extensions["timeout"]["read"] == BRIEFING_TIMEOUT
        return httpx.Response(200, json={"id": 1, "status": "completed"})

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    assert client.generate_briefing("USA") == {"id": 1, "status": "completed"}


def test_client_generate_briefing_error_mentions_post() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    with pytest.raises(QueryServiceError, match=r"POST /briefing -> HTTP 500"):
        client.generate_briefing("USA")


def test_client_briefing_run_gets_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/briefing/7"
        return httpx.Response(200, json={"id": 7, "status": "fallback"})

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    assert client.briefing_run(7) == {"id": 7, "status": "fallback"}


def test_client_briefing_timeout_nesting_holds() -> None:
    # D11 invariant: LLM 45 s < client briefing timeout; ordinary GETs
    # keep the short default.
    from macropulse.briefing import LLM_TIMEOUT_SECONDS

    assert LLM_TIMEOUT_SECONDS < BRIEFING_TIMEOUT
    assert REQUEST_TIMEOUT < BRIEFING_TIMEOUT


# --- assembly: fixtures -------------------------------------------------------


def obs(**overrides: object) -> dict:
    """One observation record shaped like the service's ObservationOut."""
    base: dict[str, object] = {
        "indicator_id": "gdp_real_growth",
        "country_iso3": "USA",
        "period": "2023-01-01",
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
        "release_time": "2024-01-25T13:30:00Z",
        "retrieval_time": "2024-01-25T14:00:00Z",
        "vintage": "2024-01-25",
        "evidence_label": "real",
        "quality_grade": "preliminary",
        "missing_reason": None,
    }
    base.update(overrides)
    return base


# --- assembly: country view ----------------------------------------------------


def test_country_view_rows_carry_full_provenance() -> None:
    rows = country_view_rows(
        [
            obs(period="2022-01-01", value=1.9, vintage="2023-01-26"),
            obs(period="2023-01-01", value=2.5),
        ]
    )
    assert [r["period"] for r in rows] == ["2022-01-01", "2023-01-01"]
    row = rows[1]
    assert row["value"] == repr(2.5)
    assert row["unit"] == "percent_per_year"
    assert row["vintage"] == "2024-01-25"
    assert row["evidence_label"] == "real"
    assert row["quality_grade"] == "preliminary"
    assert row["source"] == "world_bank · NY.GDP.MKTP.KD.ZG"
    assert row["source_role"] == "primary"
    assert row["release_time"] == "2024-01-25T13:30:00Z"
    assert row["retrieval_time"] == "2024-01-25T14:00:00Z"
    assert row["missing_reason"] == ""


def test_country_view_rows_name_missing_values() -> None:
    rows = country_view_rows(
        [obs(period="2021-01-01", value=None, missing_reason="not_observed_at_period")]
    )
    assert rows[0]["value"] == "missing (not_observed_at_period)"
    assert rows[0]["missing_reason"] == "not_observed_at_period"


def test_country_view_rows_missing_without_reason_is_named_not_blank() -> None:
    rows = country_view_rows([obs(value=None, missing_reason=None)])
    assert rows[0]["value"] == "missing (no reason recorded)"


def test_country_view_rows_sort_by_indicator_then_period() -> None:
    rows = country_view_rows(
        [
            obs(indicator_id="z_last", period="2020-01-01"),
            obs(indicator_id="a_first", period="2022-01-01"),
            obs(indicator_id="a_first", period="2021-01-01"),
        ]
    )
    assert [(r["indicator_id"], r["period"]) for r in rows] == [
        ("a_first", "2021-01-01"),
        ("a_first", "2022-01-01"),
        ("z_last", "2020-01-01"),
    ]


def test_country_view_rows_empty_input() -> None:
    assert country_view_rows([]) == []


# --- assembly: provenance view --------------------------------------------------


def test_provenance_rows_show_vintage_chain_and_flag_latest() -> None:
    rows = provenance_rows(
        [
            obs(
                period="2023-01-01",
                value=2.5,
                vintage="2024-01-25",
                quality_grade="preliminary",
            ),
            obs(
                period="2023-01-01",
                value=2.9,
                vintage="2024-06-15",
                quality_grade="revised",
            ),
            obs(period="2022-01-01", value=1.9, vintage="2023-01-26"),
        ]
    )
    assert [(r["period"], r["vintage"]) for r in rows] == [
        ("2022-01-01", "2023-01-26"),
        ("2023-01-01", "2024-01-25"),
        ("2023-01-01", "2024-06-15"),
    ]
    latest_2023 = rows[2]
    superseded_2023 = rows[1]
    assert latest_2023["is_latest_vintage"] is True
    assert latest_2023["value"] == repr(2.9)
    assert superseded_2023["is_latest_vintage"] is False
    assert rows[0]["is_latest_vintage"] is True  # sole vintage is latest


def test_provenance_rows_empty_input() -> None:
    assert provenance_rows([]) == []


# --- assembly: comparison matrix ------------------------------------------------


def test_comparison_matrix_union_grid_and_missing_cells() -> None:
    rows = comparison_matrix(
        [
            obs(country_iso3="USA", period="2023-01-01", value=2.5),
            obs(country_iso3="USA", period="2024-01-01", value=2.8),
            obs(
                country_iso3="ZAF",
                period="2023-01-01",
                value=None,
                missing_reason="not_observed_at_period",
            ),
        ],
        ["USA", "ZAF"],
    )
    assert [r["period"] for r in rows] == ["2023-01-01", "2024-01-01"]
    assert rows[0]["USA"] == repr(2.5)
    assert rows[0]["ZAF"] == "missing (not_observed_at_period)"
    assert rows[1]["USA"] == repr(2.8)
    assert rows[1]["ZAF"] == "missing"  # no row at all for that country/period


def test_comparison_matrix_ignores_countries_outside_order() -> None:
    rows = comparison_matrix(
        [obs(country_iso3="JPN", period="2023-01-01", value=1.0)],
        ["USA"],
    )
    assert rows == [{"period": "2023-01-01", "USA": "missing"}]


def test_comparison_matrix_empty_input() -> None:
    assert comparison_matrix([], ["USA"]) == []


# --- assembly: chart traces ------------------------------------------------------


def test_chart_traces_preserve_none_for_gaps() -> None:
    traces = chart_traces(
        [
            obs(country_iso3="USA", period="2022-01-01", value=1.9),
            obs(
                country_iso3="USA",
                period="2023-01-01",
                value=None,
                missing_reason="gap",
            ),
            obs(country_iso3="USA", period="2024-01-01", value=2.8),
        ],
        ["USA"],
    )
    assert len(traces) == 1
    assert traces[0]["xs"] == ["2022-01-01", "2023-01-01", "2024-01-01"]
    assert traces[0]["ys"] == [1.9, None, 2.8]  # raw values; None -> chart gap
    assert traces[0]["unit"] == "percent_per_year"


def test_chart_traces_respect_country_order_and_skip_empty() -> None:
    traces = chart_traces(
        [
            obs(country_iso3="ZAF", period="2023-01-01", value=0.7),
            obs(country_iso3="USA", period="2023-01-01", value=2.5),
        ],
        ["USA", "ZAF", "JPN"],  # JPN has no observations -> no trace
    )
    assert [t["country"] for t in traces] == ["USA", "ZAF"]


def test_chart_traces_values_are_not_rounded() -> None:
    value = 2.93436322440155
    traces = chart_traces([obs(value=value)], ["USA"])
    assert traces[0]["ys"] == [value]


def test_chart_traces_empty_input() -> None:
    assert chart_traces([], ["USA"]) == []


# --- assembly: coverage counts ----------------------------------------------------


def test_coverage_counts_observed_and_missing_over_union_grid() -> None:
    rows = coverage_counts(
        [
            obs(country_iso3="USA", period="2022-01-01", value=1.9),
            obs(country_iso3="USA", period="2023-01-01", value=2.5),
            obs(country_iso3="USA", period="2024-01-01", value=None),  # missing row
            obs(country_iso3="ZAF", period="2023-01-01", value=0.7),
        ],
        ["USA", "ZAF", "JPN"],
    )
    by_country = {r["country"]: r for r in rows}
    assert by_country["USA"]["observed"] == 2
    assert by_country["USA"]["missing"] == 1  # union grid is 3 periods
    assert by_country["USA"]["total_periods"] == 3
    assert by_country["USA"]["first_observed"] == "2022-01-01"
    assert by_country["USA"]["last_observed"] == "2023-01-01"
    assert by_country["ZAF"]["observed"] == 1
    assert by_country["ZAF"]["missing"] == 2
    assert by_country["JPN"]["observed"] == 0
    assert by_country["JPN"]["first_observed"] is None


def test_coverage_counts_split_source_no_data_from_no_record() -> None:
    # The two missingness kinds are different facts: a NULL row the
    # source itself reported vs. a grid period with no row at all.
    rows = coverage_counts(
        [
            obs(country_iso3="USA", period="2011-01-01", value=60.0),
            obs(
                country_iso3="USA",
                period="2012-01-01",
                value=None,
                missing_reason="wb_missing_value",
            ),
            # USA has NO row for 2013-01-01; BRA puts it on the grid.
            obs(country_iso3="BRA", period="2013-01-01", value=55.0),
        ],
        ["USA", "BRA"],
    )
    by_country = {r["country"]: r for r in rows}
    usa = by_country["USA"]
    assert usa["observed"] == 1
    assert usa["source_no_data"] == 1  # 2012: row exists, value NULL
    assert usa["no_record"] == 1  # 2013: on the grid, no row at all
    assert usa["missing"] == usa["source_no_data"] + usa["no_record"] == 2
    bra = by_country["BRA"]
    assert bra["source_no_data"] == 0
    assert bra["no_record"] == 2  # 2011 and 2012 have no BRA row
    assert bra["missing"] == 2


def test_coverage_counts_empty_input() -> None:
    rows = coverage_counts([], ["USA"])
    assert rows == [
        {
            "country": "USA",
            "observed": 0,
            "missing": 0,
            "source_no_data": 0,
            "no_record": 0,
            "total_periods": 0,
            "first_observed": None,
            "last_observed": None,
        }
    ]


# --- assembly: isolated observed points (survey-wave shape) ----------------------


def test_isolated_points_all_isolated_survey_wave() -> None:
    # Findex shape: every observed year is surrounded by recorded gaps.
    xs = ["2010-01-01", "2011-01-01", "2012-01-01", "2013-01-01", "2014-01-01"]
    ys = [None, 60.0, None, None, 70.0]
    assert isolated_point_indices(xs, ys) == [1, 4]


def test_isolated_points_dense_series_has_none() -> None:
    ys = [1.0, 2.0, 3.0, 4.0]
    assert isolated_point_indices(["a", "b", "c", "d"], ys) == []


def test_isolated_points_edges_count_as_isolated() -> None:
    # A point at the series edge has only one neighbour; if that
    # neighbour is missing, no line can reach the point.
    assert isolated_point_indices(["a", "b", "c"], [1.0, None, None]) == [0]
    assert isolated_point_indices(["a", "b", "c"], [None, None, 3.0]) == [2]


def test_isolated_points_single_gap_separates_two_isolated_points() -> None:
    # connectgaps=False draws no segment across a gap, so 1.0 and 3.0
    # are BOTH unreachable by any line and both must be marked.
    assert isolated_point_indices(["a", "b", "c"], [1.0, None, 3.0]) == [0, 2]


def test_isolated_points_interior_of_observed_run_is_not_isolated() -> None:
    # Inside a run of observed points the line renders; only a point
    # cut off from every run needs a marker.
    ys = [1.0, 2.0, None, None, 5.0]
    assert isolated_point_indices(["a", "b", "c", "d", "e"], ys) == [4]


def test_isolated_points_all_missing_or_empty() -> None:
    assert isolated_point_indices(["a", "b"], [None, None]) == []
    assert isolated_point_indices([], []) == []


def test_isolated_points_single_observation() -> None:
    assert isolated_point_indices(["a"], [2.5]) == [0]


# --- full-pipeline sanity over a mocked service ------------------------------------


def test_client_assembly_pipeline_over_mock_service() -> None:
    """End to end (mock transport): fetch -> assemble -> display rows."""
    payload = [
        json.loads(json.dumps(obs(country_iso3="USA", period="2023-01-01", value=2.5)))
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return _page(payload, 1)

    client = QueryServiceClient("http://test", transport=httpx.MockTransport(handler))
    rows = country_view_rows(
        client.observations(country_iso3="USA", latest_vintage=True)
    )
    assert rows[0]["value"] == repr(2.5)
    assert rows[0]["evidence_label"] == "real"
