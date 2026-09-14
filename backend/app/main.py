from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db import get_db, init_db
from app.eval.drift import compute_drift
from app.eval.runner import run_eval
from app.models import EvalRun
from app.schemas import (
    DriftOut,
    EvalRunDetailOut,
    EvalRunOut,
    RunTriggerOut,
    SummaryOut,
)
from app.seed import seed_history

app = FastAPI(title="LLM Evaluation Framework", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import EvalRun

    db = SessionLocal()
    try:
        has_seed = db.scalar(
            select(EvalRun.id).where(EvalRun.git_sha.like("seed%")).limit(1)
        )
        if has_seed is None:
            seed_history(db)
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/eval/run", response_model=RunTriggerOut)
def trigger_eval(db: Session = Depends(get_db)) -> RunTriggerOut:
    summary = run_eval(db)
    return RunTriggerOut(
        run_id=summary.run_id,
        mean_score=summary.mean_score,
        passed=summary.passed,
        drift_alert=summary.drift_alert,
        n_cases=summary.n_cases,
        candidate=summary.candidate,
        judge=summary.judge,
    )


@app.get("/api/eval/runs", response_model=list[EvalRunOut])
def list_runs(limit: int = 50, db: Session = Depends(get_db)) -> list[EvalRun]:
    rows = db.scalars(
        select(EvalRun).order_by(EvalRun.finished_at.desc()).limit(min(limit, 200))
    ).all()
    return list(rows)


@app.get("/api/eval/runs/{run_id}", response_model=EvalRunDetailOut)
def get_run(run_id: int, db: Session = Depends(get_db)) -> EvalRun:
    run = db.scalar(
        select(EvalRun)
        .options(joinedload(EvalRun.results))
        .where(EvalRun.id == run_id)
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/eval/drift", response_model=DriftOut)
def get_drift(db: Session = Depends(get_db)) -> DriftOut:
    status = compute_drift(db)
    return DriftOut(
        current_7d_mean=status.current_7d_mean,
        previous_7d_mean=status.previous_7d_mean,
        relative_drop=status.relative_drop,
        alert=status.alert,
        message=status.message,
    )


@app.get("/api/eval/summary", response_model=SummaryOut)
def get_summary(db: Session = Depends(get_db)) -> SummaryOut:
    settings = get_settings()
    latest = db.scalar(select(EvalRun).order_by(EvalRun.id.desc()).limit(1))
    if not latest:
        return SummaryOut(
            latest_run_id=None,
            mean_score=None,
            passed=None,
            threshold=settings.eval_threshold,
            drift_alert=False,
            candidate=None,
            judge=None,
        )
    return SummaryOut(
        latest_run_id=latest.id,
        mean_score=latest.mean_score,
        passed=latest.passed,
        threshold=settings.eval_threshold,
        drift_alert=latest.drift_alert,
        candidate=latest.candidate,
        judge=latest.judge,
    )
