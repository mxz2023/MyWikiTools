from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any, Optional

import typer

from feishu_notify import __version__
from feishu_notify import help_text as ht
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
from feishu_notify.bridge.catchup import run_catch_up
from feishu_notify.bridge.dispatch import (
    agent_timeout_sec,
    default_harness,
    default_workspace,
    format_dispatch_log,
    notify_enabled,
    run_dispatch,
)
from feishu_notify.bridge.listen import ALL_INBOUND_EVENTS, run_listen
from feishu_notify.bridge.state import (
    clear_all_in_flight,
    clear_in_flight,
    is_dispatched,
    is_in_flight,
)
from feishu_notify.harnesses.codex import clear_thread, get_thread_id, list_sessions, session_key
from feishu_notify.fnp import validate_payload_for_scene
from feishu_notify.config import load_config as _load_config
from feishu_notify.redact import redact_payload

OPT_JSON = typer.Option(False, "--json-output", help=ht.OPT_JSON_OUTPUT)

app = typer.Typer(
    rich_markup_mode=None,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=ht.ROOT_HELP,
    epilog=ht.EPILOG,
)

scenes_app = typer.Typer(help=ht.CMD_SCENES)
config_app = typer.Typer(help=ht.CMD_CONFIG)
run_app = typer.Typer(help=ht.CMD_RUN)
codex_app = typer.Typer(help="Codex session bindings for Feishu bridge / Feishu↔Codex 会话绑定")
app.add_typer(scenes_app, name="scenes")
app.add_typer(config_app, name="config")
app.add_typer(run_app, name="run")
app.add_typer(codex_app, name="codex")


@app.callback()
def main_callback(
    ctx: typer.Context,
    lang: Annotated[
        str,
        typer.Option(
            "--lang",
            help=ht.OPT_LANG,
        ),
    ] = "both",
    quiet: Annotated[
        bool,
        typer.Option("-q", "--quiet", help=ht.OPT_QUIET),
    ] = False,
) -> None:
    """Global options / 全局选项."""
    import feishu_notify.i18n as i18n

    if lang in ("en", "zh", "both"):
        i18n.LANG = lang
    ctx.ensure_object(dict)
    ctx.obj["quiet"] = quiet


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


@app.command(help=ht.CMD_VERSION)
def version() -> None:
    """Print package version / 打印版本号."""
    typer.echo(__version__)


@app.command(help=ht.CMD_INSTALL)
def install(
    yes: bool = typer.Option(False, "--yes", "-y", help=ht.OPT_INSTALL_YES),
    skip_test: bool = typer.Option(False, "--skip-test", help=ht.OPT_INSTALL_SKIP_TEST),
    json_output: bool = OPT_JSON,
) -> None:
    """Guide lark-cli + fnotify setup (start here) / 引导 lark-cli 与 fnotify 配置（推荐第一步）。"""
    body = run_install(yes=yes, skip_test=skip_test, json_output=json_output)
    if json_output:
        _emit(body, json_output=True)
    if not body.get("ok"):
        raise typer.Exit(EXIT_CONFIG)


@app.command(help=ht.CMD_UNINSTALL)
def uninstall(
    yes: bool = typer.Option(False, "--yes", "-y", help=ht.OPT_UNINSTALL_YES),
    json_output: bool = OPT_JSON,
) -> None:
    """Remove fnotify config; optional lark-cli reset / 删除 fnotify 配置；可选清理 lark-cli。"""
    try:
        body = run_uninstall(yes=yes, json_output=json_output)
        if json_output:
            _emit(body, json_output=True)
    except typer.Abort:
        raise typer.Exit(0) from None


@app.command(help=ht.CMD_DOCTOR)
def doctor(
    json_output: bool = OPT_JSON,
) -> None:
    """Check lark-cli, Feishu auth, dm_self recipient / 检查 lark-cli、飞书授权与私聊收件人。"""
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


