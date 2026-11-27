from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from feishu_notify.harnesses.codex.sessions import get_thread_id, put_thread_id, session_key


def bridge_config(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("bridge")
    if not isinstance(block, dict):
        return {}
    return block


@dataclass
class CodexTurnResult:
    ok: bool
    output: str
    thread_id: str | None
    exit_code: int
    cmd: list[str]
    error: str | None = None


def codex_options(cfg: dict[str, Any]) -> dict[str, Any]:
    b = bridge_config(cfg)
    raw = b.get("codex")
    return raw if isinstance(raw, dict) else {}


MACOS_BUNDLED_CODEX = (
    "/Applications/ChatGPT.app/Contents/Resources/codex-cli/"
    "CodexCLI.app/Contents/MacOS/codex"
)


def resolve_codex_executable(cfg: dict[str, Any]) -> str:
    """Pick Codex CLI binary.

    Homebrew/npm ``codex`` can lag behind the ChatGPT.app bundle and reject
  desktop-only models (e.g. gpt-6-sol) with ChatGPT-catalog errors. Override
    via ``bridge.codex.executable`` to use the app-bundled CLI.
    """
    opts = codex_options(cfg)
    raw = opts.get("executable") or opts.get("codex_bin")
    if isinstance(raw, str) and raw.strip():
        path = Path(raw.strip()).expanduser()
        if path.is_file():
            return str(path)
        found = shutil.which(raw.strip())
        if found:
            return found
    if Path(MACOS_BUNDLED_CODEX).is_file():
        return MACOS_BUNDLED_CODEX
    return shutil.which("codex") or "codex"


def _append_codex_flags(
    cmd: list[str],
    opts: dict[str, Any],
    *,
    last_msg: Path,
    workspace: Path | None,
    resume: bool = False,
) -> None:
    if workspace is not None:
        cmd.extend(["-C", str(workspace)])
    if opts.get("skip_git_repo_check", True):
        cmd.append("--skip-git-repo-check")
    if resume:
        if opts.get("approve_for_me", True):
            cmd.extend(["-c", "approval_policy=never"])
        elif opts.get("dangerously_bypass", False):
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
    elif opts.get("approve_for_me", True):
        cmd.append("--approve-for-me")
    elif opts.get("dangerously_bypass", False):
        cmd.append("--dangerously-bypass-approvals-and-sandbox")
    if opts.get("json_events", True):
        cmd.append("--json")
    model = opts.get("model")
    if isinstance(model, str) and model.strip():
        cmd.extend(["-m", model.strip()])
    profile = opts.get("profile")
    if isinstance(profile, str) and profile.strip():
        cmd.extend(["-p", profile.strip()])
    overrides = opts.get("config_overrides")
    if isinstance(overrides, list):
        for item in overrides:
            if isinstance(item, str) and item.strip():
                cmd.extend(["-c", item.strip()])
    cmd.extend(["-o", str(last_msg)])


def build_codex_argv(
    *,
    prompt: str,
    workspace: Path,
    thread_id: str | None,
    cfg: dict[str, Any],
    last_msg: Path,
) -> list[str]:
    exe = resolve_codex_executable(cfg)
    opts = codex_options(cfg)
    if thread_id:
        # resume 子命令无 -C；工作区沿用原 thread
        cmd = [exe, "exec", "resume"]
        _append_codex_flags(cmd, opts, last_msg=last_msg, workspace=None, resume=True)
        cmd.extend([thread_id, prompt])
    else:
        cmd = [exe, "exec"]
        _append_codex_flags(cmd, opts, last_msg=last_msg, workspace=workspace, resume=False)
        cmd.append(prompt)
    return cmd


def _parse_thread_id_from_jsonl(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "thread.started":
            tid = obj.get("thread_id")
            if isinstance(tid, str) and tid.strip():
                return tid.strip()
    return None


def _parse_agent_text_from_jsonl(text: str) -> str:
    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "item.completed":
            continue
        item = obj.get("item")
        if not isinstance(item, dict):
            continue
        itype = item.get("type")
        if itype in ("agent_message", "message", "assistant_message"):
            msg = item.get("text") or item.get("message") or item.get("content")
            if isinstance(msg, str) and msg.strip():
                chunks.append(msg.strip())
        elif itype == "error":
            msg = item.get("message")
            if isinstance(msg, str):
                chunks.append(f"[error] {msg}")
    return "\n\n".join(chunks).strip()


def _extract_turn_failed(text: str) -> str | None:
    for line in text.splitlines():
        if '"turn.failed"' not in line:
            continue
        try:
            obj = json.loads(line.strip())
        except json.JSONDecodeError:
            continue
        err = obj.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
        if isinstance(err, str):
            return err
    return None


def _clean_model_error(message: str) -> str:
    m = re.search(r'"message":"([^"]+)"', message)
    if m:
        return m.group(1)
    return message[:500]


def run_codex_turn(
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
) -> CodexTurnResult:
    key = session_key(chat_id)
    thread_id = get_thread_id(key)
    fd, last_path = tempfile.mkstemp(suffix=".txt", prefix="fnotify-codex-")
    os.close(fd)
    last_msg = Path(last_path)
    try:
        cmd = build_codex_argv(
            prompt=prompt,
            workspace=workspace,
            thread_id=thread_id,
            cfg=cfg,
            last_msg=last_msg,
        )
        if dry_run:
            return CodexTurnResult(
                ok=True,
                output="",
                thread_id=thread_id,
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
        stop = threading.Event()

        def _stderr_drain() -> None:
            assert proc.stderr is not None
            for _line in proc.stderr:
                pass

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
        new_thread = _parse_thread_id_from_jsonl(stdout) or thread_id
        if new_thread and new_thread != thread_id:
            opts = codex_options(cfg)
            name = opts.get("thread_name") or "Feishu Bot"
            put_thread_id(key, new_thread, thread_name=str(name))

        output = ""
        if last_msg.is_file():
            output = last_msg.read_text(encoding="utf-8").strip()
        if not output:
            output = _parse_agent_text_from_jsonl(stdout)
        if not output and proc.stderr:
            output = proc.stderr.strip()

        fail = _extract_turn_failed(stdout)
        ok = proc.returncode == 0 and not fail
        err = None
        if fail:
            err = _clean_model_error(fail)
            if not output:
                output = err
            ok = False

        return CodexTurnResult(
            ok=ok,
            output=output,
            thread_id=new_thread,
            exit_code=int(proc.returncode or 0),
            cmd=cmd,
            error=err if not ok else None,
        )
    except subprocess.TimeoutExpired:
        return CodexTurnResult(
            ok=False,
            output="",
            thread_id=thread_id,
            exit_code=124,
            cmd=[],
            error="codex timeout",
        )
    except FileNotFoundError:
        return CodexTurnResult(
            ok=False,
            output="",
            thread_id=thread_id,
            exit_code=127,
            cmd=[],
            error="codex not found",
        )
    finally:
        if last_msg.is_file():
            last_msg.unlink(missing_ok=True)