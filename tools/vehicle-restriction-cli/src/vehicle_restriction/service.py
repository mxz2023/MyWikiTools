from __future__ import annotations

from datetime import date

from .schedule import check_due, record_published, record_unpublished
from .registry import get_provider
from .storage import get_policy, get_schedule_policy


def refresh_city(state: dict, city: str, today: date, providers=None) -> str:
    providers = providers or {}
    current = get_schedule_policy(state, city)
    check_state = state.setdefault("checks", {}).get(city, {})
    if not check_due(current, check_state, today):
        return "not_due"
    try:
        provider = providers.get(city) or get_provider(city)
        result = provider()
    except Exception as exc:
        result = None
        detail = str(exc)
    else:
        detail = result.detail
    if result and result.policy:
        if result.policy.city != city:
            raise ValueError(f"provider returned mismatched city policy: {result.policy.city}")
        if result.policy.valid_from <= today:
            state.setdefault("policies", {})[city] = result.policy.to_dict()
            # 官网返回现行周期即视为当前政策集的权威快照；旧的待生效缓存可能已被撤回或调整。
            state.setdefault("upcoming_policies", {}).pop(city, None)
        else:
            state.setdefault("upcoming_policies", {})[city] = result.policy.to_dict()
        next_known = get_schedule_policy(state, city)
        next_check = __import__("vehicle_restriction.schedule", fromlist=["add_months"]).add_months(next_known.valid_until, -1)
        state["checks"][city] = {"next_check_date": next_check.isoformat(), "last_result": "published", "last_checked": today.isoformat()}
        return "published"
    if current:
        state["checks"][city] = record_unpublished(current, check_state, today)
    else:
        # 首次抓取未能确认时，一周后重试；尚无有效期时不伪造退出期限。
        from datetime import timedelta
        state.setdefault("checks", {})[city] = {
            "next_check_date": (today + timedelta(days=7)).isoformat(),
            "last_result": "unconfirmed", "last_checked": today.isoformat(), "detail": detail,
        }
    return "unconfirmed"


def reminder(state: dict, city: str, tail: str, today: date) -> dict:
    """离线查询尾号轮换组；不将轮换匹配解释为实际通行结论。"""
    policy = get_policy(state, city, today)
    base = {
        "city": city,
        "date": today.isoformat(),
        "tail": tail,
        "travel_status": "unknown",
        "applicability_status": "unconfirmed",
        "applicability_note": (
            "仅核对普通周一至周五尾号轮换组；未核验当日是否适用、节假日或调休安排、"
            "车辆/号牌类别、实际区域与时段及临时交通措施，不能据此判断可否通行。"
        ),
    }
    if not policy:
        return {
            **base,
            "status": "unconfirmed",
            "policy_status": "unconfirmed",
            "tail_rotation_match": None,
            "reason": "该日期没有已确认有效的本地政策。",
        }

    group = policy.rotation_group_for(today)
    if group is None:
        return {
            **base,
            "status": "unconfirmed",
            "policy_status": "confirmed",
            "tail_rotation_match": None,
            "rotation_group": None,
            "source_url": policy.source_url,
            "reason": "该日期不在普通周一至周五轮换表内；是否因节假日或调休适用需另行核实。",
        }

    return {
        **base,
        "status": "unconfirmed",
        "policy_status": "confirmed",
        "tail_rotation_match": tail in group,
        "rotation_group": sorted(group),
        "source_url": policy.source_url,
        "reason": "仅表示尾号与普通工作日轮换组是否匹配；不表示车辆实际受限或可通行。",
    }
