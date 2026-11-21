from __future__ import annotations

import sys
from typing import Any

import typer

from feishu_notify.checks import run_doctor
from feishu_notify.config import CONFIG_FILE, init_config, save_dm_self_user_id
from feishu_notify.lark_bootstrap import ensure_lark_ready
from feishu_notify.lark_status import lark_cli_path
from feishu_notify.pipeline import process_send

OVERVIEW = """
┌─────────────────────────────────────────────────────────────┐
│  fnotify install = 一条命令做完本机出站环境                  │
├─────────────────────────────────────────────────────────────┤
│  1) 检查 lark-cli 已安装                                     │
│  2) 若未配应用 → 引导 lark-cli config init --new（浏览器）   │
│  3) 若用户未登录 → 引导 lark-cli auth login --domain im      │
│  4) 写入 ~/.config/fnotify（你的 open_id）+ doctor + 可选测试   │
└─────────────────────────────────────────────────────────────┘
"""


def _print_step(n: int, title: str) -> None:
    typer.echo(f"\n── 步骤 {n}：{title} ──")


def _human_report(report) -> None:
    for item in report.items:
        mark = "✓" if item.ok else "✗"
        typer.echo(f"  [{mark}] {item.title}")
        typer.echo(f"      {item.detail}")
        if not item.ok and item.fix:
            typer.echo(f"      → {item.fix}")


def run_install(
    *,
    yes: bool = False,
    skip_test: bool = False,
    json_output: bool = False,
) -> dict[str, Any]:
    if not json_output:
        typer.echo(OVERVIEW.strip())

    steps_done: list[str] = []
    issues: list[str] = []

    _print_step(1, "检查 lark-cli") if not json_output else None
    if not lark_cli_path():
        body = {
            "ok": False,
            "step": 1,
            "hint": "安装 lark-cli 后重试 fnotify install",
        }
        if json_output:
            return body
        typer.echo("  未找到 lark-cli，请先安装。")
        raise typer.Exit(1)
    steps_done.append("lark_cli")

    _print_step(2, "配置 lark-cli（应用 + 用户登录）") if not json_output else None
    status, info, fail = ensure_lark_ready(json_output=json_output)
    if fail:
        body = {"ok": False, "step": 2, "error": fail, "lark": info}
        if json_output:
            return body
        typer.echo(f"  ✗ {fail}")
        raise typer.Exit(1)

    assert info is not None
    if not json_output:
        typer.echo(f"  应用: {info.get('app_name') or '—'} ({info.get('app_id')})")
        typer.echo(f"  Bot: 就绪")
        typer.echo(
            f"  用户: {info.get('user_name') or '—'} {info.get('user_open_id') or ''}"
        )
    steps_done.append("lark_bootstrap")

    user_id = (info.get("user_open_id") or "").strip()
    if not user_id.startswith("ou_"):
        body = {"ok": False, "step": 2, "error": "missing user open_id", "lark": info}
        if json_output:
            return body
        typer.echo("  未解析到 user open_id")
        raise typer.Exit(1)

    _print_step(3, "写入 fnotify 配置") if not json_output else None
    init_config()
    save_dm_self_user_id(user_id)
    steps_done.append("fnotify_config")
    if not json_output:
        typer.echo(f"  已保存 routes.dm_self.user_id = {user_id}")
        typer.echo(f"  配置文件: {CONFIG_FILE}")

    _print_step(4, "诊断") if not json_output else None
    report = run_doctor()
    if not json_output:
        _human_report(report)

    if not report.ok:
        body = {"ok": False, "step": 4, "doctor": report.to_dict()}
        if json_output:
            return body
        raise typer.Exit(1)
    steps_done.append("doctor")

    test_sent = False
    if not skip_test:
        do_test = yes
        if not yes and not json_output and sys.stdin.isatty():
            do_test = typer.confirm("发送一条测试消息到 Bot 私聊？", default=True)
        if do_test:
            _print_step(5, "发送测试消息") if not json_output else None
            try:
                process_send(
                    {
                        "fnp_version": 1,
                        "scene": "notify.plain",
                        "format": "card",
                        "payload": {
                            "title": "fnotify 安装完成",
                            "summary": "之后 Agent 可用 fnotify send 发通知。",
                        },
                    },
                    dry_run=False,
                )
                test_sent = True
                if not json_output:
                    typer.echo("  已发送。请在飞书打开与该 Bot 的私聊查看。")
            except Exception as exc:  # noqa: BLE001
                if not json_output:
                    typer.echo(f"  发送失败: {exc}", err=True)
                issues.append(f"test send: {exc}")

    if not json_output:
        typer.echo("\n全部完成。日常发送:")
        typer.echo(
            '  echo \'{"fnp_version":1,"scene":"notify.plain","payload":{"summary":"hi"}}\' | fnotify send --stdin'
        )

    return {
        "ok": report.ok and not issues,
        "steps": steps_done,
        "user_id": user_id,
        "config_path": str(CONFIG_FILE),
        "test_sent": test_sent,
        "issues": issues,
        "doctor": report.to_dict(),
    }