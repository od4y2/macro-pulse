"""Cloud runtime bootstrap for single-process hosting (Option B, C02).

Streamlit Community Cloud runs ONE process: the dashboard. The S13
query service normally runs beside it (uvicorn), but a single-process
host has no second slot - so this module starts the SAME FastAPI app,
unchanged, on an in-process daemon thread bound to 127.0.0.1:8000. The
dashboard keeps its client contract: it still speaks HTTP to the S13
schemas, served from inside its own process.

Two host-specific facts are handled here and nowhere else:

1. Secrets-TOML values land in ``st.secrets`` and NEVER in
   ``os.environ`` - but ``database_url()`` reads ``os.environ``. The
   Neon URL is bridged into the environment BEFORE the service module
   import (``create_app`` reads DATABASE_URL at import time;
   connections stay lazy). The value is never printed or logged.
2. Neon connection strings use the bare ``postgresql://`` scheme
   (libpq naming); SQLAlchemy needs the psycopg3 driver named
   explicitly, so the scheme is normalized to
   ``postgresql+psycopg://``. Query parameters (sslmode and friends)
   travel untouched.

Idempotent and dev-safe: when something is already listening on the
port (local development runs uvicorn standalone), no thread is
started - the dashboard just uses the existing service. An explicit
``DATABASE_URL`` in the environment always wins over secrets, so
local runs and tests are unaffected.
"""

from __future__ import annotations

import os
import socket
import threading
import time

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 8000
# The service binds fast (the app import never connects); this wait only
# covers thread startup, not the first query - the HTTP client has its
# own 30s timeout for Neon compute wake-ups.
BIND_TIMEOUT_SECONDS = 10.0

_BOOT_LOCK = threading.Lock()
_booted = False


def _normalize_scheme(url: str) -> str:
    """``postgresql://`` -> ``postgresql+psycopg://``; other schemes pass."""
    prefix = "postgresql://"
    if url.startswith(prefix):
        return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def _bridge_secrets() -> None:
    """Map the Neon URL from ``st.secrets`` into ``os.environ``.

    Accepts ``DATABASE_URL`` or ``NEON_DATABASE_URL`` (the ``.env.local``
    name). No-op when the environment already carries a ``DATABASE_URL``
    or when no secrets source is available (bare runs, tests).
    """
    if os.environ.get("DATABASE_URL"):
        return
    import streamlit as st

    try:
        secrets = st.secrets
    except Exception:
        return  # no secrets file configured - nothing to bridge
    for key in ("DATABASE_URL", "NEON_DATABASE_URL"):
        try:
            url = secrets[key]
        except KeyError:
            continue
        os.environ["DATABASE_URL"] = _normalize_scheme(str(url))
        return


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _start_service_thread() -> None:
    # Imported AFTER the env bridge: create_app() reads DATABASE_URL at
    # module import time (connections stay lazy until the first query).
    import uvicorn

    from macropulse.api.main import app

    config = uvicorn.Config(
        app, host=SERVICE_HOST, port=SERVICE_PORT, log_level="warning"
    )
    server = uvicorn.Server(config)
    # uvicorn skips its signal handlers on non-main threads by design,
    # which is what makes embedding it in a daemon thread safe; the
    # thread dies with the process it serves.
    threading.Thread(
        target=server.run, daemon=True, name="macropulse-query-service"
    ).start()


def boot() -> bool:
    """Bridge secrets and ensure the query service is listening.

    Safe to call on every script run (Streamlit reruns): the work
    happens once per process; later calls are a cheap socket check.
    Returns True when a service is listening on the service port.
    """
    global _booted
    with _BOOT_LOCK:
        if not _booted:
            _bridge_secrets()
            if not _port_open(SERVICE_HOST, SERVICE_PORT):
                _start_service_thread()
                deadline = time.monotonic() + BIND_TIMEOUT_SECONDS
                while time.monotonic() < deadline:
                    if _port_open(SERVICE_HOST, SERVICE_PORT):
                        break
                    time.sleep(0.05)
            # One attempt per process (reruns are a cheap socket
            # check); if nothing is listening, the sidebar health
            # panel states it - no silent retry piles.
            _booted = True
    return _port_open(SERVICE_HOST, SERVICE_PORT)
