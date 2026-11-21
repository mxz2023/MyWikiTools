from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any

import typer

from feishu_notify.constants import CONFIG_DIR, CONFIG_FILE


def _lark_already_clean(stderr_or_stdout: str) -> bool:
    text = stderr_or_stdout.lower()
    markers = (
        "not configured",
        "not_configured",
        "no apps",
        "malformed config",
        "not logged",
        "no token",
    )
    return any(m in text for m in markers)


def _run_lark_cmd(args: list[str]) -> tuple[int, str]:
    env = {**os.environ, "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1"}
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        env=env,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _purge_lark_cli_local() -> dict[str, Any]:
    if not shutil.which("lark-cli"):
        return {"skipped": True, "logout": True, "config_remove": True, "note": "no lark-cli"}

    code_logout, out_logout = _run_lark_cmd(["lark-cli", "auth", "logout", "--json"])
    logout_ok = code_logout == 0 or _lark_already_clean(out_logout)

    code_remove, out_remove = _run_lark_cmd(["lark-cli", "config", "remove"])
    config_remove_ok = code_remove == 0 or _lark_already_clean(out_remove)

    return {
        "skipped": False,
        "logout": logout_ok,
        "config_remove": config_remove_ok,
        "already_clean": _lark_already_clean(out_logout + out_remove),
    }


def _fnotify_paths_on_path() -> list[str]:
    proc = subprocess.run(
        ["sh", "-c", "which -a fnotify 2>/dev/null || true"],
        capture_output=True,
        text=True,
    )
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return lines


def _pipx_uninstall_fnotify() -> tuple[bool, list[str]]:
    before = _fnotify_paths_on_path()
    if not shutil.which("pipx"):
        return False, before
    proc = subprocess.run(
        ["pipx", "uninstall", "feishu-notify-cli"],
        capture_output=True,
        text=True,
    )
    pipx_ok = proc.returncode == 0
    after = _fnotify_paths_on_path()
    return pipx_ok, after if after else before


def run_uninstall(*, yes: bool = False, json_output: bool = False) -> dict[str, Any]:
    lark_purged: dict[str, Any] | None = None
    pipx_removed: bool | None = None
    fnotify_paths_after: list[str] | None = None

    if not json_output:
        typer.echo("fnotify uninstall 分三步（交互模式下会逐步询问）：")
        typer.echo("  1) 删除本机配置 ~/.config/fnotify")
        typer.echo("  2) 可选：清除 lark-cli 本机应用凭证与用户登录态")
        typer.echo("  3) 可选：pipx 卸载 fnotify / feishu-notify 命令")
        typer.echo("  （lark-cli / fnotify 若还通过 pyenv、brew 等安装，需另行卸载）")
        typer.echo("")
        if not yes and sys.stdin.isatty():
            if not typer.confirm(f"步骤 1：删除 {CONFIG_DIR}？", default=False):
                raise typer.Abort()

    removed = False
    if CONFIG_DIR.exists():
        shutil.rmtree(CONFIG_DIR)
        removed = True

    interactive = not yes and sys.stdin.isatty() and not json_output

    if interactive:
        if shutil.which("lark-cli"):
            if typer.confirm(
                "步骤 2：同时清除 lark-cli 本机配置？（auth logout + config remove）",
                default=False,
            ):
                lark_purged = _purge_lark_cli_local()
                if lark_purged.get("already_clean") and lark_purged["logout"] and lark_purged["config_remove"]:
                    typer.echo("  ✓ lark-cli 本机已是未配置状态（无需再清）")
                elif lark_purged["logout"] and lark_purged["config_remove"]:
                    typer.echo("  ✓ lark-cli 本机凭证已清除")
                else:
                    typer.echo("  ✗ 未完全成功，可手动:")
                    typer.echo("      lark-cli auth logout --json")
                    typer.echo("      lark-cli config remove")
        else:
            typer.echo("  · 未安装 lark-cli，跳过步骤 2")

        if shutil.which("pipx"):
            if typer.confirm(
                "步骤 3：pipx 卸载 feishu-notify-cli（本终端将失去 fnotify 命令）？",
                default=False,
            ):
                pipx_removed, fnotify_paths_after = _pipx_uninstall_fnotify()
                if pipx_removed:
                    typer.echo("  ✓ pipx 已卸载 feishu-notify-cli")
                else:
                    typer.echo("  ✗ pipx 未找到该包或卸载失败")
                remaining = fnotify_paths_after or _fnotify_paths_on_path()
                if remaining:
                    typer.echo("  仍能在 PATH 中找到 fnotify（pipx 以外的安装）：")
                    for p in remaining:
                        typer.echo(f"      {p}")
                    if any(".pyenv/shims" in p for p in remaining):
                        typer.echo(
                            "  → 常见原因：pyenv 下 pip install -e 装过；"
                            "在对应环境里 pip uninstall feishu-notify-cli"
                        )
                else:
                    typer.echo("  ✓ PATH 中已无 fnotify")
        else:
            typer.echo("  · 未找到 pipx，跳过步骤 3")
            left = _fnotify_paths_on_path()
            if left:
                typer.echo("  当前 fnotify 位于：")
                for p in left:
                    typer.echo(f"      {p}")

    if not json_output:
        if removed:
            typer.echo(f"\n✓ 步骤 1 完成：已删除 {CONFIG_DIR}")
        else:
            typer.echo("\n· 步骤 1：配置目录不存在，无需删除")
        if yes:
            typer.echo(
                "（--yes 仅执行步骤 1；要清 lark-cli / pipx，请不带 --yes 再运行 uninstall）"
            )
        elif not interactive:
            typer.echo("（非交互环境：仅执行步骤 1）")
        else:
            typer.echo("\n重新配置: fnotify install（需先配好 lark-cli）")

    return {
        "ok": True,
        "removed_fnotify": removed,
        "config_dir": str(CONFIG_DIR),
        "config_file_was": str(CONFIG_FILE),
        "lark_purged": lark_purged,
        "pipx_removed": pipx_removed,
        "fnotify_paths_remaining": fnotify_paths_after or _fnotify_paths_on_path(),
    }