from pathlib import Path

from feishu_notify.bridge.dispatch import (
    build_harness_argv,
    event_to_prompt,
    make_run_id,
    run_dispatch,
)


def test_event_to_prompt_text():
    assert event_to_prompt("im.message.receive_v1", {"content": "  hello  "}) == "hello"


def test_build_harness_cursor():
    cfg = {"bridge": {"workspace": "/tmp"}}
    cmd = build_harness_argv(
        "cursor",
        prompt="do x",
        workspace=Path("/tmp/ws"),
        run_id="r1",
        message_id="om_1",
        cfg=cfg,
    )
    assert "agent" in cmd
    assert cmd[-1] == "do x"
    assert "--workspace" in cmd
    assert "--output-format" in cmd


def test_build_harness_codex(tmp_path):
    cfg = {"bridge": {"codex": {"approve_for_me": True}}}
    cmd = build_harness_argv(
        "codex",
        prompt="fix tests",
        workspace=Path("/repo"),
        run_id="r1",
        message_id="om_1",
        cfg=cfg,
        chat_id="oc_chat",
    )
    assert cmd[0].endswith("codex")
    assert "-C" in cmd
    assert "fix tests" in cmd


def test_custom_harness_from_config():
    cfg = {
        "bridge": {
            "harnesses": {
                "deepseek": {"argv": ["fake-deepseek", "run", "{prompt}"]},
            },
        },
    }
    cmd = build_harness_argv(
        "deepseek",
        prompt="ping",
        workspace=Path("/w"),
        run_id="r1",
        message_id="om_1",
        cfg=cfg,
    )
    assert cmd == ["fake-deepseek", "run", "ping"]


def test_dispatch_dry_run():
    result = run_dispatch(
        "im.message.receive_v1",
        {"content": "hi", "message_id": "om_x"},
        harness="shell",
        workspace=Path("."),
        timeout_sec=30,
        notify=False,
        dry_run=True,
    )
    assert result.ok
    assert result.cmd[0] == "sh"
    assert result.run_id == make_run_id({"message_id": "om_x"})