from feishu_notify.harnesses.cursor import build_cursor_argv


def test_build_cursor_argv():
    argv = build_cursor_argv(prompt="hi", workspace=__import__("pathlib").Path("/tmp/ws"))
    assert argv[-1] == "hi"
    assert argv[-2] == "/tmp/ws"
    assert "agent" in argv