"""Structured JSONL logging for the refresh layer (unit S17).

Operational logs are records, not analysis artifacts: each line is one
JSON object with ``ts`` (UTC ISO-8601), ``level``, ``event``, and the
event's fields. The same events that reach the log stream also drive the
durable ``refresh_runs`` row - the log answers "what happened in this
run, in order", the run row answers "what is the final state".

The only clock read in the ops layer lives here (and in the run-row
timestamps); analysis code stays clock-free.

Event vocabulary (see docs/OpsRunbook.md):
``run_started``, ``run_interrupted_marked``, ``run_finished``,
``series_started``, ``series_finished``, ``series_retry``,
``daemon_started``, ``daemon_sleep``, ``dry_run_plan``.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

LOGGER_NAME = "macropulse.ops"


def _json_record(level: str, event: str, fields: dict) -> str:
    record = {"ts": datetime.now(UTC).isoformat(), "level": level, "event": event}
    record.update(fields)
    return json.dumps(record, default=str)


def log_event(logger: logging.Logger, level: str, event: str, **fields) -> None:
    """Emit one structured event. Fields must be JSON-serializable
    (``default=str`` keeps errors/exceptions honest rather than crashing
    the run mid-log)."""
    getattr(logger, level)(_json_record(level, event, fields))


def setup_logging(log_file: Path | str | None = None) -> logging.Logger:
    """Configure the ops logger: JSONL lines appended to ``log_file``
    plus a human-readable stream on stderr.

    ``log_file=None`` means stderr only (useful for cron capture).
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # Re-configure cleanly if called twice (tests, daemon restarts).
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", style="%")
    )
    logger.addHandler(stream_handler)

    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, mode="a", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(file_handler)

    return logger


__all__ = ["LOGGER_NAME", "log_event", "setup_logging"]
