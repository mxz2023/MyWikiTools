"""Ensure bridge/listen --dispatch wires the event callback (regression)."""

import inspect

from feishu_notify import cli


def test_invoke_listen_assigns_on_event_when_dispatch():
    src = inspect.getsource(cli._invoke_listen)
    assert "on_event = _on_event" in src
    assert "is_dispatched" in src