from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python -m app.cli` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.eval.report import write_report
from app.eval.runner import run_eval
from app.models import EvalResult, EvalRun
from app.seed import seed_history


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LLM golden-dataset evaluation")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Fail exit code if mean score is below this (default: EVAL_THRESHOLD)",
    )
    parser.add_argument(
        "--report",
        default="reports/eval-report.json",
        help="JSON report path (relative to backend/)",
    )
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.error(f"unknown command {args.command}")

    init_db()
    settings = get_settings()
    threshold = args.fail_under if args.fail_under is not None else settings.eval_threshold

    db = SessionLocal()
    try:
        has_seed = db.scalar(
            select(EvalRun.id).where(EvalRun.git_sha.like("seed%")).limit(1)
        )
        if has_seed is None:
            seed_history(db)
        summary = run_eval(db, threshold=threshold)
        rows = db.scalars(select(EvalResult).where(EvalResult.run_id == summary.run_id)).all()
        failures = [
            {
                "case_id": row.case_id,
                "category": row.category,
                "assertion": row.assertion,
                "score": row.score,
                "rationale": row.rationale,
            }
            for row in rows
            if not row.passed
        ]
    finally:
        db.close()

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = Path(__file__).resolve().parent.parent / report_path
    write_report(
        report_path,
        {
            "run_id": summary.run_id,
            "dataset_version": summary.dataset_version,
            "mean_score": summary.mean_score,
            "pass_rate": summary.pass_rate,
            "passed": summary.passed,
            "threshold": threshold,
            "n_cases": summary.n_cases,
            "n_failed": summary.n_failed,
            "critical_failed": summary.critical_failed,
            "regression_delta": summary.regression_delta,
            "regression_alert": summary.regression_alert,
            "drift_alert": summary.drift_alert,
            "score_stderr": summary.score_stderr,
            "p95_latency_ms": summary.p95_latency_ms,
            "candidate": summary.candidate,
            "judge": summary.judge,
            "failures": failures,
        },
    )

    delta = "n/a" if summary.regression_delta is None else f"{summary.regression_delta:.4f}"
    print(
        f"run_id={summary.run_id} mean={summary.mean_score:.4f} "
        f"pass_rate={summary.pass_rate:.3f} passed={summary.passed} "
        f"critical_failed={summary.critical_failed} regression_delta={delta} "
        f"drift_alert={summary.drift_alert} dataset={summary.dataset_version} "
        f"n={summary.n_cases} candidate={summary.candidate} judge={summary.judge}"
    )
    if summary.mean_score < threshold:
        print(f"FAIL: mean {summary.mean_score:.4f} < threshold {threshold:.4f}", file=sys.stderr)
    if summary.critical_failed:
        print(f"FAIL: {summary.critical_failed} critical case(s) failed", file=sys.stderr)
    if summary.regression_alert and summary.regression_delta is not None:
        print(
            f"FAIL: regression {summary.regression_delta:.4f} >= {settings.eval_regression:.4f}",
            file=sys.stderr,
        )
    if not summary.passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
