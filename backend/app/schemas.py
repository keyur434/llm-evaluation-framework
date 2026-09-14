from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EvalResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    category: str
    score: float
    rationale: str
    actual_output: str


class EvalRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: Optional[datetime]
    candidate: str
    judge: str
    mean_score: Optional[float]
    passed: Optional[bool]
    git_sha: Optional[str]
    drift_alert: bool


class EvalRunDetailOut(EvalRunOut):
    results: list[EvalResultOut] = []


class DriftOut(BaseModel):
    current_7d_mean: Optional[float]
    previous_7d_mean: Optional[float]
    relative_drop: Optional[float]
    alert: bool
    message: str


class SummaryOut(BaseModel):
    latest_run_id: Optional[int]
    mean_score: Optional[float]
    passed: Optional[bool]
    threshold: float
    drift_alert: bool
    candidate: Optional[str]
    judge: Optional[str]


class RunTriggerOut(BaseModel):
    run_id: int
    mean_score: float
    passed: bool
    drift_alert: bool
    n_cases: int
    candidate: str
    judge: str
