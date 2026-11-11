from datetime import datetime, timezone

from vehicle_restriction.sources import (
    BEIJING_INDEX,
    fetch_beijing,
    fetch_tianjin,
    fetch_text,
    parse_beijing_policies,
)

CHECKED = datetime(2026, 11, 11, tzinfo=timezone.utc)


def test_tianjin_expired_notice_never_becomes_current_policy():
    html = "<html>自2025年3月31日至2026年3月29日，我市继续实施机动车限行交通管理措施</html>"
    result = fetch_tianjin(lambda _: html, CHECKED)
    assert result.policy is None
    assert result.status == "unconfirmed"
    assert "2026-03-29" in result.detail


def annual_notice_html():
    return """
    <html><body><main>
      <p>自2026年3月30日至2026年6月28日，星期一至星期五限行机动车车牌尾号分别为：2和7、3和8、4和9、5和0、1和6。</p>
      <p>自2026年6月29日至2026年9月27日，星期一至星期五限行机动车车牌尾号分别为：1和6、2和7、3和8、4和9、5和0。</p>
      <p>自2026年9月28日至2026年12月27日，星期一至星期五限行机动车车牌尾号分别为：5和0、1和6、2和7、3和8、4和9。</p>
      <p>自2026年12月28日至2027年3月28日，星期一至星期五限行机动车车牌尾号分别为：4和9、5和0、1和6、2和7、3和8。</p>
    </main></body></html>
    """


def test_beijing_parser_extracts_current_and_upcoming_cycle_from_policy_body():
    policies = parse_beijing_policies(
        annual_notice_html(),
        "https://www.beijing.gov.cn/zhengce/zhengcefagui/202603/t20260323_4564097.html",
        CHECKED,
    )
    assert [(p.valid_from.isoformat(), p.valid_until.isoformat()) for p in policies] == [
        ("2026-03-30", "2026-06-28"),
        ("2026-06-29", "2026-09-27"),
        ("2026-09-28", "2026-12-27"),
        ("2026-12-28", "2027-03-28"),
    ]
    current = next(p for p in policies if p.is_valid_on(CHECKED.date()))
    upcoming = next(p for p in policies if p.valid_from > CHECKED.date())
    assert current.weekday_groups[2] == frozenset({"2", "7"})
    assert upcoming.weekday_groups[0] == frozenset({"4", "9"})


def test_fetch_beijing_uses_shanghai_date_at_utc_midnight_boundary():
    page = """<p>自2026年10月1日至2026年11月10日，星期一至星期五限行机动车车牌尾号分别为：1和6、2和7、3和8、4和9、5和0。</p>
    <p>自2026年11月11日至2027年2月28日，星期一至星期五限行机动车车牌尾号分别为：5和0、1和6、2和7、3和8、4和9。</p>"""
    utc_just_before_midnight = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)
    result = fetch_beijing(lambda _: page, utc_just_before_midnight)
    assert result.status == "published"
    assert result.policy.valid_from.isoformat() == "2026-11-11"


def test_fetch_beijing_follows_official_link_and_selects_current_or_next_by_date():
    pages = {
        BEIJING_INDEX: '<a href="https://www.beijing.gov.cn/zhengce/zhengcefagui/202603/t20260323_4564097.html">北京市人民政府关于实施工作日高峰时段区域限行交通管理措施的通告</a>',
        "https://www.beijing.gov.cn/zhengce/zhengcefagui/202603/t20260323_4564097.html": annual_notice_html(),
    }
    fetcher = lambda url: pages[url]

    current_result = fetch_beijing(fetcher, CHECKED)
    upcoming_result = fetch_beijing(fetcher, datetime(2026, 11, 27, tzinfo=timezone.utc))

    assert current_result.status == "published"
    assert current_result.policy.valid_from.isoformat() == "2026-09-28"
    assert current_result.policy.source_url.endswith("t20260323_4564097.html")
    assert upcoming_result.status == "published"
    assert upcoming_result.policy.valid_from.isoformat() == "2026-12-28"


def test_beijing_fetch_does_not_call_fetcher_for_external_candidate():
    requested = []
    index_with_external_link = '<a href="https://outside.example/vehicle">机动车限行政策</a>'

    result = fetch_beijing(lambda url: requested.append(url) or index_with_external_link, CHECKED)

    assert requested == [BEIJING_INDEX]
    assert result.status == "unconfirmed"


def test_fetch_text_rejects_external_url_before_opening(monkeypatch):
    import pytest
    import vehicle_restriction.sources as sources

    opened = []
    monkeypatch.setattr(sources, "urlopen", lambda *args, **kwargs: opened.append(args[0]))
    with pytest.raises(ValueError, match="before|refusing"):
        fetch_text("https://outside.example/vehicle")
    assert opened == []
