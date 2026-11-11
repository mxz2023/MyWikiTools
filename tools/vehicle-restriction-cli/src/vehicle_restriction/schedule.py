from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


def today_shanghai(now: datetime | None = None) -> date:
    """当前或给定时刻对应的 Asia/Shanghai 自然日。"""
    if now is None:
        return datetime.now(SHANGHAI).date()
    if now.tzinfo is None:
        now = now.replace(tzinfo=SHANGHAI)
    return now.astimezone(SHANGHAI).date()


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    final_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, final_day))


def initial_check_due(policy, today: date) -> bool:
    return policy is None


def check_due(policy, check_state: dict | None, today: date) -> bool:
    """首次立即检查；一月前周查，T-3后到期日复查，到期后每7天重试。"""
    check_state = check_state or {}
    next_check = check_state.get("next_check_date")
    # 兼容旧状态：旧版 T-3 检查将 final_check_done 置真但没有正确的到期日计划。
    if policy and check_state.get("final_check_done") and not check_state.get("phase"):
        return today >= policy.valid_until
    if next_check:
        return today >= date.fromisoformat(next_check)
    if policy is None:
        return True
    return today >= add_months(policy.valid_until, -1)


def record_unpublished(policy, check_state: dict | None, checked_on: date) -> dict:
    """记载失败刷新：T-3 后安排到期日复查，到期仍无新政策则按周重试。"""
    check_state = dict(check_state or {})
    first_check = add_months(policy.valid_until, -1)
    final_pre_expiry_check = policy.valid_until - timedelta(days=3)
    previous = date.fromisoformat(check_state["next_check_date"]) if check_state.get("next_check_date") else first_check

    if checked_on >= policy.valid_until:
        next_check = checked_on + timedelta(days=7)
        phase = "expired_weekly_retry"
        final_check_done = True
    elif checked_on >= final_pre_expiry_check:
        next_check = policy.valid_until
        phase = "expiry_day_check"
        final_check_done = True
    else:
        candidate = max(checked_on, previous) + timedelta(days=7)
        next_check = min(candidate, final_pre_expiry_check)
        phase = "pre_expiry_weekly_retry"
        final_check_done = False

    check_state.update({
        "next_check_date": next_check.isoformat(),
        "last_result": "unpublished",
        "last_checked": checked_on.isoformat(),
        "final_check_done": final_check_done,
        "phase": phase,
    })
    return check_state


def record_published(check_state: dict | None, checked_on: date) -> dict:
    return {"next_check_date": None, "last_result": "published", "last_checked": checked_on.isoformat(), "phase": "published"}
