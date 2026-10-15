from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.config import GOLDEN_PATH

ASSERTIONS = {"exact", "contains", "json", "judge"}
REQUIRED = ("id", "category", "prompt", "expected")
JUDGE_IDS = {"if-01", "if-08"}
JSON_IDS = {"if-03"}


def default_assertion(case_id: str, category: str) -> str:
    if case_id in JSON_IDS:
        return "json"
    if category in {"summarization", "refusal"} or case_id in JUDGE_IDS:
        return "judge"
    if category == "extraction":
        return "contains"
    return "exact"


def normalize_case(raw: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in REQUIRED if not str(raw.get(key, "")).strip()]
    if missing:
        raise ValueError(f"golden case missing {missing}: {raw.get('id', '?')}")
    assertion = str(raw.get("assertion") or default_assertion(raw["id"], raw["category"]))
    if assertion not in ASSERTIONS:
        raise ValueError(f"unknown assertion {assertion!r} on {raw['id']}")
    critical = raw.get("critical")
    if critical is None:
        critical = raw["category"] == "refusal"
    return {
        "id": str(raw["id"]),
        "category": str(raw["category"]),
        "prompt": str(raw["prompt"]),
        "expected": str(raw["expected"]),
        "assertion": assertion,
        "critical": bool(critical),
    }


def load_golden(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or GOLDEN_PATH
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise ValueError("golden dataset must be a non-empty list")
    cases = [normalize_case(item) for item in data]
    ids = [c["id"] for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate golden ids: {sorted(dupes)}")
    return cases


def dataset_version(cases: list[dict[str, Any]]) -> str:
    payload = json.dumps(cases, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
