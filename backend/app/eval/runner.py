from __future__ import annotations

import json
import math
import os
import statistics
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.eval.adapters import CandidateAdapter, get_candidate
from app.eval.assertions import case_passed, run_assertion
from app.eval.dataset import dataset_version, load_golden
from app.eval.drift import compute_drift
from app.eval.judge import Judge, JudgeVerdict, get_judge
from app.models import EvalResult, EvalRun


@dataclass
class CaseOutcome:
    case_id: str
    category: str
    assertion: str
    critical: bool
    score: float
    rationale: str
    actual_output: str
    passed: bool
    latency_ms: float
    error: str
    rubric: dict[str, float] | None


@dataclass
class RunSummary:
    run_id: int
    mean_score: float
    passed: bool
    drift_alert: bool
    n_cases: int
    candidate: str
    judge: str
    pass_rate: float
    n_failed: int
    critical_failed: int
    regression_delta: float | None
    regression_alert: bool
    dataset_version: str
    p95_latency_ms: float
    score_stderr: float


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(0.95 * len(ordered)) - 1))
    return ordered[index]


def _score_one(
    case: dict,
    candidate: CandidateAdapter,
    judge: Judge,
) -> CaseOutcome:
    started = perf_counter()
    try:
        actual = candidate.generate(case["prompt"], case["id"])
        if case["assertion"] == "judge":
            verdict: JudgeVerdict = judge.score(
                case["prompt"], case["expected"], actual, case["category"]
            )
        else:
            verdict = run_assertion(case["assertion"], case["expected"], actual)
        error = ""
    except Exception as exc:  # noqa: BLE001 — one bad case must not abort the suite
        actual = ""
        verdict = JudgeVerdict(0.0, "case error")
        error = str(exc)[:500]
    latency_ms = (perf_counter() - started) * 1000
    return CaseOutcome(
        case_id=case["id"],
        category=case["category"],
        assertion=case["assertion"],
        critical=bool(case["critical"]),
        score=verdict.score,
        rationale=verdict.rationale,
        actual_output=actual,
        passed=case_passed(case["assertion"], verdict.score) and not error,
        latency_ms=round(latency_ms, 2),
        error=error,
        rubric=verdict.rubric,
    )


def _previous_mean(db: Session, version: str, run_id: int) -> float | None:
    prev = db.scalar(
        select(EvalRun)
        .where(
            EvalRun.id != run_id,
            EvalRun.dataset_version == version,
            EvalRun.mean_score.is_not(None),
            or_(EvalRun.git_sha.is_(None), ~EvalRun.git_sha.like("seed%")),
        )
        .order_by(EvalRun.id.desc())
        .limit(1)
    )
    if prev is None or prev.mean_score is None:
        return None
    return float(prev.mean_score)


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
    version = dataset_version(cases)
    sha = git_sha or os.environ.get("GITHUB_SHA") or os.environ.get("GIT_SHA")
    workers = max(1, settings.eval_concurrency)

    run = EvalRun(
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        candidate=candidate.name,
        judge=judge.name,
        git_sha=sha,
        drift_alert=False,
        dataset_version=version,
    )
    db.add(run)
    db.flush()

    with ThreadPoolExecutor(max_workers=min(workers, len(cases))) as pool:
        outcomes = list(pool.map(lambda case: _score_one(case, candidate, judge), cases))

    scores = [item.score for item in outcomes]
    for item in outcomes:
        db.add(
            EvalResult(
                run_id=run.id,
                case_id=item.case_id,
                category=item.category,
                score=item.score,
                rationale=item.rationale,
                actual_output=item.actual_output,
                assertion=item.assertion,
                passed=item.passed,
                latency_ms=item.latency_ms,
                error=item.error,
                rubric_json=json.dumps(item.rubric) if item.rubric else "",
            )
        )

    mean_score = sum(scores) / len(scores) if scores else 0.0
    n_failed = sum(1 for item in outcomes if not item.passed)
    critical_failed = sum(1 for item in outcomes if item.critical and not item.passed)
    prior = _previous_mean(db, version, run.id)
    delta = None if prior is None else prior - mean_score
    regression_alert = delta is not None and delta >= settings.eval_regression
    passed = mean_score >= threshold and critical_failed == 0 and not regression_alert
    stderr = statistics.pstdev(scores) / math.sqrt(len(scores)) if len(scores) > 1 else 0.0

    run.mean_score = mean_score
    run.passed = passed
    run.pass_rate = (len(scores) - n_failed) / len(scores) if scores else 0.0
    run.n_cases = len(scores)
    run.n_failed = n_failed
    run.critical_failed = critical_failed
    run.regression_delta = delta
    run.regression_alert = regression_alert
    run.p95_latency_ms = _p95([item.latency_ms for item in outcomes])
    run.score_stderr = stderr
    run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)

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
        pass_rate=float(run.pass_rate or 0.0),
        n_failed=n_failed,
        critical_failed=critical_failed,
        regression_delta=delta,
        regression_alert=regression_alert,
        dataset_version=version,
        p95_latency_ms=float(run.p95_latency_ms or 0.0),
        score_stderr=stderr,
    )
