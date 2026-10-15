# Configuration

Copy `.env.example` to `.env` in the repository root. The backend also reads `backend/.env` if you put the file there.

Do not commit `.env`. It is gitignored.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | empty | Claude judge. Empty selects `MockJudge`. |
| `EVAL_TARGET_URL` | empty | OpenAI-compatible base URL, without a trailing path. Empty selects `MockCandidate`. |
| `EVAL_TARGET_MODEL` | `gpt-4o-mini` | `model` field on the chat completion request |
| `EVAL_TARGET_API_KEY` | empty | Sent as `Authorization: Bearer ...` when set |
| `EVAL_THRESHOLD` | `0.80` | Minimum mean score |
| `EVAL_REGRESSION` | `0.05` | Maximum allowed drop versus the previous same-dataset run |
| `EVAL_CONCURRENCY` | `8` | Parallel case workers |
| `DATABASE_URL` | `sqlite:///./eval_history.db` | SQLAlchemy URL. The relative SQLite path is resolved from the process working directory, so run commands from `backend/`. |

The judge model id is `judge_model` in `backend/app/config.py` (`claude-sonnet-4-5`). Override it by extending settings if you need another Claude model. It is not an environment variable today.

## Example: OpenAI as the candidate, Claude as the judge

```env
EVAL_TARGET_URL=https://api.openai.com
EVAL_TARGET_MODEL=gpt-4o-mini
EVAL_TARGET_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
EVAL_THRESHOLD=0.80
EVAL_REGRESSION=0.05
```

## Example: Ollama

```env
EVAL_TARGET_URL=http://127.0.0.1:11434
EVAL_TARGET_MODEL=llama3.2
EVAL_TARGET_API_KEY=
```

Ollama's OpenAI-compatible route is `{EVAL_TARGET_URL}/v1/chat/completions`.

## Dashboard

`frontend` is Vite. `npm run dev` serves http://localhost:5173 and proxies `/api` to http://127.0.0.1:8000.

The page shows:

- latest mean, gate result, 7-day mean
- pass rate, failed-case count, p95 latency
- dataset version in the header line
- a drift banner, and a regression banner when the latest run alerted
- mean score over time, with an 80% reference line
- category means for the latest run
- a table of failed cases with assertion, score, and rationale

`Run eval` calls `POST /api/eval/run` and reloads the page data.
