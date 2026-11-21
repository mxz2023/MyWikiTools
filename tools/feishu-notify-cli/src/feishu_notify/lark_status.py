from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any


def lark_cli_path() -> str | None:
    return shutil.which("lark-cli")


def fetch_auth_status() -> tuple[dict[str, Any] | None, str | None]:
    if not lark_cli_path():
        return None, "lark-cli not on PATH"
    env = {**os.environ, "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1"}
    proc = subprocess.run(
        ["lark-cli", "auth", "status", "--json", "--verify"],
        capture_output=True,
        text=True,
        env=env,
    )
    raw = (proc.stdout or proc.stderr or "").strip()
    if not raw:
        return None, "auth status failed (empty response)"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, "could not parse lark-cli auth status JSON"

    if isinstance(payload, dict) and payload.get("ok") is False:
        err = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        hint = err.get("hint") or err.get("message") or "lark-cli not configured"
        return None, str(hint)

    if proc.returncode != 0:
        return None, raw

    return payload, None


def identity_summary(status: dict[str, Any]) -> dict[str, Any]:
    identities = status.get("identities") or {}
    bot = identities.get("bot") if isinstance(identities.get("bot"), dict) else {}
    user = identities.get("user") if isinstance(identities.get("user"), dict) else {}
    return {
        "app_id": status.get("appId"),
        "app_name": bot.get("appName"),
        "bot_ready": bool(bot.get("available")) and bot.get("status") == "ready",
        "bot_open_id": bot.get("openId"),
        "bot_message": bot.get("message"),
        "user_ready": bool(user.get("available")) and user.get("status") == "ready",
        "user_open_id": user.get("openId"),
        "user_name": user.get("userName"),
        "user_message": user.get("message"),
        "user_hint": user.get("hint"),
    }