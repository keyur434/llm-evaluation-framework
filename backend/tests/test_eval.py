from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.eval.adapters import MockCandidate, load_golden
from app.eval.drift import compute_drift
from app.eval.judge import MockJudge
from app.eval.runner import run_eval
from app.models import Base, EvalRun


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_golden_has_50_cases():
    cases = load_golden()
    assert len(cases) == 50
    cats = {c["category"] for c in cases}
    assert {
        "instruction_following",
        "factual",
        "summarization",
        "classification",
        "extraction",
        "refusal",
    }.issubset(cats)


def test_mock_judge_exact_match():
    j = MockJudge()
    v = j.score("q", "Paris", "Paris", "factual")
    assert v.score == 1.0


def test_mock_judge_refusal():
    j = MockJudge()
    good = j.score("bad", "Refuse", "I can't help with that.", "refusal")
    bad = j.score("bad", "Refuse", "Sure, here's how to do it step 1...", "refusal")
    assert good.score >= 0.9
    assert bad.score <= 0.2


def test_drift_alert_on_10pct_drop(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(3):
        db.add(
            EvalRun(
                started_at=now - timedelta(days=10, hours=i),
                finished_at=now - timedelta(days=10, hours=i),
                candidate="mock",
                judge="mock",
                mean_score=0.90,
                passed=True,
                drift_alert=False,
            )
        )
    for i in range(3):
        db.add(
            EvalRun(
                started_at=now - timedelta(days=2, hours=i),
                finished_at=now - timedelta(days=2, hours=i),
                candidate="mock",
                judge="mock",
                mean_score=0.70,
                passed=False,
                drift_alert=False,
            )
        )
    db.commit()
    status = compute_drift(db, now=now)
    assert status.alert is True
    assert status.relative_drop is not None
    assert status.relative_drop >= 0.10


def test_drift_no_alert_when_stable(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for day in range(1, 14):
        db.add(
            EvalRun(
                started_at=now - timedelta(days=day),
                finished_at=now - timedelta(days=day),
                candidate="mock",
                judge="mock",
                mean_score=0.85,
                passed=True,
                drift_alert=False,
            )
        )
    db.commit()
    status = compute_drift(db, now=now)
    assert status.alert is False


def test_run_eval_passes_threshold(db):
    summary = run_eval(
        db,
        candidate=MockCandidate(),
        judge=MockJudge(),
        threshold=0.80,
    )
    assert summary.n_cases == 50
    assert summary.mean_score >= 0.80
    assert summary.passed is True


def test_run_eval_fails_high_threshold(db):
    summary = run_eval(
        db,
        candidate=MockCandidate(),
        judge=MockJudge(),
        threshold=0.99,
    )
    assert summary.passed is False
    assert summary.mean_score < 0.99
