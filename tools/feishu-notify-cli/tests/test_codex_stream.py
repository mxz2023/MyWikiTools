from feishu_notify.codex_stream import CodexActivityFeed, describe_codex_event


def test_turn_started():
    assert describe_codex_event({"type": "turn.started"}) == "▶️ 开始推理"


def test_agent_message_commentary():
    line = describe_codex_event(
        {
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": "我先查一下天气",
                "phase": "commentary",
            },
        }
    )
    assert line and "💭" in line


def test_extension_web_search():
    line = describe_codex_event(
        {
            "type": "item.completed",
            "item": {
                "type": "Extension",
                "kind": "web.search",
                "action": {"query": "北京天气"},
            },
        }
    )
    assert line and "搜索" in line


def test_feed_skips_duplicate():
    feed = CodexActivityFeed(max_lines=5)
    feed.push("a")
    feed.push("a")
    assert len(feed.lines) == 1


def test_feed_consumes_jsonl():
    feed = CodexActivityFeed()
    feed.consume_jsonl('{"type":"turn.started"}')
    assert feed.step_count >= 1