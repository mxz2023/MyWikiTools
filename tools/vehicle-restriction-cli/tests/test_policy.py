from datetime import date

from vehicle_restriction.policy import Policy, validate_policy


def test_policy_accepts_valid_tail_rotation_and_matches_active_range():
    policy = validate_policy(
        {
            "city": "beijing",
            "valid_from": "2026-09-28",
            "valid_until": "2026-12-27",
            "weekday_groups": {
                "0": ["5", "0"],
                "1": ["1", "6"],
                "2": ["2", "7"],
                "3": ["3", "8"],
                "4": ["4", "9"],
            },
            "source_url": "https://www.beijing.gov.cn/fuwu/bmfw/bmzt/whts/xxwh/",
            "checked_at": "2026-11-11T00:00:00+00:00",
        }
    )

    assert isinstance(policy, Policy)
    assert policy.is_valid_on(date(2026, 11, 11))
    assert not policy.is_valid_on(date(2026, 12, 28))
    assert policy.restricted_tails_for(date(2026, 11, 11)) == {"2", "7"}


def test_policy_rejects_non_official_source():
    payload = {
        "city": "beijing",
        "valid_from": "2026-09-28",
        "valid_until": "2026-12-27",
        "weekday_groups": {str(day): ["2", "7"] for day in range(5)},
        "source_url": "https://example.com/rules",
        "checked_at": "2026-11-11T00:00:00+00:00",
    }

    try:
        validate_policy(payload)
    except ValueError as exc:
        assert "official" in str(exc).lower() or "source" in str(exc).lower()
    else:
        raise AssertionError("non-official source must not be accepted")


def test_policy_rejects_an_official_url_from_the_wrong_city():
    payload = {
        "city": "tianjin",
        "valid_from": "2026-01-01",
        "valid_until": "2026-12-31",
        "weekday_groups": {str(day): ["7"] for day in range(5)},
        "source_url": "https://jtgl.beijing.gov.cn/jgj/lszt/659722/660341/",
        "checked_at": "2026-11-11T00:00:00+00:00",
    }
    try:
        validate_policy(payload)
    except ValueError as exc:
        assert "tianjin" in str(exc).lower() or "source" in str(exc).lower()
    else:
        raise AssertionError("Tianjin policy must not cite a Beijing government URL")
