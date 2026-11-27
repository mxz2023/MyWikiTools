from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from feishu_notify.bridge_dispatch import run_dispatch
from feishu_notify.bridge_state import (
    clear_in_flight,
    is_in_flight,
    load_dispatched_ids,
    mark_dispatched,
)
from feishu_notify.config import load_config
from feishu_notify.listen_flow import dm_self_user_id

# Avoid re-running Codex on pasted automation digests during catch-up.
_MAX_CATCHUP_PROMPT_CHARS = 400


def _lark_list_messages(
    *,
    chat_id: str | None,
    user_id: str | None,
    page_size: int = 40,
) -> list[dict[str, Any]]:
    cmd = [
        "lark-cli",
        "im",
        "+chat-messages-list",
        "--page-size",
        str(page_size),
        "--order",
        "desc",
    ]
    if chat_id:
        cmd.extend(["--chat-id", chat_id])
    elif user_id:
        cmd.extend(["--user-id", user_id])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "lark-cli list failed")
    body = json.loads(proc.stdout)
    if not body.get("ok"):
        raise RuntimeError(str(body.get("error") or "list not ok"))
    data = body.get("data") or {}
    messages = data.get("messages")
    return list(messages) if isinstance(messages, list) else []


def _is_user_text(msg: dict[str, Any], user_open_id: str) -> bool:
    sender = msg.get("sender") or {}
    if sender.get("sender_type") != "user":
        return False
    if sender.get("id") != user_open_id:
        return False
    if msg.get("deleted"):
        return False
    return msg.get("msg_type") == "text"


def _is_bot_message(msg: dict[str, Any]) -> bool:
    sender = msg.get("sender") or {}
    return sender.get("sender_type") == "app"


def _is_ack_only(body: str, user_content: str) -> bool:
    """Bot placeholders that are not a final reply (catch-up should keep scanning)."""
    text = body.strip()
    if not text:
        return True
    if text == user_content:
        return True
    if text.startswith("##### 已收到\n\n"):
        rest = text.replace("##### 已收到\n\n", "", 1).strip()
        return rest == user_content.strip()
    if text.startswith("<card title=\"已收到") and "本轮推理结束" not in text:
        return True
    if text.startswith("<card title=\"Codex 工作中\">"):
        return True
    if "Codex 处理中" in text and text.startswith("<card"):
        return True
    return False


def _codex_reply_card_finished(body: str) -> bool:
    """agent.codex_reply card with conclusion (green header or footer after ---)."""
    if "已收到「" not in body:
        return False
    if any(t in body for t in ('"template": "green"', '"template":"green"', '"template": "red"', '"template":"red"')):
        return True
    if '"status": "failed"' in body or '"status":"failed"' in body:
        return True
    if "---" in body:
        tail = body.rsplit("---", 1)[-1].strip()
        return len(tail) > 80
    return False


def _codex_reply_card_in_progress(body: str) -> bool:
    """In-flight M2 card — not a final reply (catch-up may still run if not in_flight)."""
    if "已收到「" not in body:
        return False
    if _codex_reply_card_finished(body):
        return False
    return '"template": "blue"' in body or '"template":"blue"' in body


def _has_conclusion_after(
    ordered: list[dict[str, Any]],
    user_idx: int,
    *,
    user_id: str,
    user_content: str,
) -> bool:
    for msg in ordered[user_idx + 1 :]:
        if _is_user_text(msg, user_id):
            break
        if not _is_bot_message(msg):
            continue
        body = str(msg.get("content") or "")
        if _codex_reply_card_finished(body):
            return True
        if _codex_reply_card_in_progress(body):
            continue
        if _is_ack_only(body, user_content):
            continue
        return True
    return False


def pending_user_events(
    cfg: dict[str, Any],
    *,
    chat_id: str | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    user_id = dm_self_user_id(cfg)
    if not user_id:
        return []
    routes = cfg.get("routes") or {}
    dm = routes.get("dm_self") or {}
    resolved_chat = (chat_id or dm.get("chat_id") or "").strip() or None
    raw = _lark_list_messages(chat_id=resolved_chat, user_id=user_id, page_size=limit)
    if not raw:
        return []
    if not resolved_chat:
        resolved_chat = str(raw[0].get("chat_id") or "")
    chronological = list(reversed(raw))
    dispatched = load_dispatched_ids()
    pending: list[dict[str, Any]] = []
    for idx, msg in enumerate(chronological):
        if not _is_user_text(msg, user_id):
            continue
        mid = str(msg.get("message_id") or "")
        if not mid or mid in dispatched or is_in_flight(mid):
            continue
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        if len(content) > _MAX_CATCHUP_PROMPT_CHARS:
            continue
        if _has_conclusion_after(chronological, idx, user_id=user_id, user_content=content):
            mark_dispatched(mid)
            continue
        pending.append(
            {
                "type": "im.message.receive_v1",
                "event_id": f"catchup-{mid}",
                "message_id": mid,
                "chat_id": resolved_chat or str(msg.get("chat_id") or ""),
                "message_type": "text",
                "sender_id": user_id,
                "content": content,
            }
        )
    return pending


def run_catch_up(
    *,
    harness: str,
    workspace: Path,
    timeout_sec: int,
    config_path: Path | None = None,
    dry_run: bool = False,
    notify: bool = True,
) -> int:
    cfg = load_config(config_path)
    try:
        events = pending_user_events(cfg)
    except Exception as exc:
        print(f"[bridge] catch-up scan failed: {exc}", file=sys.stderr, flush=True)
        return 0
    if not events:
        print("[bridge] catch-up: 无未回复的用户消息", file=sys.stderr, flush=True)
        return 0
    for event in events:
        preview = str(event.get("content") or "")[:60]
        mid = str(event.get("message_id") or "")
        print(f"[bridge] catch-up 补跑 message_id={mid} {preview!r}", file=sys.stderr, flush=True)
        if dry_run:
            continue
        try:
            result = run_dispatch(
                "im.message.receive_v1",
                event,
                harness=harness,
                workspace=workspace,
                timeout_sec=timeout_sec,
                notify=notify,
                dry_run=False,
                config_path=config_path,
            )
        except Exception as exc:  # noqa: BLE001
            clear_in_flight(mid)
            print(f"[bridge] catch-up 异常 mid={mid}: {exc}", file=sys.stderr, flush=True)
            continue
        print(
            f"[bridge] catch-up done mid={mid} ok={result.ok} exit={result.exit_code}",
            file=sys.stderr,
            flush=True,
        )
    return len(events)