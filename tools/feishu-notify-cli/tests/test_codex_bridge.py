from pathlib import Path

from feishu_notify.codex_bridge import (
    _parse_thread_id_from_jsonl,
    _parse_agent_text_from_jsonl,
    build_codex_argv,
    resolve_codex_executable,
)
from feishu_notify.codex_sessions import clear_thread, get_thread_id, put_thread_id, session_key


def test_parse_thread_started():
    raw = '{"type":"thread.started","thread_id":"01a2132b-55bb-73c1-a04c-a364c838e58c"}\n'
    assert _parse_thread_id_from_jsonl(raw) == "01a2132b-55bb-73c1-a04c-a364c838e58c"


def test_parse_agent_message():
    raw = (
        '{"type":"item.completed","item":{"id":"1","type":"agent_message",'
        '"text":"hello from codex"}}\n'
    )
    assert _parse_agent_text_from_jsonl(raw) == "hello from codex"


def test_codex_session_store(tmp_path: Path):
    store = tmp_path / "codex_sessions.json"
    key = session_key("oc_test")
    put_thread_id(key, "01a-uuid", store_path=store)
    assert get_thread_id(key, store_path=store) == "01a-uuid"
    assert clear_thread(key, store_path=store)
    assert get_thread_id(key, store_path=store) is None


def test_resolve_codex_executable_override(tmp_path: Path):
    exe = tmp_path / "codex"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(0o755)
    cfg = {"bridge": {"codex": {"executable": str(exe)}}}
    assert resolve_codex_executable(cfg) == str(exe)


def test_build_codex_resume_argv(tmp_path: Path):
    cfg = {"bridge": {"codex": {"skip_git_repo_check": True, "approve_for_me": True}}}
    last = tmp_path / "out.txt"
    cmd = build_codex_argv(
        prompt="next",
        workspace=Path("/w"),
        thread_id="01a-old",
        cfg=cfg,
        last_msg=last,
    )
    assert "resume" in cmd
    assert "01a-old" in cmd
    assert "next" in cmd
    assert "-o" in cmd
    assert "-C" not in cmd
    assert cmd.index("resume") < cmd.index("01a-old") < cmd.index("next")