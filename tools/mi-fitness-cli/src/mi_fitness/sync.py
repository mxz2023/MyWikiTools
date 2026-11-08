"""Pull cloud data into SQLite."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from mi_fitness import parsers
from mi_fitness.client import (
    fetch_heart_rate_daily,
    fetch_sleep_daily,
    fetch_steps_daily,
    fetch_weight,
    fetch_workouts,
    open_mifit,
    fetch_fitness_key,
)
from mi_fitness.constants import SYNC_TYPES
from mi_fitness import store


def parse_dates(
    *,
    start_date: date | None,
    end_date: date | None,
    days: int,
) -> tuple[date, date]:
    end = end_date or date.today()
    if start_date is not None:
        start = start_date
    else:
        start = end - timedelta(days=max(days - 1, 0))
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    return start, end


def sync_range(
    start: date,
    end: date,
    types: list[str] | None = None,
) -> dict[str, Any]:
    chosen = list(types or SYNC_TYPES)
    unknown = [t for t in chosen if t not in SYNC_TYPES]
    if unknown:
        raise ValueError(f"unknown sync type(s): {', '.join(unknown)}")

    store.init_db()
    mifit = open_mifit()
    summary: dict[str, Any] = {"types": {}, "start": start.isoformat(), "end": end.isoformat()}
    total_ins, total_upd = 0, 0

    for sync_type in chosen:
        run_id = store.start_sync_run(sync_type, start, end)
        err: str | None = None
        ins, upd = 0, 0
        try:
            if sync_type == "daily_activity":
                recs = fetch_steps_daily(mifit, start, end)
                rows = parsers.step_rows(recs)
                ins, upd = store.upsert_daily_activity(rows)
            elif sync_type == "sleep":
                recs = fetch_sleep_daily(mifit, start, end)
                rows = parsers.sleep_rows(recs)
                ins, upd = store.upsert_sleep(rows)
            elif sync_type == "heart_rate":
                recs = fetch_heart_rate_daily(mifit, start, end)
                rows = parsers.heart_rate_rows(recs)
                ins, upd = store.upsert_heart_rate_daily(rows)
            elif sync_type == "workouts":
                recs = fetch_workouts(mifit, start, end)
                rows = parsers.workout_rows(recs)
                ins, upd = store.upsert_workouts(rows)
            elif sync_type == "body_measurements":
                recs = fetch_weight(mifit, start, end)
                raw_weight = fetch_fitness_key(mifit, "weight", start, end)
                rows = parsers.weight_rows(recs, raw_weight)
                ins, upd = store.upsert_body(rows)
        except Exception as exc:
            err = str(exc)
            summary["types"][sync_type] = {"error": err}
            store.finish_sync_run(run_id, inserted=ins, updated=upd, error=err)
            continue

        store.finish_sync_run(run_id, inserted=ins, updated=upd, error=None)
        summary["types"][sync_type] = {"inserted": ins, "updated": upd}
        total_ins += ins
        total_upd += upd

    summary["inserted"] = total_ins
    summary["updated"] = total_upd
    return summary
