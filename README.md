# LLM Evaluation Framework

Standalone eval infrastructure: golden dataset → any LLM endpoint → Claude-as-judge → SQLite history → drift alerts → CI gate → React dashboard.

## Features

- 50 prompt/expected pairs (`backend/data/golden.json`)
- Mock candidate + OpenAI-compatible HTTP adapter
- Claude judge (`ANTHROPIC_API_KEY`) with MockJudge fallback for free local/CI runs
- SQLite score history with timestamps
- Drift alert when 7-day mean drops ≥10% vs prior 7 days
- GitHub Actions fails if mean score &lt; 80%
- React dashboard: score history, category table, drift banner

## Quick start

```bash
# Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# CLI eval
python -m app.cli run --fail-under 0.80

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API at http://localhost:8000/docs.

Copy `.env.example` to `.env` and set keys as needed.

## Point at a real model

```env
EVAL_TARGET_URL=https://api.openai.com
EVAL_TARGET_MODEL=gpt-4o-mini
EVAL_TARGET_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
EVAL_THRESHOLD=0.80
```

Without these, MockCandidate + MockJudge run (zero cost, deterministic).

## CI

`.github/workflows/eval.yml` runs pytest then `python -m app.cli run --fail-under 0.80` on every push/PR. Optional secrets: `ANTHROPIC_API_KEY`, `EVAL_TARGET_URL`, `EVAL_TARGET_MODEL`, `EVAL_TARGET_API_KEY`.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/eval/run` | Trigger eval |
| GET | `/api/eval/runs` | History |
| GET | `/api/eval/runs/{id}` | Per-case scores |
| GET | `/api/eval/drift` | 7-day drift status |
| GET | `/api/eval/summary` | Latest mean / pass / threshold |

## Layout

```
backend/app/          FastAPI + eval engine
backend/data/         golden.json
frontend/             Vite + React + Recharts
.github/workflows/    eval gate
```
