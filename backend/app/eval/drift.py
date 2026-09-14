from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EvalRun

DROP_THRESHOLD = 0.10  # 10% relative drop


@dataclass
class DriftStatus:
    current_7d_mean: float | None
    previous_7d_mean: float | None
    relative_drop: float | None
    alert: bool
    message: str


def _mean(scores: list[float]) -> float | None:
    if not scores:
        return None
    return sum(scores) / len(scores)


def compute_drift(db: Session, now: datetime | None = None) -> DriftStatus:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    current_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)

    current_rows = db.scalars(
        select(EvalRun).where(
            EvalRun.finished_at.is_not(None),
            EvalRun.mean_score.is_not(None),
            EvalRun.finished_at >= current_start,
            EvalRun.finished_at <= now,
        )
    ).all()
    previous_rows = db.scalars(
        select(EvalRun).where(
            EvalRun.finished_at.is_not(None),
            EvalRun.mean_score.is_not(None),
            EvalRun.finished_at >= previous_start,
            EvalRun.finished_at < current_start,
        )
    ).all()

    current_mean = _mean([r.mean_score for r in current_rows if r.mean_score is not None])
    previous_mean = _mean([r.mean_score for r in previous_rows if r.mean_score is not None])

    if current_mean is None or previous_mean is None or previous_mean == 0:
        return DriftStatus(
            current_7d_mean=current_mean,
            previous_7d_mean=previous_mean,
            relative_drop=None,
            alert=False,
            message="Insufficient history for drift detection.",
        )

    relative_drop = (previous_mean - current_mean) / previous_mean
    alert = relative_drop >= DROP_THRESHOLD
    if alert:
        msg = (
            f"Drift alert: 7-day mean {current_mean:.3f} is "
            f"{relative_drop * 100:.1f}% below prior 7-day mean {previous_mean:.3f}."
        )
    else:
        msg = (
            f"No drift: current {current_mean:.3f} vs prior {previous_mean:.3f} "
            f"(drop {relative_drop * 100:.1f}%)."
        )
    return DriftStatus(
        current_7d_mean=current_mean,
        previous_7d_mean=previous_mean,
        relative_drop=relative_drop,
        alert=alert,
        message=msg,
    )
