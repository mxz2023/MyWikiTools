from feishu_notify.bridge_catchup import _has_conclusion_after, _is_ack_only


def test_is_ack_only():
    assert _is_ack_only("##### 已收到\n\n早上好", "早上好")
    assert not _is_ack_only("你好，今天天气不错", "早上好")


def test_has_conclusion_after_ack_only():
    user_id = "ou_u1"
    msgs = [
        {"message_id": "1", "msg_type": "text", "content": "早上好", "sender": {"sender_type": "user", "id": user_id}},
        {"message_id": "2", "msg_type": "post", "content": "##### 已收到\n\n早上好", "sender": {"sender_type": "app", "id": "app"}},
    ]
    assert not _has_conclusion_after(msgs, 0, user_id=user_id, user_content="早上好")


def test_progress_card_not_conclusion():
    user_id = "ou_u1"
    msgs = [
        {"message_id": "1", "msg_type": "text", "content": "下午好", "sender": {"sender_type": "user", "id": user_id}},
        {"message_id": "2", "msg_type": "post", "content": "##### 已收到\n\n下午好", "sender": {"sender_type": "app", "id": "app"}},
        {
            "message_id": "3",
            "msg_type": "interactive",
            "content": '<card title="Codex 工作中">\n**⏳ Codex 处理中',
            "sender": {"sender_type": "app", "id": "app"},
        },
    ]
    assert not _has_conclusion_after(msgs, 0, user_id=user_id, user_content="下午好")


def test_codex_reply_blue_card_not_counted_as_finished():
    user_id = "ou_u1"
    msgs = [
        {"message_id": "1", "msg_type": "text", "content": "晚安", "sender": {"sender_type": "user", "id": user_id}},
        {
            "message_id": "2",
            "msg_type": "interactive",
            "content": '{"header":{"template":"blue","title":{"content":"已收到「晚安」"}}}',
            "sender": {"sender_type": "app", "id": "app"},
        },
    ]
    assert not _has_conclusion_after(msgs, 0, user_id=user_id, user_content="晚安")


def test_codex_reply_red_failure_card_counts_as_handled():
    user_id = "ou_u1"
    msgs = [
        {"message_id": "1", "msg_type": "text", "content": "失败", "sender": {"sender_type": "user", "id": user_id}},
        {
            "message_id": "2",
            "msg_type": "interactive",
            "content": '{"header":{"template":"red","title":{"content":"已收到「失败」"}}}',
            "sender": {"sender_type": "app", "id": "app"},
        },
    ]
    assert _has_conclusion_after(msgs, 0, user_id=user_id, user_content="失败")


def test_codex_reply_finished_card_counts_as_handled():
    user_id = "ou_u1"
    msgs = [
        {"message_id": "1", "msg_type": "text", "content": "晚安", "sender": {"sender_type": "user", "id": user_id}},
        {
            "message_id": "2",
            "msg_type": "interactive",
            "content": '{"header":{"template":"green","title":"已收到「晚安」"}}\n---\n\n好梦',
            "sender": {"sender_type": "app", "id": "app"},
        },
    ]
    assert _has_conclusion_after(msgs, 0, user_id=user_id, user_content="晚安")


def test_has_conclusion_after_real_reply():
    user_id = "ou_u1"
    msgs = [
        {"message_id": "1", "msg_type": "text", "content": "你好", "sender": {"sender_type": "user", "id": user_id}},
        {"message_id": "2", "msg_type": "post", "content": "你好呀", "sender": {"sender_type": "app", "id": "app"}},
    ]
    assert _has_conclusion_after(msgs, 0, user_id=user_id, user_content="你好")