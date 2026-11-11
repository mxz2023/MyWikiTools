from datetime import date, datetime, timezone

from vehicle_restriction.policy import validate_policy
from vehicle_restriction.schedule import add_months, check_due, record_unpublished, today_shanghai
from vehicle_restriction.service import refresh_city, reminder
from vehicle_restriction.sources import SourceResult
from vehicle_restriction.storage import load_state, save_state


def sample_policy(city="beijing", end="2026-12-27", start="2026-09-28"):
    return validate_policy({
        "city": city, "valid_from": start, "valid_until": end,
        "weekday_groups": {str(i): [str(i), str(i + 5)] for i in range(5)},
        "source_url": ("https://www.tj.gov.cn/" if city == "tianjin" else "https://jtgl.beijing.gov.cn/jgj/lszt/659722/660341/"),
        "checked_at": datetime(2026, 11, 11, tzinfo=timezone.utc).isoformat(),
    })


def test_atomic_state_round_trip(tmp_path):
    path = tmp_path / "state.json"
    policy = sample_policy()
    state = {"policies": {"beijing": policy.to_dict()}, "checks": {}}
    save_state(path, state)
    assert load_state(path)["policies"]["beijing"]["valid_until"] == "2026-12-27"
    assert not list(tmp_path.glob("*.tmp"))


def test_refresh_due_one_month_before_end_and_retry_capped_at_three_days():
    policy = sample_policy(end="2026-12-27")
    assert add_months(policy.valid_until, -1) == date(2026, 11, 27)
    assert not check_due(policy, {}, date(2026, 11, 26))
    assert check_due(policy, {}, date(2026, 11, 27))
    state = record_unpublished(policy, {}, date(2026, 11, 27))
    assert state["next_check_date"] == "2026-12-04"
    state = record_unpublished(policy, {"next_check_date": "2026-12-18"}, date(2026, 12, 18))
    assert state["next_check_date"] == "2026-12-24"
    final_state = record_unpublished(policy, state, date(2026, 12, 24))
    assert final_state["final_check_done"] is True
    assert final_state["phase"] == "expiry_day_check"
    assert final_state["next_check_date"] == "2026-12-27"
    assert not check_due(policy, final_state, date(2026, 12, 25))
    assert check_due(policy, final_state, date(2026, 12, 27))

    expired_retry = record_unpublished(policy, final_state, date(2026, 12, 27))
    assert expired_retry["phase"] == "expired_weekly_retry"
    assert expired_retry["next_check_date"] == "2027-01-03"
    assert not check_due(policy, expired_retry, date(2027, 1, 2))
    assert check_due(policy, expired_retry, date(2027, 1, 3))

    next_retry = record_unpublished(policy, expired_retry, date(2027, 1, 3))
    assert next_retry["next_check_date"] == "2027-01-10"
    assert not check_due(policy, next_retry, date(2027, 1, 4))
    assert check_due(policy, next_retry, date(2027, 1, 10))


def test_reminder_is_offline_and_expired_or_absent_policy_is_unconfirmed():
    missing = reminder({"policies": {}, "checks": {}}, "tianjin", "7", date(2026, 11, 11))
    assert missing["status"] == "unconfirmed"
    assert missing["tail_rotation_match"] is None
    assert missing["travel_status"] == "unknown"
    expired = sample_policy(city="tianjin", start="2025-03-31", end="2026-03-29").to_dict()
    assert reminder({"policies": {"tianjin": expired}}, "tianjin", "7", date(2026, 11, 11))["status"] == "unconfirmed"


def test_initial_failure_waits_seven_days_before_retry():
    from vehicle_restriction.schedule import check_due

    assert check_due(None, {}, date(2026, 11, 11))
    retry = {"next_check_date": "2026-11-18"}
    assert not check_due(None, retry, date(2026, 11, 17))
    assert check_due(None, retry, date(2026, 11, 18))


def test_reminder_uses_upcoming_policy_only_when_its_effective_date_arrives():
    current = sample_policy(start="2026-09-28", end="2026-12-27").to_dict()
    upcoming = sample_policy(start="2026-12-28", end="2027-03-28").to_dict()
    state = {"policies": {"beijing": current}, "upcoming_policies": {"beijing": upcoming}}
    current_result = reminder(state, "beijing", "7", date(2026, 11, 11))
    next_result = reminder(state, "beijing", "7", date(2026, 12, 28))
    assert current_result["policy_status"] == next_result["policy_status"] == "confirmed"
    assert current_result["tail_rotation_match"] is True
    assert next_result["tail_rotation_match"] is False
    assert current_result["status"] == "unconfirmed"
    assert current_result["travel_status"] == "unknown"
    assert "不能据此判断可否通行" in current_result["applicability_note"]
    assert "restricted" not in current_result


def test_reminder_does_not_assume_weekend_is_in_rotation_schedule():
    policy = sample_policy().to_dict()
    state = {"policies": {"beijing": policy}, "checks": {}}
    result = reminder(state, "beijing", "7", date(2026, 11, 14))
    assert result["tail_rotation_match"] is None
    assert result["travel_status"] == "unknown"
    assert result["status"] == "unconfirmed"


def test_shanghai_date_crosses_utc_day_boundary():
    utc = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)
    assert utc.date() == date(2026, 11, 10)
    assert today_shanghai(utc) == date(2026, 11, 11)


def test_refresh_current_policy_clears_stale_upcoming_policy():
    current = sample_policy(start="2026-09-28", end="2026-12-27")
    stale_upcoming = sample_policy(start="2026-12-28", end="2027-03-28")
    state = {
        "policies": {"beijing": current.to_dict()},
        "upcoming_policies": {"beijing": stale_upcoming.to_dict()},
        "checks": {"beijing": {"next_check_date": "2026-11-27"}},
    }
    provider = lambda: SourceResult(current, "published")

    result = refresh_city(state, "beijing", date(2026, 11, 27), providers={"beijing": provider})

    assert result == "published"
    assert "beijing" not in state["upcoming_policies"]


def test_refresh_new_future_policy_replaces_old_upcoming_cache():
    current = sample_policy(start="2026-09-28", end="2026-12-27")
    old_upcoming = sample_policy(start="2026-12-28", end="2027-03-28")
    revised_upcoming = sample_policy(start="2026-12-28", end="2027-03-31")
    state = {
        "policies": {"beijing": current.to_dict()},
        "upcoming_policies": {"beijing": old_upcoming.to_dict()},
        "checks": {"beijing": {"next_check_date": "2026-11-27"}},
    }
    provider = lambda: SourceResult(revised_upcoming, "published")

    result = refresh_city(state, "beijing", date(2026, 11, 27), providers={"beijing": provider})

    assert result == "published"
    assert state["upcoming_policies"]["beijing"]["valid_until"] == "2027-03-31"
