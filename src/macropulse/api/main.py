"""MacroPulse FastAPI query service (unit S13).

Exposes typed, paginated, filterable data and methodology endpoints over
the normalized database. Response shapes are the S03-pinned schemas in
``macropulse.api.schemas`` (implemented unchanged); provenance fields
travel with every value.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from macropulse.api import briefing, methodology, routes
from macropulse.api.deps import DbSession
from macropulse.api.schemas import HealthOut
from macropulse.briefing import LlmSource
from macropulse.db.base import database_url, make_engine, make_session_factory


def create_app(
    session_factory: Callable[[], Session] | None = None,
    llm_source_factory: Callable[[], LlmSource] | None = None,
) -> FastAPI:
    """Assemble the query service.

    The session factory is injectable so tests can bind the service to a
    dedicated database; production reads ``DATABASE_URL`` (engines connect
    lazily, so importing this module never opens a connection). The LLM
    prose-source factory is injectable the same way (tests pass a fake);
    when unset, ``POST /briefing`` resolves ``LLM_*`` from the environment
    at call time and falls back deterministically when absent - importing
    this module never reads LLM configuration.
    """
    if session_factory is None:
        session_factory = make_session_factory(make_engine(database_url()))
    app = FastAPI(title="MacroPulse", version="0.1.0")
    app.state.session_factory = session_factory
    app.state.llm_source_factory = llm_source_factory
    app.include_router(routes.router)
    app.include_router(methodology.router)
    app.include_router(briefing.router)

    @app.get("/health", response_model=HealthOut)
    def health(db: DbSession) -> HealthOut:
        """Truthful liveness: report the database actually backing the service.

        ``data_mode`` states where data comes from, not what it contains -
        per-row provenance (evidence label, quality grade) is the only
        honest content claim, and it travels on every observation.
        """
        try:
            db.execute(text("SELECT 1"))
        except (OSError, SQLAlchemyError):
            return HealthOut(status="degraded", data_mode="database-unreachable")
        return HealthOut(status="ok", data_mode="database")

    return app


app = create_app()
