from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from feishu_notify.harnesses.cursor.sessions import get_session_id, put_session_id, session_key


def bridge_config(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("bridge")
    if not isinstance(block, dict):
        return {}
    return block


def cursor_options(cfg: dict[str, Any]) -> dict[str, Any]:
    b = bridge_config(cfg)
    raw = b.get("cursor")
    return raw if isinstance(raw, dict) else {}


def resolve_cursor_executable(cfg: dict[str, Any]) -> str:
    opts = cursor_options(cfg)
    raw = opts.get("executable")
    if isinstance(raw, str) and raw.strip():
        return shutil.which(raw.strip()) or raw.strip()
    return shutil.which("cursor") or "cursor"


def build_cursor_argv(
    *,
    prompt: str,
    workspace: Path,
    session_id: str | None,
    cfg: dict[str, Any],
) -> list[str]:
    exe = resolve_cursor_executable(cfg)
    opts = cursor_options(cfg)
    cmd = [
        exe,
        "agent",
        "--print",
        "--force",
        "--workspace",
        str(workspace),
    ]
    fmt = str(opts.get("output_format") or "stream-json").strip() or "stream-json"
    cmd.extend(["--output-format", fmt])
    if opts.get("stream_partial_output"):
        cmd.append("--stream-partial-output")
    model = opts.get("model")
    if isinstance(model, str) and model.strip():
        cmd.extend(["--model", model.strip()])
    mode = opts.get("mode")
    if isinstance(mode, str) and mode.strip():
        cmd.extend(["--mode", mode.strip()])
    if session_id:
        cmd.extend(["--resume", session_id])
    cmd.append(prompt)
    return cmd


def _parse_session_id_from_ndjson(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "system" and obj.get("subtype") == "init":
            sid = obj.get("session_id")
            if isinstance(sid, str) and sid.strip():
                return sid.strip()
        sid = obj.get("session_id")
        if isinstance(sid, str) and sid.strip():
            return sid.strip()
    return None


def _parse_final_result(text: str) -> tuple[str, bool]:
    """Return (assistant text, ok)."""
    result_text = ""
    ok = True
    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "result":
            if obj.get("is_error"):
                ok = False
            res = obj.get("result")
            if isinstance(res, str) and res.strip():
                result_text = res.strip()
            subtype = obj.get("subtype")
            if subtype and subtype != "success":
                ok = False
            continue
        if obj.get("type") == "assistant":
            msg = obj.get("message")
            if isinstance(msg, dict):
                for part in msg.get("content") or []:
                    if not isinstance(part, dict):
                        continue
                    t = part.get("text")
                    if isinstance(t, str) and t.strip():
                        chunks.append(t.strip())
    if result_text:
        return result_text, ok
    return "\n\n".join(chunks).strip(), ok


@dataclass
class CursorTurnResult:
    ok: bool
    output: str
    session_id: str | None
    exit_code: int
    cmd: list[str]
    error: str | None = None


def run_cursor_turn(
    *,
    prompt: str,
    workspace: Path,
    chat_id: str | None,
    cfg: dict[str, Any],
    timeout_sec: int,
    dry_run: bool = False,
    on_jsonl_line: Callable[[str], None] | None = None,
    progress_heartbeat: Callable[[], None] | None = None,
    heartbeat_sec: float = 8.0,
) -> CursorTurnResult:
    key = session_key(chat_id)
    session_id = get_session_id(key)
    cmd = build_cursor_argv(
        prompt=prompt,
        workspace=workspace,
        session_id=session_id,
        cfg=cfg,
    )
    if dry_run:
        return CursorTurnResult(
            ok=True,
            output="",
            session_id=session_id,
            exit_code=0,
            cmd=cmd,
        )

    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(workspace),
        env=env,
        bufsize=1,
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    stop = threading.Event()

    def _stderr_drain() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_chunks.append(line)

    def _heartbeat() -> None:
        if not progress_heartbeat:
            return
        while not stop.wait(heartbeat_sec):
            progress_heartbeat()

    threading.Thread(target=_stderr_drain, daemon=True).start()
    hb_thread = None
    if progress_heartbeat:
        hb_thread = threading.Thread(target=_heartbeat, daemon=True)
        hb_thread.start()

    assert proc.stdout is not None
    deadline = time.monotonic() + timeout_sec
    try:
        while True:
            if time.monotonic() > deadline:
                proc.kill()
                proc.wait(timeout=5)
                raise subprocess.TimeoutExpired(cmd, timeout_sec)
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            stdout_chunks.append(line)
            if on_jsonl_line:
                on_jsonl_line(line.rstrip("\n"))
    finally:
        stop.set()
        if hb_thread:
            hb_thread.join(timeout=0.5)

    if proc.poll() is None:
        try:
            proc.wait(timeout=max(1, timeout_sec))
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            raise

    stdout = "".join(stdout_chunks)
    new_session = _parse_session_id_from_ndjson(stdout) or session_id
    if new_session and new_session != session_id:
        label = str(cursor_options(cfg).get("session_label") or "Feishu Bot")
        put_session_id(key, new_session, label=label)

    output, stream_ok = _parse_final_result(stdout)
    stderr_text = "".join(stderr_chunks).strip()
    if not output and stderr_text:
        output = stderr_text

    ok = proc.returncode == 0 and stream_ok and bool(output.strip())
    err = None
    if proc.returncode != 0:
        ok = False
        err = output[:500] if output else f"cursor exit {proc.returncode}"
    elif not output.strip():
        ok = False
        err = "cursor 无输出（请执行 cursor agent login 或设置 CURSOR_API_KEY）"

    return CursorTurnResult(
        ok=ok,
        output=output,
        session_id=new_session,
        exit_code=int(proc.returncode or 0),
        cmd=cmd,
        error=err if not ok else None,
    )