from __future__ import annotations

import fcntl
import json
from pathlib import Path
from typing import Any, Callable


def state_path() -> Path:
    p = Path.home() / ".config" / "fnotify" / "dispatched_messages.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _normalize(data: dict[str, Any]) -> dict[str, list[str]]:
    ids = data.get("message_ids")
    flight = data.get("in_flight")
    return {
        "message_ids": sorted({str(x) for x in ids if x})[-500:]
        if isinstance(ids, list)
        else [],
        "in_flight": sorted({str(x) for x in flight if x})[-100:]
        if isinstance(flight, list)
        else [],
    }


def _read_unlocked() -> dict[str, list[str]]:
    p = state_path()
    if not p.is_file():
        return {"message_ids": [], "in_flight": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"message_ids": [], "in_flight": []}
    return _normalize(data) if isinstance(data, dict) else {"message_ids": [], "in_flight": []}


def _write_unlocked(data: dict[str, list[str]]) -> None:
    p = state_path()
    p.write_text(
        json.dumps(_normalize(data), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _with_lock(mutator: Callable[[dict[str, list[str]]], dict[str, list[str]]]) -> None:
    p = state_path()
    lock_path = p.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        try:
            data = _read_unlocked()
            _write_unlocked(mutator(data))
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def load_dispatched_ids() -> set[str]:
    return set(_read_unlocked().get("message_ids") or [])


def load_in_flight_ids() -> set[str]:
    return set(_read_unlocked().get("in_flight") or [])


def is_dispatched(message_id: str) -> bool:
    return (message_id or "").strip() in load_dispatched_ids()


def is_in_flight(message_id: str) -> bool:
    return (message_id or "").strip() in load_in_flight_ids()


def mark_dispatched(message_id: str) -> None:
    mid = (message_id or "").strip()
    if not mid:
        return

    def _mut(data: dict[str, list[str]]) -> dict[str, list[str]]:
        ids = set(data.get("message_ids") or [])
        ids.add(mid)
        flight = set(data.get("in_flight") or [])
        flight.discard(mid)
        return {"message_ids": sorted(ids), "in_flight": sorted(flight)}

    _with_lock(_mut)


def mark_in_flight(message_id: str) -> None:
    mid = (message_id or "").strip()
    if not mid:
        return

    def _mut(data: dict[str, list[str]]) -> dict[str, list[str]]:
        flight = set(data.get("in_flight") or [])
        flight.add(mid)
        return {**data, "in_flight": sorted(flight)}

    _with_lock(_mut)


def clear_all_in_flight() -> None:
    """Drop stale in_flight after bridge restart (prior worker did not finish bookkeeping)."""

    def _mut(data: dict[str, list[str]]) -> dict[str, list[str]]:
        if not data.get("in_flight"):
            return data
        return {**data, "in_flight": []}

    _with_lock(_mut)


def clear_in_flight(message_id: str) -> None:
    mid = (message_id or "").strip()
    if not mid:
        return

    def _mut(data: dict[str, list[str]]) -> dict[str, list[str]]:
        flight = set(data.get("in_flight") or [])
        if mid not in flight:
            return data
        flight.discard(mid)
        return {**data, "in_flight": sorted(flight)}

    _with_lock(_mut)