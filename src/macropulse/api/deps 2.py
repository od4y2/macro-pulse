"""Request-scoped database session dependency for the query service."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Iterator[Session]:
    """Yield a per-request session from the app-bound session factory.

    The factory lives on ``app.state`` (set by ``create_app``) so tests can
    bind the service to a dedicated database without patching module
    globals; each request gets its own session, closed on completion.
    """
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


# Annotated dependency marker: the canonical FastAPI style, and it keeps
# function calls out of parameter defaults (ruff B008).
DbSession = Annotated[Session, Depends(get_session)]
