from datetime import date
from pathlib import Path
from types import SimpleNamespace
import importlib.util

import pytest

scheduler_path = Path(__file__).parents[1] / "launchd" / "scheduler.py"
spec = importlib.util.spec_from_file_location("vehicle_restriction_launchd_scheduler", scheduler_path)
scheduler = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(scheduler)
registered_cities = scheduler.registered_cities
city_check_date = scheduler.city_check_date
scheduled_city_check_date = scheduler.scheduled_city_check_date
earliest_check = scheduler.earliest_check


def test_registry_json_includes_future_city(monkeypatch):
    monkeypatch.setattr(
        scheduler.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout='["beijing", "tianjin", "shanghai"]\n', stderr=""
        ),
    )
    assert registered_cities("vehicle-restriction") == ("beijing", "tianjin", "shanghai")


@pytest.mark.parametrize(
    "stdout",
    [
        '{"cities":["beijing"]}',
        "[]",
        '["beijing", "beijing"]',
        '["北京"]',
        '["beijing", 3]',
        "not json",
    ],
)
def test_invalid_city_registry_fails_closed(monkeypatch, stdout):
    monkeypatch.setattr(
        scheduler.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=stdout, stderr=""),
    )
    with pytest.raises(ValueError):
        registered_cities("vehicle-restriction")


def test_city_registry_nonzero_exit_fails_closed(monkeypatch):
    monkeypatch.setattr(
        scheduler.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout="[]", stderr="usage error"),
    )
    with pytest.raises(RuntimeError, match="exited 2"):
        registered_cities("vehicle-restriction")


def test_t_minus_three_check_date_is_not_delayed_by_old_retry_marker():
    state = {
        "policies": {"beijing": {"valid_from": "2026-09-28", "valid_until": "2026-12-27"}},
        "checks": {"beijing": {"next_check_date": "2026-12-24"}},
    }
    assert scheduled_city_check_date(
        state, "beijing", date(2026, 12, 18), date(2026, 12, 25)
    ) == date(2026, 12, 24)


def test_unadvanced_overdue_city_uses_seven_day_retry():
    state = {"checks": {"beijing": {"next_check_date": "2026-11-11"}}}
    assert scheduled_city_check_date(
        state, "beijing", date(2026, 11, 12), date(2026, 11, 18)
    ) == date(2026, 11, 18)


def test_registered_third_city_participates_in_next_date_selection():
    cities = ("beijing", "tianjin", "shanghai")
    state = {
        "checks": {
            "beijing": {"next_check_date": "2026-11-27"},
            "tianjin": {"next_check_date": "2026-12-01"},
            "shanghai": {"next_check_date": "2026-11-18"},
        }
    }
    assert earliest_check(state, date(2026, 11, 12), cities) == date(2026, 11, 18)


def test_refresh_invokes_every_registered_due_city(monkeypatch, tmp_path):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(scheduler.subprocess, "run", fake_run)
    cities = ("beijing", "tianjin", "shanghai")
    assert scheduler.refresh("vehicle-restriction", tmp_path / "state.json", cities) == set()
    assert [call[-1] for call in calls] == list(cities)
    assert all(call[1:3] == ["--state", str(tmp_path / "state.json")] for call in calls)


def test_missing_city_policy_is_due_immediately():
    assert city_check_date({}, "shanghai", date(2026, 11, 11)) == date(2026, 11, 11)
