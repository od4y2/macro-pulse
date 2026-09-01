"""Dashboard view layer (unit S14).

Public surface:

- ``client.QueryServiceClient`` - typed httpx client over the S13 query
  service, with transparent pagination
- ``assembly`` - pure view-model builders (no I/O, no clock reads)
"""

from macropulse.views.assembly import (
    chart_traces,
    comparison_matrix,
    country_view_rows,
    coverage_counts,
    provenance_rows,
)
from macropulse.views.client import (
    DEFAULT_BASE_URL,
    QueryServiceClient,
    QueryServiceError,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "QueryServiceClient",
    "QueryServiceError",
    "chart_traces",
    "comparison_matrix",
    "country_view_rows",
    "coverage_counts",
    "provenance_rows",
]
