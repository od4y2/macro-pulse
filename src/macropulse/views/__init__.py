"""Dashboard view layer (units S14-S15).

Public surface:

- ``client.QueryServiceClient`` - typed httpx client over the S13 query
  service, with transparent pagination
- ``assembly`` - pure view-model builders (no I/O, no clock reads)
- ``labels`` - freshness states, quality badges, chart captions (S15)
"""

from macropulse.views.assembly import (
    briefing_highlights,
    chart_traces,
    comparison_matrix,
    country_view_rows,
    coverage_counts,
    isolated_point_indices,
    provenance_rows,
)
from macropulse.views.client import (
    DEFAULT_BASE_URL,
    QueryServiceClient,
    QueryServiceError,
)
from macropulse.views.labels import (
    FRESHNESS_LAG_STEPS,
    FRESHNESS_STATES,
    GRADE_MEANINGS,
    QUALITY_BADGES,
    chart_caption,
    freshness_summary,
    merge_freshness,
    missingness_note,
    quality_badge,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "FRESHNESS_LAG_STEPS",
    "FRESHNESS_STATES",
    "GRADE_MEANINGS",
    "QUALITY_BADGES",
    "QueryServiceClient",
    "QueryServiceError",
    "briefing_highlights",
    "chart_caption",
    "chart_traces",
    "comparison_matrix",
    "country_view_rows",
    "coverage_counts",
    "freshness_summary",
    "isolated_point_indices",
    "merge_freshness",
    "missingness_note",
    "provenance_rows",
    "quality_badge",
]
