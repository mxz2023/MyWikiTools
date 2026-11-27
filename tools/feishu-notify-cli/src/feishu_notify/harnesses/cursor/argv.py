from __future__ import annotations

from pathlib import Path
from typing import Any

from feishu_notify.harnesses.cursor.sessions import get_session_id, session_key
from feishu_notify.harnesses.cursor.turn import build_cursor_argv as _build_argv


def build_cursor_argv(
    *,
    prompt: str,
    workspace: Path,
    cfg: dict[str, Any] | None = None,
    chat_id: str | None = None,
) -> list[str]:
    cfg = cfg or {}
    sid = get_session_id(session_key(chat_id))
    return _build_argv(
        prompt=prompt,
        workspace=workspace,
        session_id=sid,
        cfg=cfg,
    )