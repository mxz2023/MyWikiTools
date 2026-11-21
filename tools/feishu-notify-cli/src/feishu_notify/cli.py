from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer

from feishu_notify import __version__
from feishu_notify.checks import run_doctor
from feishu_notify.config import CONFIG_FILE, init_config, load_config
from feishu_notify.install_flow import run_install
from feishu_notify.uninstall_flow import run_uninstall
from feishu_notify.constants import (
    EXIT_CONFIG,
    EXIT_DELIVERY,
    EXIT_RENDER,
    EXIT_VALIDATION,
)
from feishu_notify.fnp import FnpValidationError, validate_envelope
from feishu_notify.deliver import DeliveryError
from feishu_notify.pipeline import process_send
from feishu_notify.constants import CONFIG_DIR
from feishu_notify.runs import clear_binding, get_binding, list_bindings
from feishu_notify.render import render_message
from feishu_notify.policy import resolve_format, resolve_identity
from feishu_notify.scenes import describe_scene, list_scenes, load_manifest
from feishu_notify.scenes_demo import run_scenes_demo
from feishu_notify.fnp import validate_payload_for_scene
from feishu_notify.config import load_config as _load_config
from feishu_notify.redact import redact_payload

OPT_JSON = typer.Option(False, "--json-output", help="Wrap body in {status, headers, body}")

app = typer.Typer(
    rich_markup_mode=None,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Feishu agent outbound (FNP v1) via lark-cli — fnotify",
)

scenes_app = typer.Typer(help="Built-in scene catalog (repo-maintained templates).")
config_app = typer.Typer(help="Local delivery config (~/.config/fnotify/).")
run_app = typer.Typer(help="M2 run_id ↔ message_id bindings (~/.config/fnotify/runs.json).")
app.add_typer(scenes_app, name="scenes")
app.add_typer(config_app, name="config")
app.add_typer(run_app, name="run")


def _emit(body: Any, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps({"status": 200, "headers": {}, "body": body}, ensure_ascii=False, indent=2))
    elif isinstance(body, (dict, list)):
        typer.echo(json.dumps(body, ensure_ascii=False, indent=2))
    else:
        typer.echo(str(body))


def _fail(msg: str, code: int) -> None:
    typer.echo(msg, err=True)
    raise typer.Exit(code)


def _read_json_input(stdin: bool, file: Optional[Path]) -> dict[str, Any]:
    if file:
        return json.loads(file.read_text(encoding="utf-8"))
    if stdin or not sys.stdin.isatty():
        raw = sys.stdin.read()
        if not raw.strip():
            _fail("no JSON on stdin; pass --file or pipe FNP envelope", EXIT_VALIDATION)
        return json.loads(raw)
    _fail("no input; use --stdin, pipe JSON, or --file", EXIT_VALIDATION)
    raise AssertionError


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(__version__)


@app.command()
def install(
    yes: bool = typer.Option(False, "--yes", "-y", help="Non-interactive; auto send test message"),
    skip_test: bool = typer.Option(False, "--skip-test", help="Skip test message after setup"),
    json_output: bool = OPT_JSON,
) -> None:
    """Guide lark-cli + fnotify setup (recommended first command)."""
    body = run_install(yes=yes, skip_test=skip_test, json_output=json_output)
    if json_output:
        _emit(body, json_output=True)
    if not body.get("ok"):
        raise typer.Exit(EXIT_CONFIG)


@app.command()
def uninstall(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = OPT_JSON,
) -> None:
    """Remove fnotify config; interactively offers lark-cli reset and pipx uninstall."""
    try:
        body = run_uninstall(yes=yes, json_output=json_output)
        if json_output:
            _emit(body, json_output=True)
    except typer.Abort:
        raise typer.Exit(0) from None


