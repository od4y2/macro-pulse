# MacroPulse

Global macroeconomic monitoring with statistical-blind-spot analysis:
observed data with full provenance (source, vintage, evidence label,
quality grade on every row), derived metrics with published formulas and
gates, and explicit documented limitations.

- Dashboard: `app/dashboard.py` (Streamlit)
- Query service: `src/macropulse/api/` (FastAPI) — on single-process
  hosts it runs on an in-process thread (`src/macropulse/cloud_runtime.py`)
- Database: PostgreSQL (Neon) — `DATABASE_URL`

The dashboard states observed values with citations only: no forecasts,
no causal claims, no investment advice, no rankings of merit.
