from feishu_notify.lark_bootstrap import needs_lark_app_config


def test_needs_lark_app_config():
    assert needs_lark_app_config("run `lark-cli config init --new`")
    assert needs_lark_app_config("not configured yet")
    assert needs_lark_app_config("malformed config: no apps")
    assert not needs_lark_app_config(None)
    assert not needs_lark_app_config("some random error")