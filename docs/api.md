# API and CLI

Base URL in local development: `http://127.0.0.1:8000`.

Interactive schema: `http://127.0.0.1:8000/docs`.

The dashboard dev server proxies `/api` and `/health` to that host.

## Endpoints

### `GET /health`

```json
{"status": "ok"}
```

### `POST /api/eval/run`

Runs the golden set with the configured candidate and judge. Blocks until the run is stored.

```json
{
  "run_id": 17,
  "mean_score": 0.888,
  "passed": true,
  "drift_alert": false,
  "n_cases": 50,
  "candidate": "mock",
  "judge": "mock",
  "pass_rate": 0.88,
  "n_failed": 6,
  "critical_failed": 0,
  "regression_alert": false,
  "dataset_version": "17177453152670ce"
}
```

### `GET /api/eval/summary`

Latest run plus the configured threshold. Fields are null when the database has no runs.

Includes `pass_rate`, `n_failed`, `critical_failed`, `regression_delta`, `regression_alert`, `dataset_version`, `p95_latency_ms`, and `score_stderr`.

### `GET /api/eval/runs?limit=50`

Run history, newest first. `limit` is capped at 200.

### `GET /api/eval/runs/{id}`

One run plus its `results` array. Each result has `case_id`, `category`, `score`, `rationale`, `actual_output`, `assertion`, `passed`, `latency_ms`, `error`, and `rubric_json`.

Returns 404 when the id does not exist.

### `GET /api/eval/drift`

```json
{
  "current_7d_mean": 0.85,
  "previous_7d_mean": 0.86,
  "relative_drop": 0.015,
  "alert": false,
  "message": "No drift: current 0.852 vs prior 0.865 (drop 1.5%)."
}
```

`relative_drop` is null when either window has no scored runs.

## CLI

From `backend/`:

```bash
python -m app.cli run --fail-under 0.80 --report reports/eval-report.json
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--fail-under` | `EVAL_THRESHOLD` | Mean required for a pass |
| `--report` | `reports/eval-report.json` | Report path. Relative paths are under `backend/` |

The process prints one summary line and exits 0 only when the run passed. On failure, stderr names the mean, critical misses, or regression delta.

The report JSON contains the same summary plus a `failures` array (`case_id`, `category`, `assertion`, `score`, `rationale`). `reports/` is gitignored.

On an empty database the CLI inserts the 14-day seed history before the real run, matching the API startup behavior.
