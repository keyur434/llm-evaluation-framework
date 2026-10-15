# Architecture

```
golden.json
    │
    ▼
Eval runner ──► candidate adapter ──► model output
    │                                      │
    │                                      ▼
    │                               assertion or judge
    │                                      │
    ▼                                      ▼
SQLite (runs + per-case results)     JSON report
    │
    ├── drift detector (7-day windows)
    ├── regression check (same dataset hash)
    ▼
FastAPI ──► React dashboard
GitHub Actions reads the CLI exit code
```

## Pieces

| Piece | Role |
| --- | --- |
| `backend/data/golden.json` | Fixed prompt / expected pairs |
| `app/eval/dataset.py` | Validates cases and hashes the set |
| `app/eval/adapters.py` | `MockCandidate` or OpenAI-compatible HTTP |
| `app/eval/assertions.py` | `exact`, `contains`, `json` |
| `app/eval/judge.py` | Claude judge, or `MockJudge` when no API key is set |
| `app/eval/runner.py` | Scores cases concurrently and writes the run |
| `app/eval/drift.py` | Compares the last 7 days with the 7 days before that |
| `app/eval/report.py` | Writes the CI JSON report |
| `app/main.py` | HTTP API |
| `frontend/` | Score history, category means, failed cases |

## Candidate adapters

`MockCandidate` returns a canned answer per case id. A few answers are intentionally wrong so the mean is not 1.0.

`OpenAICompatCandidate` sends `POST {EVAL_TARGET_URL}/v1/chat/completions` with temperature 0. It retries transient HTTP errors up to three times. The candidate name stored on the run is `openai_compat`.

The runner picks the HTTP adapter when `EVAL_TARGET_URL` is set. Otherwise it uses the mock.

## Judge

The runner calls the judge only when a case assertion is `judge`. Deterministic cases never spend a judge call.

`ClaudeJudge` uses the Anthropic Messages API. The model id is `judge_model` in settings (default `claude-sonnet-4-5`). Candidate text is wrapped in `<untrusted_output>` so the judge treats it as data.

`MockJudge` is a deterministic heuristic. Refusal cases look for refusal language versus compliance. Open-ended cases use token coverage and length limits. It exists so CI stays free and repeatable.

## Storage

SQLite via SQLAlchemy. Default file: `backend/eval_history.db`.

`eval_runs` stores one row per execution: timestamps, candidate, judge, mean score, pass flag, git SHA, dataset version, pass rate, failure counts, regression delta, drift flag, p95 latency, and the standard error of the mean.

`eval_results` stores one row per case: score, assertion, pass flag, rationale, actual output, latency, error text, and rubric JSON.

Startup adds missing columns on an existing SQLite file so older databases keep working.

The API seeds 14 days of synthetic runs when the database has no `seed*` git SHA. Those rows exist so the chart is not empty. Drift and regression ignore them as comparison baselines (`git_sha` like `seed%`).

## Concurrency

Cases are scored in a thread pool. `EVAL_CONCURRENCY` defaults to 8. Results are written on the main thread after all cases finish, in dataset order.