def _invoke_listen(
    *,
    keys: tuple[str, ...],
    as_identity: str,
    timeout: str,
    max_events: int,
    jq: str | None,
    p2p_only: bool,
    self_only: bool,
    include_post: bool,
    log: bool,
    log_file: Path | None,
    log_meta: bool,
    quiet_bus: bool,
    dry_run: bool,
    json_output: bool,
    dispatch: bool,
    harness: str | None,
    workspace: Path | None,
    agent_timeout: int | None,
    no_notify: bool,
    dispatch_dry_run: bool,
    catch_up: bool = True,
) -> None:
    cfg = _load_config()
    harness_name = (harness or default_harness(cfg)).strip().lower()
    ws = default_workspace(cfg, workspace)
    timeout_agent = agent_timeout_sec(cfg, agent_timeout)
    use_notify = notify_enabled(cfg, dispatch and not no_notify)

    on_event = None
    if dispatch and not dry_run and not dispatch_dry_run:
        clear_all_in_flight()
    if dispatch and not dry_run and catch_up and not dispatch_dry_run:
        run_catch_up(
            harness=harness_name,
            workspace=ws,
            timeout_sec=timeout_agent,
            dry_run=False,
            notify=use_notify and not dispatch_dry_run,
        )
    if dispatch and not dry_run:
        typer.echo(
            f"[bridge] 就绪 harness={harness_name} workspace={ws} "
            f"(回复走飞书卡片；进度见 stderr)",
            err=True,
        )

        def _on_event(event_key: str, event: dict[str, Any]) -> None:
            if event_key == "im.message.receive_v1":
                mid = str(event.get("message_id") or "").strip()
                if mid and (is_dispatched(mid) or is_in_flight(mid)):
                    reason = "处理中" if is_in_flight(mid) else "已处理"
                    print(
                        f"[bridge] 跳过{reason} message_id={mid}（WebSocket 重放）",
                        file=sys.stderr,
                        flush=True,
                    )
                    return
            preview = str(event.get("content") or event.get("action_value") or "")[:80]
            print(f"[bridge] 派发中… {preview!r}", file=sys.stderr, flush=True)
            if harness_name in ("codex", "cursor"):
                label = "Cursor" if harness_name == "cursor" else "Codex"
                print(
                    f"[bridge] {label} 运行中，进度卡标题为「已收到 …」；"
                    "结论在同一张卡底部更新，不另发纯文本 ack",
                    file=sys.stderr,
                    flush=True,
                )
            try:
                result = run_dispatch(
                    event_key,
                    event,
                    harness=harness_name,
                    workspace=ws,
                    timeout_sec=timeout_agent,
                    notify=use_notify and not dispatch_dry_run,
                    dry_run=dispatch_dry_run,
                )
            except Exception as exc:  # noqa: BLE001
                mid = str(event.get("message_id") or "").strip()
                if mid:
                    clear_in_flight(mid)
                typer.echo(f"[bridge] 派发异常: {exc}", err=True)
                return
            typer.echo(format_dispatch_log(result), err=True)
            if json_output:
                _emit(result.to_dict(), json_output=True)
            if catch_up and result.ok:
                run_catch_up(
                    harness=harness_name,
                    workspace=ws,
                    timeout_sec=timeout_agent,
                    dry_run=False,
                    notify=use_notify and not dispatch_dry_run,
                )

        on_event = _on_event

    try:
        result = run_listen(
            events=keys,
            identity=as_identity,
            timeout=timeout,
            max_events=max_events,
            jq=jq,
            p2p_only=p2p_only,
            self_only=self_only,
            include_post=include_post,
            log=log or log_file is not None,
            log_file=log_file,
            log_meta=log_meta,
            mirror_bus=not quiet_bus,
            dry_run=dry_run,
            json_output=json_output,
            on_event=on_event,
            serial_dispatch=True,
            mirror_stdout=False if dispatch else None,
        )
    except FileNotFoundError:
        _fail("lark-cli not found; install and run fnotify install", EXIT_CONFIG)
        return
    if dry_run:
        return
    if json_output:
        _emit(result.to_dict(), json_output=True)
    elif not json_output:
        typer.echo(
            f"\n[listen] done — received {result.events_received} event(s), "
            f"reason={result.reason}, duration={result.duration_sec:.1f}s"
            + (f", log={result.log_file}" if result.log_file else ""),
            err=True,
        )
    if not result.ok:
        raise typer.Exit(EXIT_DELIVERY)


