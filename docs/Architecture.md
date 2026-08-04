# Architecture and Runbook

## 1. System architecture

```text
Official APIs / approved files
        |
        v
Connector layer (FRED, World Bank, ILOSTAT; later IMF/OECD/ITU)
        |
        v
Raw observation store -> validation -> normalized observations
        |                              |
        |                              v
        +----------------------> derived metric engine
                                       |
                                       v
                              FastAPI service layer
                                       |
                  +--------------------+------------------+
                  v                                       v
          Streamlit dashboard                    Structured AI briefing
```

## 2. Baseline technology
- Python 3.12+
- FastAPI + Pydantic
- PostgreSQL in Docker; do not install PostgreSQL directly unless Docker fails
- SQLAlchemy + Alembic
- pandas/numpy/httpx
- Streamlit + Plotly
- pytest + Ruff
- APScheduler or platform cron

## 3. Data model
Core entities: `countries`, `indicators`, `source_catalog`, `release_calendar`, `raw_observations`, `normalized_observations`, `derived_metrics`, `metric_versions`, `data_quality_flags`, `briefing_runs`, and `briefing_claims`.

Every normalized observation must preserve period, release time, retrieval time, vintage/version, unit, frequency, seasonal adjustment, source, and quality grade.

## 4. Scientific and statistical rules
All formulas in student-facing and research documents must use proper display mathematics. Linear fallback notation is prohibited. Formula implementation must have deterministic tests covering normal, boundary, missing-data, and invalid-input cases.

## 5. AI boundary
The LLM may summarize validated facts, compare periods, describe cross-indicator context, and state limitations. It may not calculate source-of-truth metrics, invent causes, hide missingness, or produce financial advice.

## 6. Local runbook
```bash
cp .env.example .env
docker compose up -d db
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
alembic upgrade head
python -m pytest
uvicorn macropulse.api.main:app --reload
streamlit run app/dashboard.py
```
