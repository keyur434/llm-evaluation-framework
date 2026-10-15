# LLM Evaluation Framework

A standalone evaluation service. It runs a versioned golden dataset against an LLM endpoint, scores each case with a deterministic check or an LLM judge, stores the history, and fails CI when quality drops.

The default path uses a mock candidate and a mock judge, so local runs and GitHub Actions cost nothing. Point the same runner at an OpenAI-compatible endpoint and Claude when you want a real model.

## Quick start

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy ..\.env.example ..\.env   # Windows
# cp ../.env.example ../.env   # macOS/Linux

python -m app.cli run --fail-under 0.80
uvicorn app.main:app --reload --port 8000
```

Dashboard, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs

## Documentation

| Guide | What it covers |
| --- | --- |
| [Architecture](docs/architecture.md) | Components, data flow, storage |
| [Golden dataset](docs/dataset.md) | Case schema, assertions, versioning |
| [Scoring and gates](docs/scoring.md) | Judge rubric, pass rules, drift, regression |
| [API](docs/api.md) | HTTP endpoints and the CLI |
| [CI](docs/ci.md) | GitHub Actions gate and the JSON report |
| [Configuration](docs/configuration.md) | Environment variables |

## What a run checks

A run passes only when all three are true:

1. Mean score is at least `EVAL_THRESHOLD` (default 0.80).
2. Every critical case passes. Refusal cases are critical.
3. The mean has not dropped by `EVAL_REGRESSION` or more (default 0.05) versus the previous run on the same dataset version.

## Layout

```
backend/app/eval/     runner, assertions, judge, drift, report
backend/data/         golden.json
backend/tests/        pytest suite (no live API calls)
frontend/             Vite + React dashboard
.github/workflows/    eval gate
docs/                 this documentation
```
