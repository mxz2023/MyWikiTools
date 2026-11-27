from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import Any, TextIO

from feishu_notify.config import load_config

DEFAULT_EVENTS = ("im.message.receive_v1",)
ALL_INBOUND_EVENTS = ("im.message.receive_v1", "card.action.trigger")

EXIT_LISTEN = 7


@dataclass
class ListenResult:
    ok: bool
    event_keys: list[str]
    events_received: int
    reason: str
    log_file: str | None
    duration_sec: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "event_keys": self.event_keys,
            "events_received": self.events_received,
            "reason": self.reason,
            "log_file": self.log_file,
            "duration_sec": round(self.duration_sec, 3),
        }


def parse_listen_timeout(raw: str | None) -> tuple[str | None, bool]:
    """Return (lark-cli --timeout value, unlimited)."""
    if raw is None:
        return None, True
    text = raw.strip().lower()
    if text in ("", "0", "none", "off", "unlimited", "forever"):
        return None, True
    return raw.strip(), False


def dm_self_user_id(cfg: dict[str, Any]) -> str | None:
    routes = cfg.get("routes") or {}
    dm = routes.get("dm_self") or {}
    uid = (dm.get("user_id") or "").strip()
    return uid or None


def build_default_jq(
    event_key: str,
    *,
    p2p_only: bool,
    sender_id: str | None,
    include_post: bool,
) -> str | None:
    """Return jq filter for common Bot-DM agent use, or None to pass all events through."""
    if event_key == "card.action.trigger":
        parts: list[str] = []
        if sender_id:
            parts.append(f'.operator_id == "{sender_id}"')
        if not parts:
            return None
        return (
            f"select({' and '.join(parts)}) | "
            "{type, event_id, message_id, chat_id, operator_id, action_tag, action_value}"
        )

    if event_key != "im.message.receive_v1":
        return None

    selects: list[str] = []
    if p2p_only:
        selects.append('.chat_type == "p2p"')
    if include_post:
        selects.append('(.message_type == "text" or .message_type == "post")')
    else:
        selects.append('.message_type == "text"')
    if sender_id:
        selects.append(f'.sender_id == "{sender_id}"')
    cond = " and ".join(selects)
    return (
        f"select({cond}) | {{type, event_id, message_id, chat_id, message_type, sender_id, content}}"
    )


def _default_log_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = Path.home() / ".config" / "fnotify" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"listen-{stamp}.ndjson"


def build_consume_argv(
    event_key: str,
    *,
    identity: str,
    timeout: str | None,
    max_events: int,
    jq: str | None,
) -> list[str]:
    cmd = ["lark-cli", "event", "consume", event_key, "--as", identity]
    if timeout:
        cmd.extend(["--timeout", timeout])
    if max_events and max_events > 0:
        cmd.extend(["--max-events", str(max_events)])
    if jq:
        cmd.extend(["--jq", jq])
    return cmd


