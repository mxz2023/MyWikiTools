"""Normalize mifit records into store rows."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any


def _epoch_iso(epoch_s: int | None) -> str | None:
    if epoch_s is None:
        return None
    return datetime.fromtimestamp(epoch_s, tz=timezone.utc).isoformat()


def step_rows(records: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rec in records:
        out.append(
            {
                "day": rec.date,
                "steps": rec.steps,
                "distance_m": rec.distance_m,
                "calories": rec.step_calories,
                "raw": _as_dict(rec),
            }
        )
    return out


def sleep_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for day_rec in records:
        day = day_rec.date
        if day_rec.sessions:
            for i, sess in enumerate(day_rec.sessions):
                rows.append(
                    {
                        "id": f"{day}:{sess.start_epoch_s}:{i}",
                        "day": day,
                        "start_at": _epoch_iso(sess.start_epoch_s),
                        "end_at": _epoch_iso(sess.end_epoch_s),
                        "total_min": sess.asleep_min,
                        "deep_min": sess.deep_min,
                        "light_min": sess.light_min,
                        "rem_min": sess.rem_min,
                        "awake_min": sess.awake_min,
                        "raw": _as_dict(sess),
                    }
                )
        else:
            rows.append(
                {
                    "id": f"{day}:summary",
                    "day": day,
                    "start_at": None,
                    "end_at": None,
                    "total_min": day_rec.asleep_min,
                    "deep_min": day_rec.deep_min,
                    "light_min": day_rec.light_min,
                    "rem_min": day_rec.rem_min,
                    "awake_min": day_rec.awake_min,
                    "raw": _as_dict(day_rec),
                }
            )
    return rows


def heart_rate_rows(records: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "day": rec.date,
            "avg_bpm": rec.avg_bpm,
            "max_bpm": rec.max_bpm,
            "min_bpm": rec.min_bpm,
            "resting_bpm": rec.resting_bpm,
            "raw": _as_dict(rec),
        }
        for rec in records
    ]


def workout_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in records:
        wid = f"{rec.start_epoch_s}:{rec.source_sport_code or 0}"
        rows.append(
            {
                "id": wid,
                "sport": rec.sport,
                "start_at": _epoch_iso(rec.start_epoch_s) or "",
                "end_at": _epoch_iso(rec.end_epoch_s),
                "duration_sec": rec.duration_s,
                "distance_m": rec.distance_m,
                "calories": rec.active_kcal or rec.total_kcal,
                "avg_hr": rec.avg_hr_bpm,
                "max_hr": rec.max_hr_bpm,
                "raw": _as_dict(rec),
            }
        )
    return rows


def weight_rows(records: list[Any], raw_values: list[dict] | None = None) -> list[dict[str, Any]]:
    """Map weight records; composition from parallel raw rows when present."""
    raw_by_time: dict[int, dict] = {}
    for item in raw_values or []:
        t = item.get("time")
        if isinstance(t, int):
            val = item.get("value")
            if isinstance(val, dict):
                raw_by_time[t] = val

    rows: list[dict[str, Any]] = []
    for rec in records:
        comp: dict[str, Any] = {}
        body_fat = None
        muscle = None
        raw = raw_by_time.get(rec.epoch_s) or {}
        if raw:
            comp = {k: v for k, v in raw.items() if k not in ("weight", "bmi", "time")}
            body_fat = _first_float(raw, "body_fat", "bodyFat", "fat_rate", "body_fat_rate")
            muscle = _first_float(raw, "muscle", "muscle_mass", "skeletal_muscle")

        rows.append(
            {
                "id": str(rec.epoch_s),
                "measured_at": _epoch_iso(rec.epoch_s) or "",
                "weight_kg": rec.weight_kg,
                "bmi": rec.bmi,
                "body_fat_pct": body_fat,
                "muscle_kg": muscle,
                "composition": comp,
                "raw": {"record": _as_dict(rec), "value": raw},
            }
        )
    return rows


def _first_float(data: dict, *keys: str) -> float | None:
    for key in keys:
        if key not in data:
            continue
        try:
            return float(data[key])
        except (TypeError, ValueError):
            continue
    return None


def _as_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return obj
    return str(obj)