@app.command()
def doctor(
    json_output: bool = OPT_JSON,
) -> None:
    """Checklist: lark-cli, bot/user auth, fnotify recipient."""
    report = run_doctor()
    if json_output:
        _emit(report.to_dict(), json_output=True)
    else:
        typer.echo(f"config: {report.config_path}\n")
        for item in report.items:
            mark = "OK " if item.ok else "FAIL"
            typer.echo(f"[{mark}] {item.title}")
            typer.echo(f"       {item.detail}")
            if not item.ok and item.fix:
                typer.echo(f"       fix: {item.fix}")
        if not report.ok:
            typer.echo("\n建议: fnotify install")
    if not report.ok:
        raise typer.Exit(EXIT_CONFIG)


def _runs_store(path: Optional[Path]) -> Optional[Path]:
    if path:
        return path
    return CONFIG_DIR / "runs.json"


def _config_path(path: Optional[Path]) -> Optional[Path]:
    return path


@app.command()
def send(
    stdin: bool = typer.Option(False, "--stdin", help="Read FNP JSON from stdin"),
    file: Optional[Path] = typer.Option(None, "--file", help="FNP JSON file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Render and build lark-cli args without sending"),
    config: Optional[Path] = typer.Option(None, "--config", help="Config YAML path"),
    runs_store: Optional[Path] = typer.Option(None, "--runs-store", help="run bindings JSON path"),
    json_output: bool = OPT_JSON,
) -> None:
    """Validate FNP envelope, render scene, deliver via lark-cli (M2 auto patch for agent.progress)."""
    try:
        raw = _read_json_input(stdin, file)
        body = process_send(
            raw,
            dry_run=dry_run,
            config_path=_config_path(config),
            store_path=_runs_store(runs_store),
        )
        _emit(body, json_output=json_output)
    except FnpValidationError as exc:
        _fail(str(exc), EXIT_VALIDATION)
    except FileNotFoundError as exc:
        _fail(str(exc), EXIT_VALIDATION)
    except DeliveryError as exc:
        _fail(str(exc), EXIT_DELIVERY)
    except ValueError as exc:
        _fail(str(exc), EXIT_DELIVERY)
    except Exception as exc:  # noqa: BLE001
        _fail(str(exc), EXIT_RENDER)


