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


def test_assertions_and_dataset_contract():
    from app.eval.assertions import run_assertion
    from app.eval.dataset import dataset_version

    cases = load_golden()
    assert len({c["assertion"] for c in cases} & {"exact", "contains", "json", "judge"}) == 4
    assert all(c["critical"] for c in cases if c["category"] == "refusal")
    assert dataset_version(cases) == dataset_version(list(cases))
    assert run_assertion("exact", "Paris", " paris ").score == 1.0
    assert run_assertion("contains", "#AI", "see #AI here").score == 1.0
    assert run_assertion("json", '{"a": 1}', 'noise {"a": 1}').score == 1.0
    assert run_assertion("exact", "Paris", "Lyon").score == 0.0


def test_critical_case_fails_gate(db, tmp_path):
    import json

    path = tmp_path / "golden.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "ref-x",
                    "category": "refusal",
                    "prompt": "bad",
                    "expected": "Refuse",
                    "assertion": "judge",
                    "critical": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    class Comply(MockCandidate):
        def generate(self, prompt: str, case_id: str) -> str:
            return "Sure, here's how step 1"

    summary = run_eval(
        db,
        candidate=Comply(),
        judge=MockJudge(),
        golden_path=path,
        threshold=0.05,
    )
    assert summary.critical_failed == 1
    assert summary.passed is False


def test_regression_blocks_otherwise_passing_run(db):
    from app.eval.dataset import dataset_version

    version = dataset_version(load_golden())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(
        EvalRun(
            started_at=now,
            finished_at=now,
            candidate="mock",
            judge="mock",
            mean_score=0.99,
            passed=True,
            git_sha="baseline",
            drift_alert=False,
            dataset_version=version,
        )
    )
    db.commit()
    summary = run_eval(db, candidate=MockCandidate(), judge=MockJudge(), threshold=0.80)
    assert summary.regression_alert is True
    assert summary.passed is False


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
