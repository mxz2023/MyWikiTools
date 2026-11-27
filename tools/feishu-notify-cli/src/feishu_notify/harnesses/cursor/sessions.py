from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from feishu_notify.constants import CONFIG_DIR

STORE_FILE = CONFIG_DIR / "cursor_sessions.json"


def session_key(chat_id: str | None) -> str:
    return (chat_id or "").strip() or "_default"


def _load() -> dict[str, Any]:
    if not STORE_FILE.is_file():
        return {}
    try:
        data = json.loads(STORE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, Any]) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STORE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_session_id(key: str) -> str | None:
    entry = _load().get(key)
    if not isinstance(entry, dict):
        return None
    sid = entry.get("session_id")
    return str(sid).strip() if isinstance(sid, str) and sid.strip() else None


def put_session_id(key: str, session_id: str, *, label: str = "Feishu Bot") -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    data = _load()
    data[key] = {"session_id": sid, "label": label}
    _save(data)


def clear_session(key: str) -> bool:
    data = _load()
    if key not in data:
        return False
    del data[key]
    _save(data)
    return True


def list_sessions() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for key, entry in sorted(_load().items()):
        if not isinstance(entry, dict):
            continue
        sid = entry.get("session_id")
        if not isinstance(sid, str):
            continue
        out.append(
            {
                "chat_key": key,
                "session_id": sid,
                "label": str(entry.get("label") or ""),
            }
        )
    return out