from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python -m app.cli` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.eval.runner import run_eval
from app.models import EvalRun
from app.seed import seed_history
from sqlalchemy import select


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LLM golden-dataset evaluation")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Fail exit code if mean score is below this (default: EVAL_THRESHOLD)",
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
    finally:
        db.close()

    print(
        f"run_id={summary.run_id} mean={summary.mean_score:.4f} "
        f"passed={summary.passed} drift_alert={summary.drift_alert} "
        f"n={summary.n_cases} candidate={summary.candidate} judge={summary.judge}"
    )
    if summary.mean_score < threshold:
        print(f"FAIL: mean {summary.mean_score:.4f} < threshold {threshold:.4f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
