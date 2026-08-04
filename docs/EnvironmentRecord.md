# Environment Record
Updated during WORKSPACE_AUDIT (2026-08-04); to be finalized in E01/E02.

## OS / host
- macOS 15.7.4 (Darwin 24.6.0, arm64).

## Toolchain (actual, measured this audit)
- Python: 3.13.14 (system `python3`).
- git: 2.39.5 (Apple Git-154).
- pip: 26.2 (inside `.venv`).
- pytest: 9.1.1.
- ruff: 0.16.1.
- fastapi: 0.141.1; starlette: 1.3.1; uvicorn: 0.52.1.
- pydantic: 2.13.4; httpx: 0.28.1.
- macropulse: 0.1.0 (editable install from `src/`).
- Docker / docker compose: NOT installed. `docker compose up -d db` could not run. E01 must resolve.

## Commands used (actual results)
- `python3 -m venv .venv` -> ok.
- `.venv/bin/python -m pip install --upgrade pip` -> pip 26.2.
- `.venv/bin/python -m pip install -e '.[dev]'` -> Success.
- `.venv/bin/python scripts/validate_structure.py` -> structure validation passed.
- `.venv/bin/python -m pytest -v` -> 4 passed in 0.55s.
- `.venv/bin/python -m macropulse.smoke` -> MacroPulse starter smoke test passed.
- `cp .env.example .env` -> no-op; `.env` already present with identical placeholders.

## Failures / fixes
- None during audit. Open gap: Docker absent (see above); deferred to E01.

## Editor / CLI
- opencode CLI (coding assistant) on macOS zsh.