def _runs_store(path: Optional[Path]) -> Optional[Path]:
    if path:
        return path
    return CONFIG_DIR / "runs.json"


def _config_path(path: Optional[Path]) -> Optional[Path]:
    return path


@app.command()
def send(
    stdin: bool = typer.Option(False, "--stdin", help=ht.OPT_SEND_STDIN),
    file: Optional[Path] = typer.Option(None, "--file", help=ht.OPT_FILE),
    dry_run: bool = typer.Option(False, "--dry-run", help=ht.OPT_DRY_RUN),
    config: Optional[Path] = typer.Option(None, "--config", help=ht.OPT_CONFIG),
    runs_store: Optional[Path] = typer.Option(None, "--runs-store", help=ht.OPT_RUNS_STORE),
    json_output: bool = OPT_JSON,
) -> None:
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


send.__doc__ = f"{ht.CMD_SEND}\n\n{ht.DOC_SEND}"


@app.command()
def patch(
    stdin: bool = typer.Option(False, "--stdin", help=ht.OPT_SEND_STDIN),
    file: Optional[Path] = typer.Option(None, "--file", help=ht.OPT_FILE),
    message_id: Optional[str] = typer.Option(None, "--message-id", help=ht.OPT_PATCH_MSG_ID),
    dry_run: bool = typer.Option(False, "--dry-run", help=ht.OPT_DRY_RUN),
    config: Optional[Path] = typer.Option(None, "--config", help=ht.OPT_CONFIG),
    runs_store: Optional[Path] = typer.Option(None, "--runs-store", help=ht.OPT_RUNS_STORE),
    json_output: bool = OPT_JSON,
) -> None:
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


patch.__doc__ = f"{ht.CMD_PATCH}\n\n{ht.DOC_PATCH}"


@run_app.command("list", help=ht.GRP_RUN_LIST)
def run_list(
    runs_store: Optional[Path] = typer.Option(None, "--runs-store", help=ht.OPT_RUNS_STORE),
    json_output: bool = OPT_JSON,
) -> None:
    """List M2 bindings / 列出 M2 绑定。"""
    _emit(list_bindings(store_path=_runs_store(runs_store)), json_output=json_output)


@run_app.command("show", help=ht.GRP_RUN_SHOW)
def run_show(
    run_id: str = typer.Argument(..., help="run_id from context.run_id / 与 FNP context.run_id 一致"),
    runs_store: Optional[Path] = typer.Option(None, "--runs-store", help=ht.OPT_RUNS_STORE),
    json_output: bool = OPT_JSON,
) -> None:
    """Show one binding / 查看单个 run 的 message_id。"""
    binding = get_binding(run_id, store_path=_runs_store(runs_store))
    if not binding:
        _fail(f"no binding for run_id={run_id}", EXIT_VALIDATION)
    _emit(binding.to_dict(), json_output=json_output)


@run_app.command("clear", help=ht.GRP_RUN_CLEAR)
def run_clear(
    run_id: str = typer.Argument(..., help="run_id to drop / 要清除的 run_id"),
    runs_store: Optional[Path] = typer.Option(None, "--runs-store", help=ht.OPT_RUNS_STORE),
    json_output: bool = OPT_JSON,
) -> None:
    """Remove binding for run_id / 删除该 run_id 的绑定。"""
    cleared = clear_binding(run_id, store_path=_runs_store(runs_store))
    _emit({"ok": True, "run_id": run_id, "cleared": cleared}, json_output=json_output)


@app.command(help=ht.CMD_RENDER)
def render(
    scene: str = typer.Option(..., "--scene", help=ht.OPT_SCENE),
    file: Optional[Path] = typer.Option(None, "--file", help=ht.OPT_FILE),
    format: str = typer.Option("auto", "--format", help=ht.OPT_FORMAT),
    stdin: bool = typer.Option(False, "--stdin", help=ht.OPT_STDIN),
    json_output: bool = OPT_JSON,
) -> None:
    """Render scene template without send / 只渲染场景模板，不发送。"""
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


@scenes_app.command("list", help=ht.GRP_SCENES_LIST)
def scenes_list(json_output: bool = OPT_JSON) -> None:
    """Tabulate builtin scenes / 列出内置场景。"""
    _emit(list_scenes(), json_output=json_output)


