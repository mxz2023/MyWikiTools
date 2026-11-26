"""Bilingual --help contract (see docs/cli-help-standard.md)."""

from feishu_notify import help_text as ht


def test_root_help_bilingual_blocks():
    text = ht.ROOT_HELP
    assert "Workflow" in text and "流程" in text
    assert "Defaults" in text and "默认" in text
    assert "Exit codes" in text and "退出码" in text
    assert "dm_self" in text
    assert "lark-cli" in text


def test_command_short_strings_bilingual():
    for val in (
        ht.CMD_SEND,
        ht.CMD_LISTEN,
        ht.CMD_DOCTOR,
        ht.GRP_SCENES_DEMO,
        ht.OPT_JSON_OUTPUT,
    ):
        assert " / " in val, val