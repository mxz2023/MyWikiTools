from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .policy import Policy, validate_policy
from .schedule import add_months, today_shanghai

BEIJING_INDEX = "https://jtgl.beijing.gov.cn/jgj/lszt/659722/660341/"
TIANJIN_LAST_KNOWN = "https://www.tj.gov.cn/sy/zwdt/bmdt/202503/t20250325_6891873.html"


@dataclass(frozen=True)
class SourceResult:
    policy: Policy | None
    status: str
    detail: str = ""


def fetch_text(url: str, timeout: int = 15) -> str:
    from .policy import _is_official_url

    if not _is_official_url(url):
        raise ValueError("refusing to request a non-official source URL")
    request = Request(url, headers={"User-Agent": "vehicle-restriction-cli/0.1 (+official-source-check)"})
    with urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        if not _is_official_url(final_url):
            raise ValueError("official source redirected to a non-official host")
        return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.links.append(("".join(self._text).strip(), self._href))
            self._href = None
            self._text = []


class _VisibleText(HTMLParser):
    """提取官方 HTML 正文文字，忽略脚本与样式，并保留表格/段落边界。"""

    BLOCKS = {"p", "div", "tr", "td", "th", "li", "br", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        elif not self._skip and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        elif not self._skip and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def _visible_text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    return parser.text()


def parse_beijing_policies(text_or_html: str, source_url: str, checked: datetime) -> list[Policy]:
    """从北京官方年度通告或限行表格中提取每段日期及周一至周五尾号组。"""
    import re

    text = _visible_text(text_or_html)
    date_pattern = re.compile(
        r"(?:自\s*)?(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日\s*至\s*"
        r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日"
    )
    matches = list(date_pattern.finditer(text))
    policies: list[Policy] = []
    for index, match in enumerate(matches):
        segment_end = matches[index + 1].start() if index + 1 < len(matches) else min(len(text), match.end() + 600)
        segment = text[match.end():segment_end]
        weekday = re.search(
            r"(?:星期一至星期五|周一至周五)[\s\S]{0,120}?(?:尾号|车牌尾号)[\s\S]{0,80}?(?:分别为|为)\s*[:：]?\s*([\s\S]{0,140})",
            segment,
        )
        if not weekday:
            # 通告表格可能先出现“星期一至星期五”，后接尾号组，但省略“尾号”重复表头。
            weekday = re.search(r"(?:星期一至星期五|周一至周五)[\s\S]{0,100}?(?:分别为)\s*[:：]?\s*([\s\S]{0,140})", segment)
        if not weekday:
            continue
        pairs = re.findall(r"([0-9])\s*(?:和|、)\s*([0-9])", weekday.group(1))
        if len(pairs) < 5:
            continue
        y1, m1, d1, y2, m2, d2 = map(int, match.groups())
        try:
            policies.append(validate_policy({
                "city": "beijing",
                "valid_from": date(y1, m1, d1).isoformat(),
                "valid_until": date(y2, m2, d2).isoformat(),
                "weekday_groups": {str(day): list(pair) for day, pair in enumerate(pairs[:5])},
                "source_url": source_url,
                "checked_at": checked.isoformat(),
            }))
        except ValueError:
            continue
    # 年度通告偶尔会在摘要和正文重复同一个周期，按日期去重。
    unique = {(p.valid_from, p.valid_until): p for p in policies}
    return sorted(unique.values(), key=lambda p: p.valid_from)


def _select_beijing_policy(policies: list[Policy], today: date) -> Policy | None:
    active = [policy for policy in policies if policy.is_valid_on(today)]
    future = [policy for policy in policies if policy.valid_from > today]
    if active:
        current = max(active, key=lambda policy: policy.valid_from)
        upcoming = [policy for policy in future if policy.valid_from > current.valid_until]
        if upcoming and today >= add_months(current.valid_until, -1):
            return min(upcoming, key=lambda policy: policy.valid_from)
        return current
    return min(future, key=lambda policy: policy.valid_from) if future else None


def fetch_beijing(fetcher=fetch_text, now: datetime | None = None) -> SourceResult:
    checked = now or datetime.now(timezone.utc)
    index_html = fetcher(BEIJING_INDEX)
    policies = parse_beijing_policies(index_html, BEIJING_INDEX, checked)
    local_day = today_shanghai(checked)
    if policies:
        policy = _select_beijing_policy(policies, local_day)
        if policy:
            return SourceResult(policy, "published")

    # 交管局专题页链接至政府年度通告；从官方链接发现正文，正文含多个轮换周期。
    links = LinkCollector()
    links.feed(index_html)
    candidates = [(label, href) for label, href in links.links if "限行" in label or "机动车" in label]
    from .policy import _is_official_url

    for _, href in candidates[:8]:
        detail_url = urljoin(BEIJING_INDEX, href)
        if not _is_official_url(detail_url, "beijing"):
            continue
        try:
            page = fetcher(detail_url)
            policies = parse_beijing_policies(page, detail_url, checked)
            policy = _select_beijing_policy(policies, local_day)
            if policy:
                return SourceResult(policy, "published")
        except (OSError, ValueError):
            continue
    return SourceResult(None, "unconfirmed", "未能从北京官方通告解析到当前或下一有效轮换周期")


def fetch_tianjin(fetcher=fetch_text, now: datetime | None = None) -> SourceResult:
    """旧通告已经过期，未找到现行天津官方入口前安全地返回无法确认。"""
    checked = now or datetime.now(timezone.utc)
    html = fetcher(TIANJIN_LAST_KNOWN)
    import re
    period = re.search(r"自\s*(20\d{4})年?(\d{1,2})月(\d{1,2})日?至\s*(20\d{4})年?(\d{1,2})月(\d{1,2})日", html)
    if "2026年3月29日" in html or "2026-03-29" in html:
        return SourceResult(None, "unconfirmed", "天津最后已知官方通告有效至2026-03-29，现行政策无法确认")
    if period:
        return SourceResult(None, "unconfirmed", "仅找到历史天津政策，现行政策无法确认")
    return SourceResult(None, "unconfirmed", "未能核实天津现行官方政策")
