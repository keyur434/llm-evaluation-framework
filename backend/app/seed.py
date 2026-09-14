from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import EvalResult, EvalRun


def seed_history(db: Session, days: int = 14) -> int:
    """Insert synthetic daily runs so the dashboard is not empty."""
    rng = random.Random(42)
    created = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for day_offset in range(days, 0, -1):
        finished = now - timedelta(days=day_offset, hours=rng.randint(0, 6))
        # Slight downward drift in older window so detector has signal room
        base = 0.88 if day_offset > 7 else 0.86
        mean = round(base + rng.uniform(-0.03, 0.03), 4)
        run = EvalRun(
            started_at=finished - timedelta(minutes=5),
            finished_at=finished,
            candidate="mock",
            judge="mock",
            mean_score=mean,
            passed=mean >= 0.80,
            git_sha=f"seed{day_offset:02d}",
            drift_alert=False,
        )
        db.add(run)
        db.flush()
        for i in range(5):
            db.add(
                EvalResult(
                    run_id=run.id,
                    case_id=f"seed-{day_offset}-{i}",
                    category="seed",
                    score=mean,
                    rationale="seeded",
                    actual_output="seed",
                )
            )
        created += 1

    db.commit()
    return created
