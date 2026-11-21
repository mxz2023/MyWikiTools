from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from feishu_notify.config import resolve_route


class DeliveryError(RuntimeError):
    pass


def extract_message_id(result: dict[str, Any]) -> str | None:
    if not isinstance(result, dict):
        return None
    for key in ("message_id", "msg_id"):
        val = result.get(key)
        if isinstance(val, str) and val.startswith("om_"):
            return val
    data = result.get("data")
    if isinstance(data, dict):
        for key in ("message_id", "msg_id"):
            val = data.get(key)
            if isinstance(val, str) and val.startswith("om_"):
                return val
    body = result.get("body")
    if isinstance(body, dict):
        mid = extract_message_id(body)
        if mid:
            return mid
    return None


def _run_lark(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise DeliveryError(proc.stderr.strip() or proc.stdout.strip() or "lark-cli failed")
    out = proc.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw_stdout": out}


def _send_file_message(
    *,
    identity: str,
    target_args: list[str],
    path: Path,
) -> dict[str, Any]:
    cmd = [
        "lark-cli",
        "im",
        "+messages-send",
        "--as",
        identity,
        *target_args,
        "--file",
        str(path),
    ]
    return _run_lark(cmd)


def deliver(
    *,
    cfg: dict[str, Any],
    route_name: str,
    identity: str,
    rendered: dict[str, Any],
    payload: dict[str, Any],
    dry_run: bool,
    max_body_chars: int,
) -> dict[str, Any]:
    route = resolve_route(cfg, route_name)
    route_type = route.get("type", "bot_p2p")

    body_md = payload.get("body_md") or ""
    long_body_path: Path | None = None
    if isinstance(body_md, str) and len(body_md) > max_body_chars:
        if not dry_run:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".md",
                encoding="utf-8",
                delete=False,
            ) as fh:
                fh.write(body_md)
                long_body_path = Path(fh.name)

    target_args: list[str] = []
    if route_type == "bot_p2p":
        uid = route.get("user_id") or ""
        if not uid and not dry_run:
            raise DeliveryError("routes.dm_self.user_id is empty; run fnotify install")
        if not uid and dry_run:
            uid = "ou_dry_run"
        target_args = ["--user-id", uid]
    elif route_type == "user_p2p":
        uid = route.get("user_id") or ""
        if not uid:
            raise DeliveryError("route user_id is empty")
        target_args = ["--user-id", uid]
    elif route_type == "chat":
        chat_id = route.get("chat_id") or ""
        if not chat_id:
            raise DeliveryError("route chat_id is empty")
        target_args = ["--chat-id", chat_id]
    else:
        raise DeliveryError(f"unsupported route type: {route_type}")

    if rendered["format"] == "text":
        cmd = [
            "lark-cli",
            "im",
            "+messages-send",
            "--as",
            identity,
            *target_args,
            "--markdown",
            rendered["markdown"],
        ]
    else:
        content = json.dumps(rendered["card"], ensure_ascii=False)
        cmd = [
            "lark-cli",
            "im",
            "+messages-send",
            "--as",
            identity,
            *target_args,
            "--msg-type",
            "interactive",
            "--content",
            content,
        ]

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "delivered_as": identity,
            "route": route_name,
            "format_used": rendered["format"],
            "lark_command": cmd,
            "long_body_followup": bool(long_body_path),
        }

    result = _run_lark(cmd)
    message_id = extract_message_id(result)
    followup: dict[str, Any] | None = None
    if long_body_path and long_body_path.is_file():
        try:
            followup = _send_file_message(
                identity=identity, target_args=target_args, path=long_body_path
            )
        finally:
            long_body_path.unlink(missing_ok=True)
    return {
        "ok": True,
        "dry_run": False,
        "delivered_as": identity,
        "route": route_name,
        "format_used": rendered["format"],
        "message_id": message_id,
        "lark_response": result,
        "long_body_followup": followup,
    }


def deliver_patch(
    *,
    message_id: str,
    identity: str,
    rendered: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    if rendered["format"] != "card":
        raise DeliveryError("patch only supports interactive cards (use scene with card format)")
    card_json = json.dumps(rendered["card"], ensure_ascii=False)
    body = json.dumps({"content": card_json}, ensure_ascii=False)
    cmd = [
        "lark-cli",
        "im",
        "messages",
        "patch",
        "--as",
        identity,
        "--message-id",
        message_id,
        "--data",
        body,
    ]
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "delivered_as": identity,
            "message_id": message_id,
            "format_used": "card",
            "lark_command": cmd,
        }
    result = _run_lark(cmd)
    return {
        "ok": True,
        "dry_run": False,
        "delivered_as": identity,
        "message_id": message_id,
        "format_used": "card",
        "lark_response": result,
    }