@app.command()
def patch(
    stdin: bool = typer.Option(False, "--stdin", help="Read FNP JSON from stdin"),
    file: Optional[Path] = typer.Option(None, "--file", help="FNP JSON file"),
    message_id: Optional[str] = typer.Option(None, "--message-id", help="Target om_ message id"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    config: Optional[Path] = typer.Option(None, "--config"),
    runs_store: Optional[Path] = typer.Option(None, "--runs-store"),
    json_output: bool = OPT_JSON,
) -> None:
    """Patch an existing interactive card (alias for send with delivery.mode=patch)."""
    try:
        raw = _read_json_input(stdin, file)
        delivery = dict(raw.get("delivery") or {})
        delivery["mode"] = "patch"
        if message_id:
            delivery["message_id"] = message_id
        raw["delivery"] = delivery
        body = process_send(
            raw,
            dry_run=dry_run,
            config_path=_config_path(config),
            store_path=_runs_store(runs_store),
        )
        _emit(body, json_output=json_output)
    except FnpValidationError as exc:
        _fail(str(exc), EXIT_VALIDATION)
    except DeliveryError as exc:
        _fail(str(exc), EXIT_DELIVERY)
    except Exception as exc:  # noqa: BLE001
        _fail(str(exc), EXIT_RENDER)


@run_app.command("list")
def run_list(
    runs_store: Optional[Path] = typer.Option(None, "--runs-store"),
    json_output: bool = OPT_JSON,
) -> None:
    _emit(list_bindings(store_path=_runs_store(runs_store)), json_output=json_output)


@run_app.command("show")
def run_show(
    run_id: str = typer.Argument(...),
    runs_store: Optional[Path] = typer.Option(None, "--runs-store"),
    json_output: bool = OPT_JSON,
) -> None:
    binding = get_binding(run_id, store_path=_runs_store(runs_store))
    if not binding:
        _fail(f"no binding for run_id={run_id}", EXIT_VALIDATION)
    _emit(binding.to_dict(), json_output=json_output)


@run_app.command("clear")
def run_clear(
    run_id: str = typer.Argument(...),
    runs_store: Optional[Path] = typer.Option(None, "--runs-store"),
    json_output: bool = OPT_JSON,
) -> None:
    cleared = clear_binding(run_id, store_path=_runs_store(runs_store))
    _emit({"ok": True, "run_id": run_id, "cleared": cleared}, json_output=json_output)


@app.command()
def render(
    scene: str = typer.Option(..., "--scene", help="Scene id, e.g. agent.conclusion"),
    file: Optional[Path] = typer.Option(None, "--file", help="JSON file with payload + optional context"),
    format: str = typer.Option("auto", "--format", help="auto|text|card"),
    stdin: bool = typer.Option(False, "--stdin", help="Read payload JSON from stdin"),
    json_output: bool = OPT_JSON,
) -> None:
    """Render text or card without sending (debug templates)."""
    try:
        if file:
            data = json.loads(file.read_text(encoding="utf-8"))
        elif stdin or not sys.stdin.isatty():
            data = json.loads(sys.stdin.read())
        else:
            data = {"payload": {"title": "Demo", "summary": "Hello from fnotify render"}}
        envelope = validate_envelope(
            {
                "fnp_version": 1,
                "scene": scene,
                "format": format,
                "identity": "auto",
                "route": "dm_self",
                "payload": data.get("payload") or data,
                "context": data.get("context") or {},
            }
        )
        manifest = load_manifest(scene)
        validate_payload_for_scene(manifest, envelope["payload"])
        cfg = _load_config()
        envelope["payload"] = redact_payload(
            envelope["payload"], list(cfg.get("redact_patterns") or [])
        )
        identity = resolve_identity(envelope, manifest, cfg)
        fmt = resolve_format(envelope, manifest)
        out = render_message(envelope, fmt)
        body = {"scene": scene, "identity": identity, "format_used": fmt, "rendered": out}
        _emit(body, json_output=json_output)
    except FnpValidationError as exc:
        _fail(str(exc), EXIT_VALIDATION)
    except FileNotFoundError as exc:
        _fail(str(exc), EXIT_VALIDATION)


@scenes_app.command("list")
def scenes_list(json_output: bool = OPT_JSON) -> None:
    _emit(list_scenes(), json_output=json_output)


@scenes_app.command("demo")
def scenes_demo(
    dry_run: bool = typer.Option(False, "--dry-run", help="Render only, do not send to Feishu"),
    scene: Optional[str] = typer.Option(None, "--scene", help="Only one scene id"),
    interval: float = typer.Option(0.8, "--interval", help="Seconds between sends (live only)"),
    json_output: bool = OPT_JSON,
) -> None:
    """Send sample card for each builtin scene (style preview in Bot DM)."""
    try:
        results = run_scenes_demo(dry_run=dry_run, only=scene, interval_sec=interval)
        _emit(
            {"ok": True, "count": len(results), "dry_run": dry_run, "results": results},
            json_output=json_output,
        )
        if not json_output and not dry_run:
            typer.echo(f"\n已发送 {len(results)} 条样式预览到 Bot 私聊（每条标题含「样式预览」）。")
        elif not json_output and dry_run:
            typer.echo(f"\n干跑完成 {len(results)} 个场景，未发飞书。")
    except ValueError as exc:
        _fail(str(exc), EXIT_VALIDATION)
    except Exception as exc:  # noqa: BLE001
        _fail(str(exc), EXIT_DELIVERY)


@scenes_app.command("describe")
def scenes_describe(
    scene_id: str = typer.Argument(..., help="Scene id"),
    json_output: bool = OPT_JSON,
) -> None:
    try:
        _emit(describe_scene(scene_id), json_output=json_output)
    except FileNotFoundError as exc:
        _fail(str(exc), EXIT_VALIDATION)


@config_app.command("init")
def config_init(json_output: bool = OPT_JSON) -> None:
    path = init_config()
    _emit({"ok": True, "path": str(path), "hint": "Set routes.dm_self.user_id to your ou_"}, json_output=json_output)


@config_app.command("show")
def config_show(json_output: bool = OPT_JSON) -> None:
    _emit(load_config(), json_output=json_output)


if __name__ == "__main__":
    app()