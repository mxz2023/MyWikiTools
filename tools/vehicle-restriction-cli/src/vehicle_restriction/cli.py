from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from .registry import CITY_REGISTRY
from .schedule import today_shanghai
from .service import refresh_city, reminder
from .storage import load_state, save_state


def default_state_path() -> Path:
    configured = os.environ.get("VEHICLE_RESTRICTION_STATE")
    return Path(configured).expanduser() if configured else Path.home() / ".local/share/vehicle-restriction-cli/state.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="vehicle-restriction")
    parser.add_argument("--state", type=Path, default=default_state_path())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("cities", help="离线列出注册城市")
    update = sub.add_parser("refresh", help="联网检查官方政策")
    supported_cities = tuple(CITY_REGISTRY)
    update.add_argument("--city", choices=supported_cities, required=True)
    check = sub.add_parser("remind", help="离线查询本地尾号轮换组")
    check.add_argument("city", choices=supported_cities)
    check.add_argument("--plate-region", required=True, help="号牌地区简称，例如津")
    check.add_argument("--tail", required=True, choices=tuple("0123456789"), help="号牌尾号")
    check.add_argument("--date", type=date.fromisoformat, default=None)
    args = parser.parse_args(argv)
    if args.command == "cities":
        print(json.dumps(list(CITY_REGISTRY), ensure_ascii=False))
        return 0
    if args.command == "remind" and args.date is None:
        args.date = today_shanghai()
    state = load_state(args.state)
    if args.command == "refresh":
        results = {args.city: refresh_city(state, args.city, today_shanghai())}
        save_state(args.state, state)
        print(json.dumps(results, ensure_ascii=False))
        return 0
    if len(args.plate_region) != 1:
        parser.error("--plate-region 只接受一个地区简称字符")
    result = reminder(state, args.city, args.tail, args.date)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["policy_status"] == "confirmed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
