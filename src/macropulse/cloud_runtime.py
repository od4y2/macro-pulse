"""Cloud runtime bootstrap for single-process hosting (Option B, C02).

Streamlit Community Cloud runs ONE process: the dashboard. The S13
query service normally runs beside it (uvicorn), but a single-process
host has no second slot - so this module starts the SAME FastAPI app,
unchanged, on an in-process daemon thread bound to 127.0.0.1. The
dashboard keeps its client contract: it still speaks HTTP to the S13
schemas, served from inside its own process.

Host-specific facts are handled here and nowhere else:

1. Secrets-TOML values land in ``st.secrets`` and NEVER in
   ``os.environ`` - but ``database_url()`` reads ``os.environ``, and so
   does the briefing layer's call-time ``LLMSettings.from_env()``. The
   Neon URL and the ``LLM_*`` keys are bridged into the environment
   BEFORE the service module import (``create_app`` reads DATABASE_URL
   at import time; connections stay lazy). Values are never printed or
   logged. An explicit environment variable always wins over a secret.
2. Neon connection strings use the bare ``postgresql://`` scheme
   (libpq naming); SQLAlchemy needs the psycopg3 driver named
   explicitly, so the scheme is normalized to
   ``postgresql+psycopg://``. Query parameters (sslmode and friends)
   travel untouched.
3. The host's own infrastructure may occupy the preferred port:
   Streamlit Community Cloud runs an internal proxy on port 8000 that
   answers unknown paths with HTTP 502, so "port open" does NOT mean
   "our service is there". The port is only reused after an IDENTITY
   probe (``GET /health`` must answer with this service's JSON); when
   the preferred port belongs to something else, the service binds an
   OS-assigned port instead and exports its real address through
   ``MACROPULSE_API_URL`` (which the dashboard's client reads).

Idempotent and dev-safe: when the identity probe finds the query
service already listening (local development runs uvicorn standalone),
no thread is started - the dashboard just uses the existing service.
An explicit ``DATABASE_URL`` in the environment always wins over
secrets, and an explicit ``MACROPULSE_API_URL`` always wins over the
discovered address, so local runs and tests are unaffected.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 8000  # preferred; NOT guaranteed on shared hosts (fact 3)
# The service binds fast (the app import never connects); this wait only
# covers thread startup, not the first query - the HTTP client has its
# own 30s timeout for Neon compute wake-ups.
BIND_TIMEOUT_SECONDS = 10.0
PROBE_TIMEOUT_SECONDS = 1.0
HEALTH_PATH = "/health"

_BOOT_LOCK = threading.Lock()
_booted = False
# Address and port the query service actually listens on (set by boot()).
SERVICE_URL: str | None = None
SERVICE_PORT_ACTUAL: int | None = None


def _log(message: str) -> None:
    # stderr shows up in the host's app logs; never includes secret values.
    print(f"cloud_runtime: {message}", file=sys.stderr, flush=True)


def _normalize_scheme(url: str) -> str:
    """``postgresql://`` -> ``postgresql+psycopg://``; other schemes pass."""
    prefix = "postgresql://"
    if url.startswith(prefix):
        return "postgresql+psycopg://" + url[len(prefix) :]
    return url


# LLM configuration the briefing layer reads from os.environ at call
# time (briefing/llm.py, D3): bridged from st.secrets on cloud hosts,
# where secrets never reach the environment on their own.
BRIDGED_LLM_KEYS = (
    "LLM_PROVIDER",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_API_KEY",
    "LLM_EXTRA_BODY",
    "LLM_TIMEOUT_SECONDS",
)


def _bridge_key(secrets: object, key: str) -> bool:
    """Copy one secret verbatim into ``os.environ``; report whether it landed.

    An explicit environment value always wins (local runs and tests are
    unaffected). A missing key - or no secrets file at all
    (``StreamlitSecretNotFoundError``) - is a silent skip: there is
    simply nothing to bridge. The VALUE is never logged.
    """
    if os.environ.get(key):
        return False  # env-explicit wins
    try:
        value = secrets[key]  # type: ignore[index]
    except Exception:  # noqa: BLE001 - any failure means "not there"
        return False
    os.environ[key] = str(value)
    return True


def _bridge_secrets() -> None:
    """Map the Neon URL and the ``LLM_*`` keys from ``st.secrets``.

    The database URL accepts ``DATABASE_URL`` or ``NEON_DATABASE_URL``
    (the ``.env.local`` name) and is scheme-normalized for psycopg3. An
    environment that already carries ``DATABASE_URL`` skips only the DB
    bridge - the LLM keys are still considered (they have their own
    env-explicit guard). No-op when no secrets source is available
    (bare runs, tests).
    """
    try:
        import streamlit as st

        secrets = st.secrets
    except Exception:  # noqa: BLE001 - any failure shape means "no secrets"
        return  # no secrets file configured - nothing to bridge

    if not os.environ.get("DATABASE_URL"):
        # Accept either name; NEON_DATABASE_URL lands under DATABASE_URL.
        for source_key in ("DATABASE_URL", "NEON_DATABASE_URL"):
            try:
                url = secrets[source_key]  # type: ignore[index]
            except Exception:  # noqa: BLE001, S112 - nothing to bridge
                # KeyError for a missing key, StreamlitSecretNotFoundError
                # when no secrets file exists at all (bare local runs) -
                # either way there is nothing to bridge for this name.
                continue
            os.environ["DATABASE_URL"] = _normalize_scheme(str(url))
            break
    for key in BRIDGED_LLM_KEYS:
        _bridge_key(secrets, key)


