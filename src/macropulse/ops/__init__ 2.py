"""Operational layer (unit S17): scheduled updates, logs, retry
boundaries, and safe failure behavior for the refresh pipeline.

Public surface:

- ``macropulse.ops.refresh`` - the orchestrator and CLI
  (``python -m macropulse.ops.refresh``); NOT re-exported here so the
  package import never conflicts with running the module as a script
- ``retry`` - bounded retry with a closed retryable-error classification
- ``runs`` - refresh_runs lifecycle and closed status/reason vocabularies
- ``scheduler`` - stdlib daily scheduler (polling convention)
- ``logging_setup`` - JSONL structured operational logging
"""

from macropulse.ops.retry import (
    DEFAULT_RETRY_POLICY,
    RetryOutcome,
    RetryPolicy,
    fetch_with_retries,
    retryable,
)
from macropulse.ops.runs import (
    FAILURE_REASONS,
    RUN_STATUSES,
    RUN_TRIGGERS,
    SERIES_STATUSES,
    classify_run_status,
    finish_run,
    mark_interrupted_runs,
    start_run,
)
from macropulse.ops.scheduler import DAILY_REFRESH_UTC, next_run_at, run_forever

__all__ = [
    "DAILY_REFRESH_UTC",
    "DEFAULT_RETRY_POLICY",
    "FAILURE_REASONS",
    "RUN_STATUSES",
    "RUN_TRIGGERS",
    "SERIES_STATUSES",
    "RetryOutcome",
    "RetryPolicy",
    "classify_run_status",
    "fetch_with_retries",
    "finish_run",
    "mark_interrupted_runs",
    "next_run_at",
    "retryable",
    "run_forever",
    "start_run",
]
