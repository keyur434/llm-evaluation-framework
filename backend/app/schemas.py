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
    assertion: str = ""
    passed: bool = False
    latency_ms: Optional[float] = None
    error: str = ""
    rubric_json: str = ""


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
    dataset_version: str = ""
    pass_rate: Optional[float] = None
    n_cases: Optional[int] = None
    n_failed: Optional[int] = None
    critical_failed: int = 0
    regression_delta: Optional[float] = None
    regression_alert: bool = False
    p95_latency_ms: Optional[float] = None
    score_stderr: Optional[float] = None


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
    pass_rate: Optional[float] = None
    n_failed: Optional[int] = None
    critical_failed: int = 0
    regression_delta: Optional[float] = None
    regression_alert: bool = False
    dataset_version: str = ""
    p95_latency_ms: Optional[float] = None
    score_stderr: Optional[float] = None


class RunTriggerOut(BaseModel):
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
    regression_alert: bool
    dataset_version: str
