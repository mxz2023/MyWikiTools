"""Mi Fitness cloud client wrapper."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests
from mifit.auth.renew import renew_session
from mifit.auth.session import Session
from mifit.client import MiFit, to_epoch_s
from mifit.domains.passthrough import fetch_raw_rows
from mifit.errors import AuthError
from mifit.transport import Transport

from mi_fitness.config import load_local_session, save_local_session
from mi_fitness.constants import HEALTH_API_BASE


def _day_str(d: date) -> str:
    return d.isoformat()


def date_range_epoch(start: date, end: date) -> tuple[int, int]:
    start_s = to_epoch_s(_day_str(start))
    end_s = to_epoch_s(_day_str(end), end_of_day=True)
    return start_s, end_s


def open_mifit(session: Session | None = None) -> MiFit:
    sess = session or load_local_session()
    if sess is None or not sess.is_valid():
        raise AuthError("No valid session. Run `mfp login`.")
    http = requests.Session()

    def renew(old: Session) -> Session:
        new = renew_session(old, http)
        save_local_session(new)
        return new

    mifit = MiFit(session=sess, http=http, auto_renew=False)
    mifit._transport = Transport(sess, http=http, renew=renew, delay_s=0.5)  # noqa: SLF001
    return mifit


def ping_cloud(session: Session | None = None) -> dict[str, Any]:
    """Lightweight connectivity check."""
    mifit = open_mifit(session)
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=1)
    try:
        result = mifit.steps(_day_str(start), _day_str(today))
        return {"ok": True, "api_base": HEALTH_API_BASE, "sample_rows": len(result.raw)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def fetch_fitness_key(
    mifit: MiFit,
    key: str,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    start_s, end_s = date_range_epoch(start, end)
    t = mifit._transport  # noqa: SLF001 — sync layer needs transport
    result = fetch_raw_rows(t, key, start_s, end_s)
    rows: list[dict[str, Any]] = []
    for entry in result.raw:
        if not isinstance(entry, dict):
            continue
        row = dict(entry)
        val = row.get("value")
        if isinstance(val, str):
            try:
                row["value"] = json.loads(val)
            except json.JSONDecodeError:
                pass
        rows.append(row)
    return rows


def fetch_workouts(mifit: MiFit, start: date, end: date) -> list[Any]:
    result = mifit.workouts(_day_str(start), _day_str(end))
    return list(result.records)


def fetch_steps_daily(mifit: MiFit, start: date, end: date) -> list[Any]:
    result = mifit.steps(_day_str(start), _day_str(end))
    return list(result.records)


def fetch_sleep_daily(mifit: MiFit, start: date, end: date) -> list[Any]:
    result = mifit.sleep(_day_str(start), _day_str(end))
    return list(result.records)


def fetch_heart_rate_daily(mifit: MiFit, start: date, end: date) -> list[Any]:
    result = mifit.heart_rate_daily(_day_str(start), _day_str(end))
    return list(result.records)


def fetch_weight(mifit: MiFit, start: date, end: date) -> list[Any]:
    result = mifit.weight(_day_str(start), _day_str(end))
    return list(result.records)


def request_raw(
    session: Session,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    mifit = open_mifit(session)
    t = mifit._transport  # noqa: SLF001
    endpoint = path.lstrip("/")
    if endpoint.startswith("app/v1/"):
        endpoint = endpoint.removeprefix("app/v1/")
    return t.get_json(endpoint, payload)