def _service_url(port: int) -> str:
    return f"http://{SERVICE_HOST}:{port}"


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _is_our_service(port: int) -> bool:
    """Identity probe: True only when ``/health`` answers with THIS
    service's JSON (HTTP 200, object with a ``status`` key).

    Any other responder - a platform proxy answering 502, an unrelated
    app, a timeout - counts as foreign: the port is occupied, but not
    by the query service, and must not be reused.
    """
    import httpx

    try:
        # trust_env=False: an OS-level proxy (on macOS the system-wide
        # setting, e.g. a local Clash-style listener) would otherwise
        # intercept even this loopback probe and answer 502 itself,
        # making our own live service look foreign.
        response = httpx.get(
            _service_url(port) + HEALTH_PATH,
            timeout=PROBE_TIMEOUT_SECONDS,
            trust_env=False,
        )
        payload = response.json()
    except Exception:  # noqa: BLE001 - any failed probe means "not our service"
        return False
    return (
        response.status_code == 200
        and isinstance(payload, dict)
        and "status" in payload
    )


def _bind_listening_socket(port: int) -> socket.socket:
    """Pre-bind so the actual port is known before the thread starts
    (``port=0`` asks the OS to assign a free one)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((SERVICE_HOST, port))
        sock.listen(2048)  # uvicorn's default backlog
    except OSError:
        sock.close()
        raise
    return sock


def _start_service_thread(sock: socket.socket) -> None:
    # Imported AFTER the env bridge: create_app() reads DATABASE_URL at
    # module import time (connections stay lazy until the first query).
    import uvicorn

    from macropulse.api.main import app

    config = uvicorn.Config(app, host=SERVICE_HOST, log_level="warning")
    server = uvicorn.Server(config)
    # uvicorn skips its signal handlers on non-main threads by design,
    # which is what makes embedding it in a daemon thread safe; the
    # thread dies with the process it serves. The socket is pre-bound,
    # so the service is reachable on exactly the port we publish.
    threading.Thread(
        target=server.run,
        kwargs={"sockets": [sock]},
        daemon=True,
        name="macropulse-query-service",
    ).start()


def _wait_for_service(port: int) -> bool:
    deadline = time.monotonic() + BIND_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _is_our_service(port):
            return True
        time.sleep(0.05)
    return False


def _acquire_service() -> int | None:
    """Ensure the query service is listening; return its actual port."""
    if _is_our_service(SERVICE_PORT):
        # An existing query service (local development's standalone
        # uvicorn): reuse it, start no thread.
        return SERVICE_PORT
    if _port_open(SERVICE_HOST, SERVICE_PORT):
        _log(
            f"port {SERVICE_PORT} is occupied by a foreign responder "
            "(not the query service - on Streamlit Community Cloud this "
            "is the platform's internal proxy, which answers 502); "
            "binding an OS-assigned port instead"
        )
        candidates: tuple[int, ...] = (0,)
    else:
        candidates = (SERVICE_PORT, 0)
    for port in candidates:
        try:
            sock = _bind_listening_socket(port)
        except OSError:
            continue  # lost the race for the port - try the next candidate
        actual_port = sock.getsockname()[1]
        _start_service_thread(sock)
        if _wait_for_service(actual_port):
            return actual_port
        _log(
            f"service thread did not answer on port {actual_port} "
            f"within {BIND_TIMEOUT_SECONDS:.0f}s"
        )
    return None


def boot() -> bool:
    """Bridge secrets and ensure the query service is reachable.

    Safe to call on every script run (Streamlit reruns): the work
    happens once per process; later calls are a cheap socket check.
    On success ``SERVICE_URL`` records the address and
    ``MACROPULSE_API_URL`` carries it to the dashboard's client (unless
    explicitly set already). Returns True only when the query service
    itself is listening - never a foreign responder.
    """
    global _booted, SERVICE_URL, SERVICE_PORT_ACTUAL
    with _BOOT_LOCK:
        if not _booted:
            _bridge_secrets()
            SERVICE_PORT_ACTUAL = _acquire_service()
            if SERVICE_PORT_ACTUAL is not None:
                SERVICE_URL = _service_url(SERVICE_PORT_ACTUAL)
                if not os.environ.get("MACROPULSE_API_URL"):
                    os.environ["MACROPULSE_API_URL"] = SERVICE_URL
                _log(f"query service listening on {SERVICE_URL}")
            else:
                SERVICE_URL = None
                _log(
                    "query service did not come up; the dashboard will "
                    "report it unreachable"
                )
            # One attempt per process (reruns are a cheap socket
            # check); if nothing is listening, the sidebar health
            # panel states it - no silent retry piles.
            _booted = True
        return (
            SERVICE_PORT_ACTUAL is not None
            and _port_open(SERVICE_HOST, SERVICE_PORT_ACTUAL)
        )
