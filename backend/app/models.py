from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    candidate: Mapped[str] = mapped_column(String(128), nullable=False)
    judge: Mapped[str] = mapped_column(String(128), nullable=False)
    mean_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    git_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    drift_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    pass_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    n_cases: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    n_failed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    critical_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    regression_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    regression_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    p95_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_stderr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    results: Mapped[list["EvalResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("eval_runs.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actual_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assertion: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rubric_json: Mapped[str] = mapped_column(Text, default="", nullable=False)

    run: Mapped["EvalRun"] = relationship(back_populates="results")
