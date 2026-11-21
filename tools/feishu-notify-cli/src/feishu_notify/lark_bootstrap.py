from __future__ import annotations

import os
import subprocess
import sys
import time

import typer

from feishu_notify.lark_status import fetch_auth_status, identity_summary


def needs_lark_app_config(err: str | None) -> bool:
    if not err:
        return False
    e = err.lower()
    return any(
        x in e
        for x in (
            "not configured",
            "config init",
            "malformed config",
            "no apps",
            "invalid config",
            "not_configured",
        )
    )


def run_lark_config_init(*, json_output: bool) -> bool:
    if json_output:
        return False
    if not sys.stdin.isatty():
        return False
    typer.echo("  启动 lark-cli config init --new（会打开浏览器，请完成应用绑定）")
    env = {**os.environ, "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1"}
    proc = subprocess.run(
        ["lark-cli", "config", "init", "--new"],
        env=env,
    )
    return proc.returncode == 0


def run_user_auth_login(*, json_output: bool) -> bool:
    if json_output:
        return False
    if not sys.stdin.isatty():
        return False
    typer.echo("  启动 lark-cli auth login --domain im（请按终端提示扫码授权）")
    env = {**os.environ, "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1"}
    proc = subprocess.run(
        ["lark-cli", "auth", "login", "--domain", "im"],
        env=env,
    )
    return proc.returncode == 0


def ensure_lark_ready(*, json_output: bool, max_rounds: int = 3) -> tuple[dict | None, dict | None, str | None]:
    """
    Ensure lark-cli app config + user identity ready.
    Returns (status, info, error_message_if_failed).
    """
    last_err: str | None = None
    for _ in range(max_rounds):
        status, err = fetch_auth_status()
        last_err = err
        if needs_lark_app_config(err):
            if json_output or not sys.stdin.isatty():
                return None, None, err or "lark-cli not configured"
            if not run_lark_config_init(json_output=json_output):
                return None, None, "lark-cli config init 未完成"
            continue

        if not status:
            return None, None, err or "auth status unavailable"

        info = identity_summary(status)
        if not info.get("bot_ready"):
            return (
                status,
                info,
                "Bot 未就绪：请在飞书开发者后台启用应用与机器人能力（不要对 bot 执行 auth login）",
            )

        if info.get("user_ready"):
            return status, info, None

        if json_output or not sys.stdin.isatty():
            return status, info, "user not logged in; run lark-cli auth login --domain im"

        if not run_user_auth_login(json_output=json_output):
            typer.echo("  用户登录未完成，5 秒后重试检测…")
            time.sleep(5)
            continue

    status, err = fetch_auth_status()
    if status:
        info = identity_summary(status)
        if info.get("user_ready") and info.get("bot_ready"):
            return status, info, None
    return status, identity_summary(status) if status else None, last_err or err or "lark-cli setup incomplete"