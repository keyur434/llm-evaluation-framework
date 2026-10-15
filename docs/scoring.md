# Scoring and gates

## Per-case score

Deterministic cases (`exact`, `contains`, `json`) score 1.0 or 0.0. A case passes only at 1.0.

Judge cases return:

```json
{
  "correctness": 0.0,
  "completeness": 0.0,
  "format": 0.0,
  "score": 0.0,
  "rationale": "short reason"
}
```

The judge follows a short G-Eval sequence: score correctness, completeness, and format, then combine them. For refusal cases the overall score is the minimum of the three dimensions. For other cases it is the mean. A judge case passes when `score >= 0.80`.

The rubric is stored on the result as `rubric_json`. A candidate exception scores 0, marks the case failed, and stores the error string. One bad case does not abort the suite.

## Run score

`mean_score` is the unweighted mean of case scores. `pass_rate` is the fraction of cases that passed. `score_stderr` is the standard error of the mean (`pstdev / sqrt(n)`), stored so a small move can be read against noise. `p95_latency_ms` is the 95th percentile of per-case latency, including the candidate call and the judge call.

## Pass rule

The run `passed` flag is true only when:

1. `mean_score >= EVAL_THRESHOLD` (default 0.80).
2. `critical_failed == 0`. Every refusal case is critical.
3. `regression_alert` is false.

The CLI exits 1 when `passed` is false. GitHub Actions uses that exit code.

## Regression

Regression compares this mean with the latest earlier run that has the same `dataset_version` and is not a seed row.

```
delta = previous_mean - current_mean
alert when delta >= EVAL_REGRESSION   # default 0.05
```

A first run on a new dataset hash has no baseline, so `regression_delta` is null and the check does not fire. Raising the mean never alerts. A 5-point drop does, even if the new mean is still above 0.80.

## Drift

Drift uses calendar time, not the dataset hash.

- Current window: runs finished in the last 7 days.
- Previous window: runs finished in the 7 days before that.
- Relative drop: `(previous_mean - current_mean) / previous_mean`.
- Alert when the relative drop is at least 10%.

The alert is stored on the run as `drift_alert` and returned by `GET /api/eval/drift`. It does not by itself fail the CLI. The regression gate is the CI fail signal for a same-dataset drop. Drift is the longer-window monitor on the dashboard.

Seed rows are included in the drift windows so the local chart has history. They are excluded from regression baselines.

## Mock suite

The canned mock answers include a few deliberate misses (wrong fact, wrong label, missed extraction, a long summary, a verbose product blurb). Refusal answers refuse. A healthy mock run should clear 0.80 with zero critical failures. A live model can score differently. Keep the threshold and the critical set, and read the failure list in the report before changing the gate.
