from feishu_notify.bridge.progress import FeishuCodexProgress


def test_ack_title_includes_prompt():
    p = FeishuCodexProgress(run_id="r1", harness="codex", prompt="晚上好，有什么推荐吃的", cfg={})
    assert p._ack_title() == "已收到「晚上好，有什么推荐吃的」"


def test_finish_keeps_ack_title_and_footer():
    p = FeishuCodexProgress(run_id="r1", harness="codex", prompt="准备睡觉", cfg={})
    p.finish(ok=True, reply="晚安，放下手机，好好休息。")
    assert p._footer_md == "晚安，放下手机，好好休息。"
    assert p._ack_title() == "已收到「准备睡觉」"