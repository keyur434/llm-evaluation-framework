from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.eval.adapters import CandidateAdapter, get_candidate, load_golden
from app.eval.drift import compute_drift
from app.eval.judge import Judge, get_judge
from app.models import EvalResult, EvalRun


@dataclass
class RunSummary:
    run_id: int
    mean_score: float
    passed: bool
    drift_alert: bool
    n_cases: int
    candidate: str
    judge: str


def run_eval(
    db: Session,
    *,
    candidate: CandidateAdapter | None = None,
    judge: Judge | None = None,
    golden_path: Path | None = None,
    threshold: float | None = None,
    git_sha: str | None = None,
) -> RunSummary:
    settings = get_settings()
    threshold = settings.eval_threshold if threshold is None else threshold
    candidate = candidate or get_candidate()
    judge = judge or get_judge()
    cases = load_golden(golden_path)
    sha = git_sha or os.environ.get("GITHUB_SHA") or os.environ.get("GIT_SHA")

    run = EvalRun(
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        candidate=candidate.name,
        judge=judge.name,
        git_sha=sha,
        drift_alert=False,
    )
    db.add(run)
    db.flush()

    scores: list[float] = []
    for case in cases:
        actual = candidate.generate(case["prompt"], case["id"])
        verdict = judge.score(
            case["prompt"],
            case["expected"],
            actual,
            case["category"],
        )
        scores.append(verdict.score)
        db.add(
            EvalResult(
                run_id=run.id,
                case_id=case["id"],
                category=case["category"],
                score=verdict.score,
                rationale=verdict.rationale,
                actual_output=actual,
            )
        )

    mean_score = sum(scores) / len(scores) if scores else 0.0
    run.mean_score = mean_score
    run.passed = mean_score >= threshold
    run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)

    drift = compute_drift(db, now=run.finished_at)
    # Include this run's score in current window by recomputing after flush
    db.flush()
    drift = compute_drift(db, now=run.finished_at)
    run.drift_alert = drift.alert

    db.commit()
    db.refresh(run)

    return RunSummary(
        run_id=run.id,
        mean_score=mean_score,
        passed=bool(run.passed),
        drift_alert=bool(run.drift_alert),
        n_cases=len(scores),
        candidate=candidate.name,
        judge=judge.name,
    )
