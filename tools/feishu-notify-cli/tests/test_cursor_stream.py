from feishu_notify.harnesses.cursor import CursorActivityFeed, describe_cursor_event


def test_cursor_init_event():
    line = (
        '{"type":"system","subtype":"init","session_id":"abc-123",'
        '"model":"gpt-5","cwd":"/tmp"}'
    )
    desc = describe_cursor_event(__import__("json").loads(line))
    assert desc and "gpt-5" in desc


def test_cursor_result_parser():
    feed = CursorActivityFeed()
    feed.consume_jsonl(
        '{"type":"result","subtype":"success","is_error":false,'
        '"result":"hello from cursor","session_id":"x"}'
    )
    assert feed.step_count >= 1