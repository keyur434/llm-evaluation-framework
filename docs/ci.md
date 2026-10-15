# CI

Workflow: `.github/workflows/eval.yml`.

It runs on every push and pull request.

1. Install `backend/requirements.txt` on Python 3.12.
2. `pytest -q` from `backend/`. Tests use an in-memory database and never call a live model.
3. `python -m app.cli run --fail-under 0.80 --report reports/eval-report.json`.
4. Upload `backend/reports/eval-report.json` as the `eval-report` artifact, including when the gate fails.

The job fails when pytest fails or the CLI exits 1.

## Default versus real models

The workflow does not require secrets. Empty `EVAL_TARGET_URL` and `ANTHROPIC_API_KEY` select `MockCandidate` and `MockJudge`.

To score a real endpoint, add repository secrets:

| Secret | Maps to |
| --- | --- |
| `ANTHROPIC_API_KEY` | Claude judge |
| `EVAL_TARGET_URL` | OpenAI-compatible base URL |
| `EVAL_TARGET_MODEL` | Candidate model name |
| `EVAL_TARGET_API_KEY` | Candidate bearer token |

Unset secrets expand to empty strings, which keeps the mock path.

CI uses `DATABASE_URL=sqlite:///./ci_eval_history.db`, a fresh file on the runner. The first run on that file has no regression baseline. Later jobs do not reuse the file unless you add a cache. The absolute 0.80 gate and the critical-case gate still apply on every job.

## Reading a failure

Open the failed job log for the `FAIL:` lines, then download the `eval-report` artifact. `failures` lists the cases that missed their assertion. A `critical_failed` value above zero means a refusal (or another critical case) missed. A `regression_alert` means the mean fell by at least 0.05 against the previous run of the same dataset version in that database.

## Local equivalent

```bash
cd backend
pytest -q
python -m app.cli run --fail-under 0.80 --report reports/eval-report.json
```
