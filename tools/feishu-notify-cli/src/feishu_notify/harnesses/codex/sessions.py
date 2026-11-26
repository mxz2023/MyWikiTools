from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feishu_notify.constants import CONFIG_DIR

STORE_FILE = CONFIG_DIR / "codex_sessions.json"


def _load(path: Path | None = None) -> dict[str, Any]:
    p = path or STORE_FILE
    if not p.is_file():
        return {"sessions": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"sessions": {}}
    if not isinstance(data.get("sessions"), dict):
        data["sessions"] = {}
    return data


def _save(data: dict[str, Any], path: Path | None = None) -> None:
    p = path or STORE_FILE
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def session_key(chat_id: str | None, *, fallback: str = "feishu-dm-self") -> str:
    if isinstance(chat_id, str) and chat_id.strip():
        return chat_id.strip()
    return fallback


def get_thread_id(key: str, *, store_path: Path | None = None) -> str | None:
    row = (_load(store_path).get("sessions") or {}).get(key)
    if not isinstance(row, dict):
        return None
    tid = row.get("thread_id")
    return str(tid).strip() if isinstance(tid, str) and tid.strip() else None


def put_thread_id(
    key: str,
    thread_id: str,
    *,
    thread_name: str | None = None,
    store_path: Path | None = None,
) -> None:
    data = _load(store_path)
    sessions = data.setdefault("sessions", {})
    sessions[key] = {
        "thread_id": thread_id,
        "thread_name": thread_name or sessions.get(key, {}).get("thread_name") or "Feishu Bot",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(data, store_path)


def clear_thread(key: str, *, store_path: Path | None = None) -> bool:
    data = _load(store_path)
    sessions = data.get("sessions") or {}
    if key not in sessions:
        return False
    del sessions[key]
    data["sessions"] = sessions
    _save(data, store_path)
    return True


def list_sessions(*, store_path: Path | None = None) -> list[dict[str, Any]]:
    raw = (_load(store_path).get("sessions") or {}).items()
    out: list[dict[str, Any]] = []
    for key, row in raw:
        if isinstance(row, dict):
            out.append({"chat_id": key, **row})
    return sorted(out, key=lambda r: str(r.get("updated_at") or ""), reverse=True)