@scenes_app.command("demo")
def scenes_demo(
    dry_run: bool = typer.Option(False, "--dry-run", help=ht.OPT_DRY_RUN),
    scene: Optional[str] = typer.Option(None, "--scene", help=ht.OPT_DEMO_SCENE),
    interval: float = typer.Option(0.8, "--interval", help=ht.OPT_DEMO_INTERVAL),
    json_output: bool = OPT_JSON,
) -> None:
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


scenes_demo.__doc__ = f"{ht.GRP_SCENES_DEMO}\n\n{ht.DOC_SCENES_DEMO}"


@scenes_app.command("describe", help=ht.GRP_SCENES_DESCRIBE)
def scenes_describe(
    scene_id: str = typer.Argument(..., help=ht.OPT_SCENE_ID),
    json_output: bool = OPT_JSON,
) -> None:
    """Show manifest, fields, templates / 查看 manifest、字段与模板路径。"""
    try:
        _emit(describe_scene(scene_id), json_output=json_output)
    except FileNotFoundError as exc:
        _fail(str(exc), EXIT_VALIDATION)


@config_app.command("init", help=ht.GRP_CONFIG_INIT)
def config_init(json_output: bool = OPT_JSON) -> None:
    """Create ~/.config/fnotify/config.yaml / 创建默认配置文件。"""
    path = init_config()
    _emit({"ok": True, "path": str(path), "hint": "Set routes.dm_self.user_id to your ou_"}, json_output=json_output)


@config_app.command("show", help=ht.GRP_CONFIG_SHOW)
def config_show(json_output: bool = OPT_JSON) -> None:
    """Print merged config / 显示合并后的配置。"""
    _emit(load_config(), json_output=json_output)


@app.command()
def listen(
    timeout: str = typer.Option(
        "0",
        "--timeout",
        "--duration",
        help=ht.OPT_LISTEN_TIMEOUT,
    ),
    max_events: int = typer.Option(0, "--max-events", help=ht.OPT_LISTEN_MAX_EVENTS),
    log: bool = typer.Option(False, "--log", help=ht.OPT_LISTEN_LOG),
    log_file: Optional[Path] = typer.Option(None, "--log-file", help=ht.OPT_LISTEN_LOG_FILE),
    log_meta: bool = typer.Option(False, "--log-meta", help=ht.OPT_LISTEN_LOG_META),
    quiet_bus: bool = typer.Option(False, "--quiet-bus", help=ht.OPT_LISTEN_QUIET_BUS),
    all_events: bool = typer.Option(False, "--all", help=ht.OPT_LISTEN_ALL),
    event: Optional[list[str]] = typer.Option(None, "--event", help=ht.OPT_LISTEN_EVENT),
    jq: Optional[str] = typer.Option(None, "--jq", help=ht.OPT_LISTEN_JQ),
    p2p_only: bool = typer.Option(
        True,
        "--p2p-only/--any-chat",
        help="Bot DM only in default jq / 默认 jq 仅 Bot 私聊",
    ),
    self_only: bool = typer.Option(
        True,
        "--self-only/--any-sender",
        help="Only dm_self user open_id / 仅配置中的 user open_id",
    ),
    include_post: bool = typer.Option(
        True,
        "--include-post/--text-only",
        help="Include message_type post / 包含富文本 post",
    ),
    as_identity: str = typer.Option("bot", "--as", help=ht.OPT_LISTEN_AS),
    dry_run: bool = typer.Option(False, "--dry-run", help=ht.OPT_LISTEN_DRY_RUN),
    dispatch: bool = typer.Option(False, "--dispatch", help=ht.OPT_DISPATCH),
    harness: Optional[str] = typer.Option(None, "--harness", help=ht.OPT_HARNESS),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help=ht.OPT_WORKSPACE),
    agent_timeout: Optional[int] = typer.Option(
        None, "--agent-timeout", help=ht.OPT_AGENT_TIMEOUT
    ),
    no_notify: bool = typer.Option(False, "--no-notify", help=ht.OPT_NO_NOTIFY),
    dispatch_dry_run: bool = typer.Option(
        False, "--dispatch-dry-run", help=ht.OPT_DISPATCH_DRY_RUN
    ),
    json_output: bool = OPT_JSON,
) -> None:
    if all_events and event:
        _fail("use either --all or --event, not both", EXIT_VALIDATION)
    if all_events:
        keys = ALL_INBOUND_EVENTS
    elif event:
        keys = tuple(event)
    else:
        keys = ("im.message.receive_v1",)

    _invoke_listen(
        keys=keys,
        as_identity=as_identity,
        timeout=timeout,
        max_events=max_events,
        jq=jq,
        p2p_only=p2p_only,
        self_only=self_only,
        include_post=include_post,
        log=log,
        log_file=log_file,
        log_meta=log_meta,
        quiet_bus=quiet_bus,
        dry_run=dry_run,
        json_output=json_output,
        dispatch=dispatch,
        harness=harness,
        workspace=workspace,
        agent_timeout=agent_timeout,
        no_notify=no_notify,
        dispatch_dry_run=dispatch_dry_run,
    )


