from __future__ import annotations

import json
import re

from app.eval.judge import JudgeVerdict

CASE_PASS_SCORE = 0.8


def _norm(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _extract_json(text: str) -> object:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def run_assertion(kind: str, expected: str, actual: str) -> JudgeVerdict:
    if kind == "exact":
        ok = _norm(expected) == _norm(actual)
        return JudgeVerdict(1.0 if ok else 0.0, "exact match" if ok else "exact mismatch")
    if kind == "contains":
        ok = _norm(expected) in _norm(actual)
        return JudgeVerdict(1.0 if ok else 0.0, "contains expected" if ok else "missing expected text")
    if kind == "json":
        try:
            ok = _extract_json(expected) == _extract_json(actual)
        except (json.JSONDecodeError, TypeError, ValueError):
            return JudgeVerdict(0.0, "invalid JSON")
        return JudgeVerdict(1.0 if ok else 0.0, "JSON equal" if ok else "JSON mismatch")
    raise ValueError(f"not a deterministic assertion: {kind}")


def case_passed(assertion: str, score: float) -> bool:
    if assertion in {"exact", "contains", "json"}:
        return score >= 1.0
    return score >= CASE_PASS_SCORE
