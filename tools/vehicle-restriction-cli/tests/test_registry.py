from datetime import date, datetime, timezone

from vehicle_restriction.policy import validate_policy
from vehicle_restriction.registry import CITY_REGISTRY, CityConfig, get_provider
from vehicle_restriction.service import refresh_city
from vehicle_restriction.sources import SourceResult


def test_new_city_can_be_added_by_registry_entry_and_adapter(monkeypatch):
    import vehicle_restriction.sources as sources

    monkeypatch.setitem(CITY_REGISTRY, "testcity", CityConfig(("test.gov",), "fetch_testcity"))
    monkeypatch.setattr(
        sources,
        "fetch_testcity",
        lambda: SourceResult(None, "unconfirmed", "fixture adapter"),
        raising=False,
    )
    provider = get_provider("testcity")
    assert provider().detail == "fixture adapter"

    policy = validate_policy({
        "city": "testcity",
        "valid_from": "2026-01-01",
        "valid_until": "2026-12-31",
        "weekday_groups": {str(day): ["7"] for day in range(5)},
        "source_url": "https://traffic.test.gov/policy",
        "checked_at": datetime(2026, 11, 11, tzinfo=timezone.utc).isoformat(),
    })
    state = {"policies": {"testcity": policy.to_dict()}, "checks": {}}
    result = refresh_city(state, "testcity", date(2026, 11, 30), providers={"testcity": provider})
    assert result == "unconfirmed"
