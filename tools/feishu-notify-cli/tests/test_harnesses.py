from feishu_notify.harnesses.cursor import build_cursor_argv


def test_build_cursor_argv():
    argv = build_cursor_argv(prompt="hi", workspace=__import__("pathlib").Path("/tmp/ws"))
    assert argv[-1] == "hi"
    assert "--workspace" in argv
    assert "agent" in argv
    assert "--output-format" in argv