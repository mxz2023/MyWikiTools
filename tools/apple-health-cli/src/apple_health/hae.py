"""Health Auto Export (HAE) REST JSON → ahp SQLite."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from apple_health import store

_QUANTITY_METRICS: dict[str, tuple[str, str]] = {
    "step_count": ("steps", "count"),
    "heart_rate": ("heart_rate", "count/min"),
    "resting_heart_rate": ("resting_heart_rate", "count/min"),
    "walking_heart_rate_average": ("heart_rate", "count/min"),
    "active_energy": ("active_energy", "kcal"),
    "walking_running_distance": ("distance", "m"),
    "heart_rate_variability_sdnn": ("hrv_sdnn", "ms"),
}

_SLEEP_STAGES = {
    "In Bed": "inBed",
    "Asleep": "asleep",
    "Awake": "awake",
    "Core": "asleepCore",
    "Deep": "asleepDeep",
    "REM": "asleepREM",
}


def _parse_hae_datetime(raw: str) -> str:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            if fmt.endswith("Z") and raw.endswith("Z"):
                dt = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            else:
                dt = datetime.strptime(raw, fmt)
            return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except ValueError:
            continue
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _uuid(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def is_hae_payload(doc: dict[str, Any]) -> bool:
    data = doc.get("data")
    return isinstance(data, dict) and ("metrics" in data or "workouts" in data)


def convert_hae(doc: dict[str, Any]) -> dict[str, Any]:
    data = doc.get("data") or {}
    quantities: list[dict[str, Any]] = []
    categories: list[dict[str, Any]] = []

    for metric in data.get("metrics") or []:
        if not isinstance(metric, dict):
            continue
        name = str(metric.get("name") or "")
        units = str(metric.get("units") or "")
        points = metric.get("data") or []
        if name == "sleep_analysis":
            for p in points:
                if not isinstance(p, dict):
                    continue
                start = p.get("startDate") or p.get("date") or ""
                end = p.get("endDate") or start
                if not start:
                    continue
                val = _SLEEP_STAGES.get(str(p.get("value") or ""), str(p.get("value") or "unknown"))
                categories.append(
                    {
                        "uuid": _uuid("sleep", start, end, val, str(p.get("source"))),
                        "kind": "sleep",
                        "value": val,
                        "start_at": _parse_hae_datetime(str(start)),
                        "end_at": _parse_hae_datetime(str(end)),
                        "source_name": p.get("source"),
                        "source_bundle": None,
                    }
                )
            continue

        mapped = _QUANTITY_METRICS.get(name)
        if not mapped:
            continue
        kind, default_unit = mapped
        unit = units or default_unit
        for p in points:
            if not isinstance(p, dict):
                continue
            qty = p.get("qty")
            if qty is None and "Avg" in p:
                qty = p.get("Avg")
            if qty is None and "Max" in p:
                qty = p.get("Max")
            if qty is None:
                continue
            date = p.get("date") or p.get("startDate") or p.get("endDate")
            if not date:
                continue
            start_at = _parse_hae_datetime(str(date))
            end_at = start_at
            if p.get("endDate"):
                end_at = _parse_hae_datetime(str(p["endDate"]))
            value = float(qty)
            if kind == "steps":
                value = float(round(value))
            quantities.append(
                {
                    "uuid": _uuid(kind, start_at, str(qty), name),
                    "kind": kind,
                    "value": value,
                    "unit": unit,
                    "start_at": start_at,
                    "end_at": end_at,
                    "source_name": p.get("source"),
                    "source_bundle": None,
                }
            )

    workouts: list[dict[str, Any]] = []
    for w in data.get("workouts") or []:
        if not isinstance(w, dict):
            continue
        start = w.get("start") or ""
        end = w.get("end") or start
        if not start:
            continue
        dist = w.get("distance") or {}
        energy = w.get("activeEnergyBurned") or w.get("totalEnergyBurned") or {}
        workouts.append(
            {
                "uuid": str(w.get("id") or _uuid("workout", start, str(w.get("name")))),
                "activity_type": str(w.get("name") or "workout"),
                "start_at": _parse_hae_datetime(str(start)),
                "end_at": _parse_hae_datetime(str(end)),
                "duration_sec": float(w.get("duration") or 0),
                "energy_kcal": float(energy.get("qty")) if energy.get("qty") is not None else None,
                "distance_m": _distance_m(dist),
                "source_name": w.get("source") or "Health Auto Export",
            }
        )

    return {"quantities": quantities, "categories": categories, "workouts": workouts}


def _distance_m(dist: dict[str, Any]) -> float | None:
    if not dist or dist.get("qty") is None:
        return None
    qty = float(dist["qty"])
    units = str(dist.get("units") or "m").lower()
    if units in ("km", "kilometer", "kilometers"):
        return qty * 1000.0
    if units in ("mi", "mile", "miles"):
        return qty * 1609.344
    return qty


def ingest_hae(doc: dict[str, Any]) -> dict[str, Any]:
    converted = convert_hae(doc)
    q_rows = [
        {
            **r,
            "metadata_json": None,
        }
        for r in converted["quantities"]
    ]
    c_rows = [{**r, "metadata_json": None} for r in converted["categories"]]
    w_rows = [{**r, "metadata_json": None} for r in converted["workouts"]]
    counts = {
        "quantities": store.upsert_quantities(q_rows),
        "categories": store.upsert_categories(c_rows),
        "workouts": store.upsert_workouts(w_rows),
    }
    return {"upserted": counts, "cache": store.db_stats(), "format": "health-auto-export"}
