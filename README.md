# MacroPulse BigBang Project System

## Project identity
MacroPulse is a global macroeconomic monitoring and statistical-blind-spot analysis platform. It combines traceable public macroeconomic data, transparent derived metrics, structured AI briefings, and explicit methodology/limitations.

## Locked schedule
- Vibe Coding environment setup: **2 hours**, separate from core instruction.
- Core tutoring and implementation: **20 sessions x 60 minutes**.
- Software contingency: **2 hours**, used only for integration, API, deployment, or recovery work.
- Total planned envelope: **24 hours**.

## Prepared-starter route
The repository in this pack is already initialized. **Do not rerun INIT.**

1. Extract `MacroPulse_Starter_Repository.zip`.
2. Open a terminal in the extracted folder.
3. Create a baseline Git commit.
4. Paste `prompts/WORKSPACE_AUDIT.md` into the coding assistant once.
5. Execute `prompts/S01_Research_Scope_and_Claims.md` only.
6. After acceptance, update evidence and state files, commit, and stop.

## Delivery boundaries
- No fabricated macroeconomic values, release dates, citations, or test results.
- AI generates prose only from validated structured inputs.
- No investment advice, price targets, or causal claims unsupported by evidence.
- Real, synthetic, mocked, cached, and externally sourced data must be labelled separately.

## Baseline commands
```bash
cp .env.example .env
docker compose up -d db
python -m venv .venv
python -m pip install -e '.[dev]'
python -m pytest
python -m macropulse.smoke
```
