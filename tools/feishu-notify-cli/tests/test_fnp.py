import json
from pathlib import Path

import pytest

from feishu_notify.fnp import FnpValidationError, validate_envelope
from feishu_notify.pipeline import process_send
from feishu_notify.render import render_message
from feishu_notify.policy import resolve_format
from feishu_notify.runs import RunBinding, put_binding
from feishu_notify.scenes import list_scenes, load_manifest


def test_list_scenes_has_twelve():
    scenes = list_scenes()
    assert len(scenes) == 12
    ids = {s["id"] for s in scenes}
    assert "agent.progress" in ids
    assert next(s for s in scenes if s["id"] == "agent.progress")["default_format"] == "card"


def test_validate_envelope_minimal():
    raw = {
        "fnp_version": 1,
        "scene": "agent.conclusion",
        "payload": {"title": "T", "summary": "Done"},
    }
    env = validate_envelope(raw)
    assert env["scene"] == "agent.conclusion"


def test_progress_defaults_to_card():
    manifest = load_manifest("agent.progress")
    env = validate_envelope(
        {
            "fnp_version": 1,
            "scene": "agent.progress",
            "format": "auto",
            "payload": {"title": "Run", "summary": "50%"},
        }
    )
    assert resolve_format(env, manifest) == "card"


def test_render_conclusion_card():
    env = validate_envelope(
        {
            "fnp_version": 1,
            "scene": "agent.conclusion",
            "format": "card",
            "payload": {
                "title": "OK",
                "summary": "Finished",
                "fields": [{"label": "耗时", "value": "1m"}],
            },
        }
    )
    out = render_message(env, "card")
    assert out["format"] == "card"
    assert out["card"]["schema"] == "2.0"
    assert out["card"]["header"]["template"] == "green"


def test_notify_plain_no_duplicate_title():
    env = validate_envelope(
        {
            "fnp_version": 1,
            "scene": "notify.plain",
            "format": "text",
            "payload": {"summary": "only one line"},
        }
    )
    from feishu_notify.render import render_message

    out = render_message(env, "text")
    assert out["markdown"].count("only one line") == 1


def test_notify_plain_default_card():
    manifest = load_manifest("notify.plain")
    env = validate_envelope(
        {
            "fnp_version": 1,
            "scene": "notify.plain",
            "payload": {"summary": "卡片正文"},
        }
    )
    assert resolve_format(env, manifest) == "card"
    from feishu_notify.render import render_message

    out = render_message(env, "card")
    assert out["card"]["schema"] == "2.0"
    body = out["card"]["body"]["elements"][0]["content"]
    assert body == "卡片正文"
    assert out["card"]["header"]["title"]["content"] == "通知"


def test_send_dry_run():
    body = process_send(
        {
            "fnp_version": 1,
            "scene": "notify.plain",
            "payload": {"summary": "ping"},
        },
        dry_run=True,
    )
    assert body["dry_run"] is True
    assert "lark_command" in body


def test_m2_second_progress_uses_patch(tmp_path: Path):
    store = tmp_path / "runs.json"
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "progress:\n  mode: m2\n  require_run_id: true\n",
        encoding="utf-8",
    )
    put_binding(
        RunBinding(
            run_id="run-1",
            message_id="om_test_binding",
            identity="bot",
            route="dm_self",
            scene="agent.progress",
            updated_at="",
        ),
        store_path=store,
    )
    body = process_send(
        {
            "fnp_version": 1,
            "scene": "agent.progress",
            "context": {"run_id": "run-1"},
            "payload": {"title": "T", "summary": "7/10"},
        },
        dry_run=True,
        config_path=cfg,
        store_path=store,
    )
    assert body["delivery_op"] == "patch"
    assert "patch" in body["lark_command"]


def test_progress_requires_run_id_when_m2(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "progress:\n  mode: m2\n  require_run_id: true\n",
        encoding="utf-8",
    )
    with pytest.raises(FnpValidationError, match="run_id"):
        process_send(
            {
                "fnp_version": 1,
                "scene": "agent.progress",
                "payload": {"title": "T", "summary": "x"},
            },
            dry_run=True,
            config_path=cfg,
        )


def test_missing_summary_raises():
    env = validate_envelope(
        {"fnp_version": 1, "scene": "agent.conclusion", "payload": {"title": "x"}}
    )
    manifest = load_manifest("agent.conclusion")
    with pytest.raises(FnpValidationError):
        from feishu_notify.fnp import validate_payload_for_scene

        validate_payload_for_scene(manifest, env["payload"])