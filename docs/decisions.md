# Decisions

- Prepared starter uses Python/FastAPI and PostgreSQL in Docker.
- INIT is complete; workspace audit is the first action.
- S01 (2026-08-19): locked the balanced global ten-economy panel (USA, CHN, JPN, DEU, GBR, IND, BRA, KOR, ZAF, MEX), research questions RQ1-RQ4 (labor slack/youth, digital inclusion, payment-resilience healthcare case study, vintage transparency), seven non-claims, and the five-label evidence vocabulary. Single source of truth: `src/macropulse/scope.py`.
- S01 (2026-08-19): until the `.venv` hidden-flag defect is resolved in E01, run direct module commands as `PYTHONPATH=src python -m macropulse.smoke` (pytest unaffected via `pythonpath` ini).