listen.__doc__ = f"{ht.CMD_LISTEN}\n\n{ht.DOC_LISTEN}"


@app.command()
def bridge(
    timeout: str = typer.Option("0", "--timeout", "--duration", help=ht.OPT_LISTEN_TIMEOUT),
    max_events: int = typer.Option(0, "--max-events", help=ht.OPT_LISTEN_MAX_EVENTS),
    log: bool = typer.Option(True, "--log/--no-log", help=ht.OPT_LISTEN_LOG),
    log_file: Optional[Path] = typer.Option(None, "--log-file", help=ht.OPT_LISTEN_LOG_FILE),
    harness: Optional[str] = typer.Option(None, "--harness", help=ht.OPT_HARNESS),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help=ht.OPT_WORKSPACE),
    agent_timeout: Optional[int] = typer.Option(
        None, "--agent-timeout", help=ht.OPT_AGENT_TIMEOUT
    ),
    no_notify: bool = typer.Option(False, "--no-notify", help=ht.OPT_NO_NOTIFY),
    all_events: bool = typer.Option(False, "--all", help=ht.OPT_LISTEN_ALL),
    dispatch_dry_run: bool = typer.Option(
        False, "--dispatch-dry-run", help=ht.OPT_DISPATCH_DRY_RUN
    ),
    quiet_bus: bool = typer.Option(False, "--quiet-bus", help=ht.OPT_LISTEN_QUIET_BUS),
    catch_up: bool = typer.Option(
        True,
        "--catch-up/--no-catch-up",
        help="启动前扫描私聊，补跑仅有「已收到」、无结论文本的消息",
    ),
    json_output: bool = OPT_JSON,
) -> None:
    keys = ALL_INBOUND_EVENTS if all_events else ("im.message.receive_v1",)
    _invoke_listen(
        keys=keys,
        as_identity="bot",
        timeout=timeout,
        max_events=max_events,
        jq=None,
        p2p_only=True,
        self_only=True,
        include_post=True,
        log=log,
        log_file=log_file,
        log_meta=False,
        quiet_bus=quiet_bus,
        dry_run=False,
        json_output=json_output,
        dispatch=True,
        harness=harness,
        workspace=workspace,
        agent_timeout=agent_timeout,
        no_notify=no_notify,
        dispatch_dry_run=dispatch_dry_run,
        catch_up=catch_up,
    )


bridge.__doc__ = f"{ht.CMD_BRIDGE}\n\n{ht.DOC_BRIDGE}"


@codex_app.command("sessions", help="List Feishu chat_id → Codex thread_id / 列出会话绑定")
def codex_sessions_list(json_output: bool = OPT_JSON) -> None:
    _emit(list_sessions(), json_output=json_output)


@codex_app.command("reset", help="Clear Codex thread binding (new thread next message) / 清除绑定以开新对话")
def codex_session_reset(
    chat_id: Optional[str] = typer.Option(None, "--chat-id", help="Feishu oc_…; default dm_self key"),
    json_output: bool = OPT_JSON,
) -> None:
    key = session_key(chat_id)
    cleared = clear_thread(key)
    _emit({"ok": True, "chat_id": key, "cleared": cleared, "thread_id": get_thread_id(key)}, json_output=json_output)


if __name__ == "__main__":
    app()