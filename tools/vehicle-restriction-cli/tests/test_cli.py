import json
from datetime import datetime, timezone

import pytest

from vehicle_restriction.cli import main
from vehicle_restriction.policy import validate_policy
from vehicle_restriction.storage import save_state


def test_remind_accepts_region_and_tail_without_full_plate(tmp_path, capsys):
    policy = validate_policy({
        "city": "beijing",
        "valid_from": "2026-09-28",
        "valid_until": "2026-12-27",
        "weekday_groups": {str(day): ["7"] for day in range(5)},
        "source_url": "https://www.beijing.gov.cn/fuwu/bmfw/bmzt/whts/xxwh/",
        "checked_at": datetime(2026, 11, 11, tzinfo=timezone.utc).isoformat(),
    })
    state_path = tmp_path / "state.json"
    save_state(state_path, {"policies": {"beijing": policy.to_dict()}, "checks": {}})

    status = main([
        "--state", str(state_path), "remind", "beijing",
        "--plate-region", "津", "--tail", "7", "--date", "2026-11-11",
    ])

    result = json.loads(capsys.readouterr().out)
    assert status == 0
    assert result["tail"] == "7"
    assert result["tail_rotation_match"] is True
    assert result["travel_status"] == "unknown"
    assert "restricted" not in result


def test_remind_rejects_full_plate_positional_argument(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--state", str(tmp_path / "state.json"), "remind", "beijing", "津A00007"])
    assert exc.value.code == 2


def test_remind_default_date_uses_shanghai_day(monkeypatch, tmp_path, capsys):
    import vehicle_restriction.cli as cli

    policy = validate_policy({
        "city": "beijing",
        "valid_from": "2026-09-28",
        "valid_until": "2026-12-27",
        "weekday_groups": {str(day): ["7"] for day in range(5)},
        "source_url": "https://www.beijing.gov.cn/fuwu/bmfw/bmzt/whts/xxwh/",
        "checked_at": datetime(2026, 11, 11, tzinfo=timezone.utc).isoformat(),
    })
    state_path = tmp_path / "state.json"
    save_state(state_path, {"policies": {"beijing": policy.to_dict()}, "checks": {}})
    monkeypatch.setattr(cli, "today_shanghai", lambda: __import__("datetime").date(2026, 11, 11))

    cli.main([
        "--state", str(state_path), "remind", "beijing",
        "--plate-region", "津", "--tail", "7",
    ])

    result = json.loads(capsys.readouterr().out)
    assert result["date"] == "2026-11-11"


def test_refresh_due_check_uses_shanghai_day(monkeypatch, tmp_path, capsys):
    import vehicle_restriction.cli as cli
    from datetime import date

    captured = {}
    monkeypatch.setattr(cli, "today_shanghai", lambda: date(2026, 11, 11))

    def fake_refresh(state, city, today):
        captured.update(city=city, today=today)
        return "not_due"

    monkeypatch.setattr(cli, "refresh_city", fake_refresh)
    cli.main(["--state", str(tmp_path / "state.json"), "refresh", "--city", "beijing"])
    capsys.readouterr()

    assert captured == {"city": "beijing", "today": date(2026, 11, 11)}


def test_cities_prints_registry_as_json_without_loading_state(monkeypatch, tmp_path, capsys):
    import vehicle_restriction.cli as cli

    def fail_if_state_is_read(_path):
        raise AssertionError("cities must not read state")

    monkeypatch.setattr(cli, "load_state", fail_if_state_is_read)
    status = cli.main(["--state", str(tmp_path / "missing-state.json"), "cities"])

    assert status == 0
    assert capsys.readouterr().out == '["beijing", "tianjin"]\n'
