#!/usr/bin/env python3
"""Wait for each registered city's stored policy-check date and refresh due cities."""
from __future__ import annotations

import calendar
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime, time as day_time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

CITY_SLUG = re.compile(r"[a-z][a-z0-9_-]*")
TZ = ZoneInfo("Asia/Shanghai")


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def registered_cities(cli: str) -> tuple[str, ...]:
    """Read the canonical city list from the CLI; invalid output is an error."""
    result = subprocess.run(
        [cli, "cities"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[:500]
        raise RuntimeError(
            f"vehicle-restriction cities exited {result.returncode}"
            + (f": {detail}" if detail else "")
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"cities output is not valid JSON: {exc}") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("cities output must be a non-empty top-level JSON array")
    if any(not isinstance(city, str) or not CITY_SLUG.fullmatch(city) for city in payload):
        raise ValueError("cities output contains an invalid city slug")
    cities = tuple(payload)
    if len(set(cities)) != len(cities):
        raise ValueError("cities output contains duplicate city slugs")
    return cities


def city_check_date(state: dict, city: str, today: date) -> date:
    checks = state.get("checks", {}).get(city, {})
    policies = []
    for section in ("policies", "upcoming_policies"):
        payload = state.get(section, {}).get(city)
        if payload:
            policies.append(payload)
    policy = max(policies, key=lambda item: item.get("valid_from", "")) if policies else None
    if checks.get("final_check_done") and policy:
        return date.fromisoformat(policy["valid_until"])
    if checks.get("next_check_date"):
        return date.fromisoformat(checks["next_check_date"])
    if policy:
        return add_months(date.fromisoformat(policy["valid_until"]), -1)
    return today


def scheduled_city_check_date(
    state: dict, city: str, today: date, retry_after: date | None = None
) -> date:
    """A retry marker only delays a city whose stored due date is already overdue."""
    due_day = city_check_date(state, city, today)
    if due_day <= today and retry_after is not None and retry_after > today:
        return retry_after
    return due_day


def earliest_check(
    state: dict,
    today: date,
    cities: tuple[str, ...],
    retry_dates: dict[str, date] | None = None,
) -> date:
    if not cities:
        raise ValueError("no registered cities")
    retry_dates = retry_dates or {}
    return min(
        scheduled_city_check_date(state, city, today, retry_dates.get(city))
        for city in cities
    )


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"policies": {}, "checks": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("state file must contain a JSON object")
    return value


def load_retry_dates(path: Path, cities: tuple[str, ...]) -> dict[str, date]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        retry_after = payload.get("retry_after", {})
        if not isinstance(retry_after, dict):
            raise ValueError("retry_after must be an object")
        return {
            city: date.fromisoformat(day)
            for city, day in retry_after.items()
            if city in cities
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def save_retry_dates(path: Path, retry_dates: dict[str, date]) -> None:
    if retry_dates:
        path.write_text(
            json.dumps(
                {"retry_after": {city: day.isoformat() for city, day in retry_dates.items()}},
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    else:
        path.unlink(missing_ok=True)


def refresh(cli: str, state_path: Path, cities: tuple[str, ...]) -> set[str]:
    failed: set[str] = set()
    for city in cities:
        result = subprocess.run(
            [cli, "--state", str(state_path), "refresh", "--city", city],
            check=False,
        )
        if result.returncode != 0:
            print(f"refresh for {city} failed with exit code {result.returncode}", file=sys.stderr, flush=True)
            failed.add(city)
    return failed


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: scheduler.py VEHICLE_RESTRICTION_BIN STATE_PATH", file=sys.stderr)
        return 2
    cli = sys.argv[1]
    state_path = Path(sys.argv[2])
    retry_path = state_path.with_name("launchd-retries.json")
    last_cities: tuple[str, ...] | None = None
    while True:
        now = datetime.now(TZ)
        try:
            cities = registered_cities(cli)
            if cities != last_cities:
                print(f"registered policy cities: {', '.join(cities)}", flush=True)
                last_cities = cities
            state = load_state(state_path)
            retry_dates = load_retry_dates(retry_path, cities)
            scheduled = {
                city: scheduled_city_check_date(state, city, now.date(), retry_dates.get(city))
                for city in cities
            }
        except Exception as exc:
            print(
                f"city discovery or scheduler state failed; no refresh will run; retrying in six hours: {exc}",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(6 * 60 * 60)
            continue

        due_cities = tuple(city for city in cities if scheduled[city] <= now.date())
        if due_cities:
            initial_fetch = any(
                not state.get("policies", {}).get(city)
                and not state.get("upcoming_policies", {}).get(city)
                and not state.get("checks", {}).get(city, {}).get("next_check_date")
                for city in due_cities
            )
            target_today = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now < target_today and not initial_fetch:
                print(f"policy check is due today; waiting until {target_today.isoformat()}", flush=True)
                time.sleep((target_today - now).total_seconds())
                continue
            print(f"policy check is due for {', '.join(due_cities)}", flush=True)
            failed = refresh(cli, state_path, due_cities)
            try:
                updated_state = load_state(state_path)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                print(f"cannot verify updated check dates: {exc}; retrying in six hours", file=sys.stderr, flush=True)
                time.sleep(6 * 60 * 60)
                continue

            for city in due_cities:
                if city in failed or city_check_date(updated_state, city, now.date()) <= now.date():
                    # Expired policies can remain due in state after the final expiry-day check.
                    retry_dates[city] = now.date() + timedelta(days=7)
                else:
                    retry_dates.pop(city, None)
            save_retry_dates(retry_path, retry_dates)
            continue

        target_day = min(scheduled.values())
        target = datetime.combine(target_day, day_time(hour=6), tzinfo=TZ)
        delay = (target - now).total_seconds()
        print(f"next local policy check: {target.isoformat()}", flush=True)
        time.sleep(max(1, delay))


if __name__ == "__main__":
    raise SystemExit(main())
