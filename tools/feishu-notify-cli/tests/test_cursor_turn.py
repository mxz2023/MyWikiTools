from feishu_notify.harnesses.cursor.turn import _parse_final_result, _parse_session_id_from_ndjson


def test_parse_session_from_init():
    text = (
        '{"type":"system","subtype":"init","session_id":"sess-1"}\n'
        '{"type":"result","subtype":"success","result":"ok","session_id":"sess-1"}\n'
    )
    assert _parse_session_id_from_ndjson(text) == "sess-1"
    out, ok = _parse_final_result(text)
    assert ok
    assert out == "ok"