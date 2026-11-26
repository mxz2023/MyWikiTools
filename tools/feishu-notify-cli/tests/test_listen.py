from feishu_notify.bridge.listen import (
    build_consume_argv,
    build_default_jq,
    parse_listen_timeout,
    run_listen,
)


def test_parse_listen_timeout_unlimited():
    assert parse_listen_timeout("0") == (None, True)
    assert parse_listen_timeout("off") == (None, True)
    assert parse_listen_timeout("30m") == ("30m", False)


def test_build_default_jq_p2p_text():
    jq = build_default_jq(
        "im.message.receive_v1",
        p2p_only=True,
        sender_id="ou_x",
        include_post=False,
    )
    assert jq is not None
    assert "p2p" in jq
    assert "ou_x" in jq
    assert "post" not in jq


def test_build_consume_argv():
    cmd = build_consume_argv(
        "im.message.receive_v1",
        identity="bot",
        timeout="10m",
        max_events=3,
        jq=None,
    )
    assert cmd[:4] == ["lark-cli", "event", "consume", "im.message.receive_v1"]
    assert "--timeout" in cmd and "10m" in cmd
    assert "--max-events" in cmd


def test_listen_dry_run():
    result = run_listen(dry_run=True, timeout="5m", log=True)
    assert result.ok
    assert result.reason == "dry_run"
    assert result.events_received == 0