def _stream_consumer(
    *,
    event_key: str,
    cmd: list[str],
    log_file: TextIO | None,
    log_meta: bool,
    mirror_stdout: bool,
    mirror_bus: bool,
    counter: list[int],
    lock: threading.Lock,
    procs: list[subprocess.Popen[str]],
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
    dispatch_lock: threading.Lock | None = None,
) -> int:
    """Run one lark-cli consumer; returns process exit code."""
    # lark-cli consume exits when stdin hits EOF; background `nohup` closes stdin.
    # Hold the write end open so the consumer stays up until we stop it.
    keep_r, keep_w = os.pipe()
    proc = subprocess.Popen(
        cmd,
        stdin=keep_r,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    os.close(keep_r)
    setattr(proc, "_fnotify_stdin_keepalive", keep_w)
    procs.append(proc)

    def _stderr_reader() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            line = line.rstrip("\n")
            if log_meta and log_file:
                log_file.write(
                    json.dumps(
                        {"ts": _now_iso(), "stream": "stderr", "event_key": event_key, "line": line},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                log_file.flush()
            if mirror_bus and line:
                print(line, file=sys.stderr)

    threading.Thread(target=_stderr_reader, daemon=True).start()

    assert proc.stdout is not None
    for line in proc.stdout:
        raw = line.rstrip("\n")
        if not raw:
            continue
        with lock:
            counter[0] += 1
        record: dict[str, Any] = {"ts": _now_iso(), "event_key": event_key}
        try:
            record["event"] = json.loads(raw)
        except json.JSONDecodeError:
            record["raw"] = raw
            record["event"] = None
        if on_event and isinstance(record.get("event"), dict):
            if log_file:
                log_file.write(
                    json.dumps(
                        {
                            "ts": _now_iso(),
                            "type": "bridge.dispatch.start",
                            "event_key": event_key,
                            "message_id": record["event"].get("message_id"),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                log_file.flush()
            if dispatch_lock:
                dispatch_lock.acquire(blocking=True)
                try:
                    on_event(event_key, record["event"])
                finally:
                    dispatch_lock.release()
            else:
                on_event(event_key, record["event"])
            if log_file:
                log_file.write(
                    json.dumps(
                        {
                            "ts": _now_iso(),
                            "type": "bridge.dispatch.done",
                            "event_key": event_key,
                            "message_id": record["event"].get("message_id"),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                log_file.flush()
        if log_file:
            log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            log_file.flush()
        if mirror_stdout:
            if log_meta:
                print(json.dumps(record, ensure_ascii=False), flush=True)
            else:
                print(raw, flush=True)

    proc.wait()
    keep_w = getattr(proc, "_fnotify_stdin_keepalive", None)
    if isinstance(keep_w, int):
        try:
            os.close(keep_w)
        except OSError:
            pass
    return int(proc.returncode or 0)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_listen(
    *,
    events: tuple[str, ...] = DEFAULT_EVENTS,
    identity: str = "bot",
    timeout: str | None = "0",
    max_events: int = 0,
    jq: str | None = None,
    p2p_only: bool = True,
    self_only: bool = True,
    include_post: bool = True,
    log: bool = False,
    log_file: Path | None = None,
    log_meta: bool = False,
    mirror_bus: bool = True,
    dry_run: bool = False,
    json_output: bool = False,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
    serial_dispatch: bool = True,
    mirror_stdout: bool | None = None,
) -> ListenResult:
    """Block until timeout/max-events/ctrl-c; wraps lark-cli event consume."""
    cfg = load_config()
    sender = dm_self_user_id(cfg) if self_only else None
    timeout_val, _ = parse_listen_timeout(timeout)

    resolved_log = log_file or (_default_log_path() if log else None)
    plans: list[tuple[str, list[str], str | None]] = []
    for key in events:
        effective_jq = jq if jq else build_default_jq(
            key, p2p_only=p2p_only, sender_id=sender, include_post=include_post
        )
        plans.append((key, build_consume_argv(key, identity=identity, timeout=timeout_val, max_events=max_events, jq=effective_jq), effective_jq))

    if dry_run:
        body = {
            "ok": True,
            "dry_run": True,
            "identity": identity,
            "timeout": timeout_val,
            "max_events": max_events,
            "log_file": str(resolved_log) if resolved_log else None,
            "consumers": [
                {"event_key": k, "jq": jq_expr, "cmd": " ".join(shlex.quote(p) for p in cmd)}
                for k, cmd, jq_expr in plans
            ],
        }
        if json_output:
            print(json.dumps({"status": 200, "headers": {}, "body": body}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(body, ensure_ascii=False, indent=2))
        return ListenResult(
            ok=True,
            event_keys=list(events),
            events_received=0,
            reason="dry_run",
            log_file=str(resolved_log) if resolved_log else None,
            duration_sec=0.0,
        )

    started = time.monotonic()
    counter = [0]
    lock = threading.Lock()
    log_handle: TextIO | None = None
    if resolved_log:
        resolved_log.parent.mkdir(parents=True, exist_ok=True)
        log_handle = resolved_log.open("a", encoding="utf-8")
        log_handle.write(
            json.dumps(
                {
                    "ts": _now_iso(),
                    "type": "listen.start",
                    "event_keys": list(events),
                    "timeout": timeout_val,
                    "max_events": max_events,
                    "identity": identity,
                    "sender_filter": sender,
                    "dispatch": on_event is not None,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        log_handle.flush()

    echo_stdout = (
        mirror_stdout if mirror_stdout is not None else (not json_output and on_event is None)
    )

    exit_codes: list[int] = []
    threads: list[threading.Thread] = []
    procs: list[subprocess.Popen[str]] = []
    reason = "completed"
    dispatch_lock = threading.Lock() if on_event and serial_dispatch else None

    def _run_one(key: str, cmd: list[str]) -> None:
        code = _stream_consumer(
            event_key=key,
            cmd=cmd,
            log_file=log_handle,
            log_meta=log_meta,
            mirror_stdout=echo_stdout,
            mirror_bus=mirror_bus,
            counter=counter,
            lock=lock,
            procs=procs,
            on_event=on_event,
            dispatch_lock=dispatch_lock,
        )
        exit_codes.append(code)

    for key, cmd, _ in plans:
        t = threading.Thread(target=_run_one, args=(key, cmd), daemon=True)
        threads.append(t)
        t.start()

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        reason = "signal"
        for p in procs:
            keep_w = getattr(p, "_fnotify_stdin_keepalive", None)
            if isinstance(keep_w, int):
                try:
                    os.close(keep_w)
                except OSError:
                    pass
            if p.poll() is None:
                p.terminate()
        for t in threads:
            t.join(timeout=5)
    else:
        if max_events and counter[0] >= max_events:
            reason = "limit"
        elif timeout_val:
            reason = "timeout"
        elif any(c != 0 for c in exit_codes):
            reason = "error"
        elif counter[0] == 0:
            reason = "idle"

    duration = time.monotonic() - started
    if log_handle:
        log_handle.write(
            json.dumps(
                {
                    "ts": _now_iso(),
                    "type": "listen.end",
                    "reason": reason,
                    "events_received": counter[0],
                    "exit_codes": exit_codes,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        log_handle.close()

    ok = reason in ("limit", "timeout", "signal", "completed", "idle") and not any(
        c not in (0, None) for c in exit_codes
    )
    return ListenResult(
        ok=ok,
        event_keys=list(events),
        events_received=counter[0],
        reason=reason,
        log_file=str(resolved_log) if resolved_log else None,
        duration_sec=duration,
    )