from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from feishu_notify.bridge.progress import FeishuCodexProgress, agent_live_progress_enabled
from feishu_notify.bridge.state import clear_in_flight, mark_dispatched, mark_in_flight
from feishu_notify.card_safe import card_safe_summary
from feishu_notify.harnesses.codex import build_codex_argv, get_thread_id, run_codex_turn, session_key
from feishu_notify.harnesses.cursor import build_cursor_argv, run_cursor_turn
from feishu_notify.config import load_config
from feishu_notify.pipeline import process_send

BUILTIN_HARNESSES = frozenset({"cursor", "codex", "shell"})


@dataclass
class DispatchResult:
    ok: bool
    harness: str
    run_id: str
    prompt: str
    output: str
    exit_code: int
    cmd: list[str]
    error: str | None = None
    codex_thread_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "harness": self.harness,
            "run_id": self.run_id,
            "prompt": self.prompt,
            "output": self.output,
            "exit_code": self.exit_code,
            "cmd": self.cmd,
            "error": self.error,
            "codex_thread_id": self.codex_thread_id,
        }


def bridge_config(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("bridge")
    if not isinstance(block, dict):
        return {}
    return block


def configured_harness_names(cfg: dict[str, Any]) -> set[str]:
    b = bridge_config(cfg)
    raw = b.get("harnesses")
    if not isinstance(raw, dict):
        return set()
    return {str(k).strip().lower() for k in raw if str(k).strip()}


def default_harness(cfg: dict[str, Any]) -> str:
    b = bridge_config(cfg)
    name = str(b.get("default_harness") or "cursor").strip().lower()
    if name in BUILTIN_HARNESSES or name in configured_harness_names(cfg):
        return name
    return "cursor"


def default_workspace(cfg: dict[str, Any], override: Path | None) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    b = bridge_config(cfg)
    raw = b.get("workspace")
    if isinstance(raw, str) and raw.strip():
        return Path(raw.strip()).expanduser().resolve()
    return Path.cwd().resolve()


def agent_timeout_sec(cfg: dict[str, Any], override: int | None) -> int:
    if override is not None and override > 0:
        return override
    b = bridge_config(cfg)
    try:
        val = int(b.get("agent_timeout_sec") or 3600)
        return max(60, val)
    except (TypeError, ValueError):
        return 3600


def notify_enabled(cfg: dict[str, Any], cli_flag: bool) -> bool:
    b = bridge_config(cfg)
    if not cli_flag:
        return False
    if "notify" in b:
        return bool(b.get("notify"))
    return True


def _subst(template: str, ctx: dict[str, str]) -> str:
    out = template
    for key, val in ctx.items():
        out = out.replace("{" + key + "}", val)
    return out


def build_harness_argv(
    harness: str,
    *,
    prompt: str,
    workspace: Path,
    run_id: str,
    message_id: str,
    cfg: dict[str, Any],
    chat_id: str | None = None,
) -> list[str]:
    ctx = {
        "prompt": prompt,
        "workspace": str(workspace),
        "run_id": run_id,
        "message_id": message_id,
        "chat_id": chat_id or "",
    }
    harness = harness.lower()
    b = bridge_config(cfg)
    harnesses = b.get("harnesses") if isinstance(b.get("harnesses"), dict) else {}
    custom = harnesses.get(harness)

    if harness == "cursor":
        return build_cursor_argv(
            prompt=prompt,
            workspace=workspace,
            cfg=cfg,
            chat_id=chat_id,
        )

    if harness == "codex":
        dummy = workspace / ".fnotify-codex-last-msg"
        return build_codex_argv(
            prompt=prompt,
            workspace=workspace,
            thread_id=get_thread_id(session_key(ctx.get("chat_id"))),
            cfg=cfg,
            last_msg=dummy,
        )

    if harness == "shell":
        script = _subst(
            b.get("shell_cmd") or 'echo "fnotify bridge (shell): {prompt}"',
            ctx,
        )
        return ["sh", "-c", script]

    if custom:
        spec = custom if isinstance(custom, dict) else {}
        argv = spec.get("argv") or spec.get("command")
        if not isinstance(argv, list) or not argv:
            raise ValueError(f"bridge.harnesses.{harness}.argv required")
        return [_subst(str(part), ctx) for part in argv]

    raise ValueError(
        f"unknown harness: {harness}; use cursor|codex|shell, "
        "bridge.harnesses.<name>, or add under feishu_notify.harnesses/"
    )


def event_to_prompt(event_key: str, event: dict[str, Any]) -> str | None:
    if event_key == "im.message.receive_v1":
        content = event.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        return None
    if event_key == "card.action.trigger":
        raw = event.get("action_value")
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return f"[card action] {json.dumps(parsed, ensure_ascii=False)}"
            except json.JSONDecodeError:
                return f"[card action] {raw}"
        if raw is not None:
            return f"[card action] {json.dumps(raw, ensure_ascii=False)}"
        return "[card action] (no action_value)"
    return None


def make_run_id(event: dict[str, Any]) -> str:
    mid = event.get("message_id") or event.get("id") or event.get("event_id") or "unknown"
    return f"feishu-{mid}"


def _truncate(text: str, limit: int = 3500) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n…(truncated)"


def _log_feishu_send(envelope: dict[str, Any]) -> dict[str, Any] | None:
    import sys

    try:
        body = process_send(envelope, dry_run=False)
    except Exception as exc:
        print(
            f"[bridge] feishu send failed scene={envelope.get('scene')}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
    mid = body.get("message_id")
    fmt = body.get("format_used")
    print(
        f"[bridge] feishu sent scene={envelope.get('scene')} format={fmt} message_id={mid}",
        file=sys.stderr,
        flush=True,
    )
    return body


def _send_agent_reply(
    text: str,
    *,
    harness: str,
    run_id: str,
    session_ref: str | None,
    ok: bool,
    dry_run: bool,
    resume_hint: str | None = None,
) -> None:
    if dry_run or not text.strip():
        return
    body = text.strip()
    if len(body) <= 900:
        envelope = {
            "fnp_version": 1,
            "scene": "notify.plain",
            "format": "text",
            "route": "dm_self",
            "context": {"harness": harness, "run_id": run_id},
            "payload": {"summary": body},
        }
        _log_feishu_send(envelope)
        return
    fields: list[dict[str, str]] = []
    if session_ref:
        label = "Cursor session" if harness == "cursor" else "Codex thread"
        fields.append({"label": label, "value": session_ref})
        if resume_hint:
            fields.append({"label": "续聊", "value": resume_hint})
    title = "Cursor 回复" if harness == "cursor" else "Codex 回复"
    envelope = {
        "fnp_version": 1,
        "scene": "agent.conclusion",
        "route": "dm_self",
        "context": {"harness": harness, "run_id": run_id},
        "payload": {
            "title": title,
            "summary": body[:480],
            "body_md": body,
            "status": "success" if ok else "failed",
            "fields": fields,
        },
    }
    _log_feishu_send(envelope)


def _send_codex_reply(
    text: str,
    *,
    harness: str,
    run_id: str,
    thread_id: str | None,
    ok: bool,
    dry_run: bool,
) -> None:
    hint = f"codex exec resume {thread_id}" if thread_id else None
    _send_agent_reply(
        text,
        harness=harness,
        run_id=run_id,
        session_ref=thread_id,
        ok=ok,
        dry_run=dry_run,
        resume_hint=hint,
    )


def _send_scene(
    scene: str,
    *,
    harness: str,
    run_id: str,
    title: str,
    summary: str,
    status: str | None = None,
    dry_run: bool = False,
) -> None:
    payload: dict[str, Any] = {"title": title, "summary": summary}
    if status:
        payload["status"] = status
    payload["summary"] = card_safe_summary(str(payload.get("summary") or ""))
    envelope: dict[str, Any] = {
        "fnp_version": 1,
        "scene": scene,
        "route": "dm_self",
        "context": {"harness": harness, "run_id": run_id},
        "payload": payload,
    }
    if scene == "agent.ack":
        envelope["format"] = "text"
    if dry_run:
        return
    try:
        _log_feishu_send(envelope)
    except Exception:
        pass


def run_dispatch(
    event_key: str,
    event: dict[str, Any],
    *,
    harness: str,
    workspace: Path,
    timeout_sec: int,
    notify: bool,
    dry_run: bool = False,
    config_path: Path | None = None,
) -> DispatchResult:
    cfg = load_config(config_path)
    prompt = event_to_prompt(event_key, event)
    if not prompt:
        return DispatchResult(
            ok=False,
            harness=harness,
            run_id="",
            prompt="",
            output="",
            exit_code=2,
            cmd=[],
            error="empty prompt for event",
        )

    run_id = make_run_id(event)
    message_id = str(event.get("message_id") or "")
    chat_id = str(event.get("chat_id") or "") or None
    try:
        cmd = build_harness_argv(
            harness,
            prompt=prompt,
            workspace=workspace,
            run_id=run_id,
            message_id=message_id,
            cfg=cfg,
            chat_id=chat_id,
        )
    except ValueError as exc:
        return DispatchResult(
            ok=False,
            harness=harness,
            run_id=run_id,
            prompt=prompt,
            output="",
            exit_code=2,
            cmd=[],
            error=str(exc),
        )

    if dry_run:
        return DispatchResult(
            ok=True,
            harness=harness,
            run_id=run_id,
            prompt=prompt,
            output="",
            exit_code=0,
            cmd=cmd,
            error=None,
        )

    live_progress = notify and agent_live_progress_enabled(cfg, harness)
    if notify and not live_progress:
        _send_scene(
            "agent.ack",
            harness=harness,
            run_id=run_id,
            title="已收到",
            summary=_truncate(prompt, 500),
            status="running",
        )

    if message_id and not dry_run:
        mark_in_flight(message_id)

    codex_thread_id: str | None = None
    cursor_session_id: str | None = None
    agent_progress: FeishuCodexProgress | None = None
    try:
        if harness == "codex":
            if live_progress:
                agent_progress = FeishuCodexProgress(
                    run_id=run_id,
                    harness=harness,
                    prompt=prompt,
                    cfg=cfg,
                )
                agent_progress.start()
            turn = run_codex_turn(
                prompt=prompt,
                workspace=workspace,
                chat_id=chat_id,
                cfg=cfg,
                timeout_sec=timeout_sec,
                dry_run=False,
                on_jsonl_line=(
                    agent_progress.on_jsonl_line if agent_progress else None
                ),
                progress_heartbeat=(
                    agent_progress.heartbeat if agent_progress else None
                ),
            )
            codex_thread_id = turn.thread_id
            output = turn.output
            ok = turn.ok
            cmd = turn.cmd
            exit_code = turn.exit_code
            if turn.error and not output:
                output = turn.error
            if agent_progress:
                agent_progress.finish(
                    ok=ok,
                    reply=output if ok else (output or turn.error),
                )
        elif harness == "cursor":
            if live_progress:
                agent_progress = FeishuCodexProgress(
                    run_id=run_id,
                    harness=harness,
                    prompt=prompt,
                    cfg=cfg,
                )
                agent_progress.start()
            turn = run_cursor_turn(
                prompt=prompt,
                workspace=workspace,
                chat_id=chat_id,
                cfg=cfg,
                timeout_sec=timeout_sec,
                dry_run=False,
                on_jsonl_line=(
                    agent_progress.on_jsonl_line if agent_progress else None
                ),
                progress_heartbeat=(
                    agent_progress.heartbeat if agent_progress else None
                ),
            )
            cursor_session_id = turn.session_id
            output = turn.output
            ok = turn.ok
            cmd = turn.cmd
            exit_code = turn.exit_code
            if turn.error and not output:
                output = turn.error
            if agent_progress:
                agent_progress.finish(
                    ok=ok,
                    reply=output if ok else (output or turn.error),
                )
        else:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=str(workspace),
            )
            output = (proc.stdout or "").strip()
            if proc.stderr and not output:
                output = proc.stderr.strip()
            elif proc.stderr:
                output = output + "\n\n[stderr]\n" + proc.stderr.strip()
            ok = proc.returncode == 0
            exit_code = int(proc.returncode or 0)
    except subprocess.TimeoutExpired:
        if notify:
            if agent_progress:
                agent_progress.finish(
                    ok=False,
                    reply=f"Agent 超过 {timeout_sec}s 未完成",
                )
            else:
                _send_scene(
                    "agent.failure",
                    harness=harness,
                    run_id=run_id,
                    title="超时",
                    summary=f"Agent 超过 {timeout_sec}s 未完成",
                    status="failed",
                )
        if message_id:
            clear_in_flight(message_id)
        return DispatchResult(
            ok=False,
            harness=harness,
            run_id=run_id,
            prompt=prompt,
            output="",
            exit_code=124,
            cmd=cmd,
            error="agent timeout",
            codex_thread_id=codex_thread_id,
        )
    except FileNotFoundError:
        err = f"command not found: {cmd[0]}"
        if notify:
            _send_scene(
                "agent.failure",
                harness=harness,
                run_id=run_id,
                title="启动失败",
                summary=err,
                status="failed",
            )
        if message_id:
            clear_in_flight(message_id)
        return DispatchResult(
            ok=False,
            harness=harness,
            run_id=run_id,
            prompt=prompt,
            output="",
            exit_code=127,
            cmd=cmd,
            error=err,
            codex_thread_id=codex_thread_id,
        )

    if notify:
        if harness in ("codex", "cursor"):
            if agent_progress:
                pass
            elif ok:
                session = codex_thread_id if harness == "codex" else cursor_session_id
                resume = None
                if harness == "codex" and codex_thread_id:
                    resume = f"codex exec resume {codex_thread_id}"
                elif harness == "cursor" and cursor_session_id:
                    resume = f"cursor agent --resume {cursor_session_id}"
                _send_agent_reply(
                    output or "(无输出)",
                    harness=harness,
                    run_id=run_id,
                    session_ref=session,
                    ok=True,
                    dry_run=False,
                    resume_hint=resume,
                )
            else:
                title = "Cursor 失败" if harness == "cursor" else "Codex 失败"
                _send_scene(
                    "agent.failure",
                    harness=harness,
                    run_id=run_id,
                    title=title,
                    summary=_truncate(output or "未知错误", 800),
                    status="failed",
                )
        else:
            summary = _truncate(output or "(no stdout)")
            scene = "agent.conclusion" if ok else "agent.failure"
            _send_scene(
                scene,
                harness=harness,
                run_id=run_id,
                title="完成" if ok else "失败",
                summary=summary,
                status="success" if ok else "failed",
            )

    result = DispatchResult(
        ok=ok,
        harness=harness,
        run_id=run_id,
        prompt=prompt,
        output=output,
        exit_code=exit_code,
        cmd=cmd,
        error=None if ok else (output[:200] if output else f"exit {exit_code}"),
        codex_thread_id=codex_thread_id,
    )
    if message_id and not dry_run:
        if ok:
            mark_dispatched(message_id)
        else:
            clear_in_flight(message_id)
    return result


def format_dispatch_log(result: DispatchResult) -> str:
    cmd = " ".join(shlex.quote(p) for p in result.cmd)
    header = f"[bridge] harness={result.harness} run_id={result.run_id} ok={result.ok}"
    body = textwrap.shorten(result.prompt, width=120, placeholder="…")
    lines = [header, f"  prompt: {body}", f"  cmd: {cmd}", f"  exit: {result.exit_code}"]
    if result.codex_thread_id:
        lines.append(f"  codex_thread: {result.codex_thread_id}")
    return "\n".join(lines)