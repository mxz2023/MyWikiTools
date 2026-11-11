from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .policy import Policy, validate_policy


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"policies": {}, "checks": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("policies", {}), dict):
        raise ValueError("invalid state file")
    data.setdefault("policies", {})
    data.setdefault("checks", {})
    for city, payload in list(data["policies"].items()):
        policy = validate_policy(payload)
        if policy.city != city:
            raise ValueError(f"policy key does not match city: {city}")
    data.setdefault("upcoming_policies", {})
    for city, payload in list(data["upcoming_policies"].items()):
        policy = validate_policy(payload)
        if policy.city != city:
            raise ValueError(f"upcoming policy key does not match city: {city}")
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def get_policy(state: dict, city: str, on_date=None) -> Policy | None:
    candidates = []
    for section in ("policies", "upcoming_policies"):
        payload = state.get(section, {}).get(city)
        if payload:
            candidate = validate_policy(payload)
            if on_date is None or candidate.is_valid_on(on_date):
                candidates.append(candidate)
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.valid_from)


def get_schedule_policy(state: dict, city: str) -> Policy | None:
    """周期发现以最近一份已知（含待生效）政策的失效日为锚点。"""
    return get_policy(state, city)
