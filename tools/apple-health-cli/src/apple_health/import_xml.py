"""Import Apple Health export.xml into SQLite (no HealthKit signing required)."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apple_health import store

# Maps export type strings -> internal kind keys
_QUANTITY_TYPES: dict[str, tuple[str, str]] = {
    "HKQuantityTypeIdentifierStepCount": ("steps", "count"),
    "HKQuantityTypeIdentifierHeartRate": ("heart_rate", "count/min"),
    "HKQuantityTypeIdentifierRestingHeartRate": ("resting_heart_rate", "count/min"),
    "HKQuantityTypeIdentifierActiveEnergyBurned": ("active_energy", "kcal"),
    "HKQuantityTypeIdentifierDistanceWalkingRunning": ("distance", "m"),
}

_CATEGORY_TYPES: dict[str, str] = {
    "HKCategoryTypeIdentifierSleepAnalysis": "sleep",
}


def _parse_apple_datetime(raw: str) -> str:
    # export uses "2024-01-01 12:00:00 +0800"
    dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S %z")
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def already_imported(path: Path, digest: str) -> bool:
    store.init_db()
    with store.connect() as conn:
        row = conn.execute(
            "SELECT sha256 FROM import_log WHERE path = ?", (str(path.resolve()),)
        ).fetchone()
        return bool(row and row["sha256"] == digest)


def mark_imported(path: Path, digest: str) -> None:
    store.init_db()
    with store.connect() as conn:
        conn.execute(
            """
            INSERT INTO import_log (path, sha256, imported_at)
            VALUES (?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256, imported_at=excluded.imported_at
            """,
            (str(path.resolve()), digest, store.utc_now_iso()),
        )


def import_export_xml(
    path: Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = file_sha256(path)
    if not force and already_imported(path, digest):
        return {"skipped": True, "reason": "unchanged", "path": str(path)}

    quantities: list[dict[str, Any]] = []
    categories: list[dict[str, Any]] = []
    workouts: list[dict[str, Any]] = []

    context = ET.iterparse(path, events=("end",))
    for _event, elem in context:
        tag = elem.tag
        if tag == "Record":
            t = elem.get("type") or ""
            if t in _QUANTITY_TYPES:
                kind, unit = _QUANTITY_TYPES[t]
                quantities.append(
                    {
                        "uuid": elem.get("sourceVersion", "") + ":" + (elem.get("startDate") or "") + ":" + t,
                        "kind": kind,
                        "value": float(elem.get("value") or 0),
                        "unit": unit,
                        "start_at": _parse_apple_datetime(elem.get("startDate") or ""),
                        "end_at": _parse_apple_datetime(elem.get("endDate") or ""),
                        "source_name": elem.get("sourceName"),
                        "source_bundle": elem.get("sourceName"),
                        "metadata_json": None,
                    }
                )
            elif t in _CATEGORY_TYPES:
                categories.append(
                    {
                        "uuid": (elem.get("sourceVersion") or "") + ":" + (elem.get("startDate") or "") + ":" + t,
                        "kind": _CATEGORY_TYPES[t],
                        "value": elem.get("value") or "",
                        "start_at": _parse_apple_datetime(elem.get("startDate") or ""),
                        "end_at": _parse_apple_datetime(elem.get("endDate") or ""),
                        "source_name": elem.get("sourceName"),
                        "source_bundle": elem.get("sourceName"),
                        "metadata_json": None,
                    }
                )
        elif tag == "Workout":
            start = _parse_apple_datetime(elem.get("startDate") or "")
            end = _parse_apple_datetime(elem.get("endDate") or "")
            workouts.append(
                {
                    "uuid": f"workout:{start}:{elem.get('workoutActivityType')}",
                    "activity_type": (elem.get("workoutActivityType") or "unknown").replace(
                        "HKWorkoutActivityType", ""
                    ),
                    "start_at": start,
                    "end_at": end,
                    "duration_sec": float(elem.get("duration") or 0),
                    "energy_kcal": _optional_float(elem.get("totalEnergyBurned")),
                    "distance_m": _optional_float(elem.get("totalDistance")),
                    "source_name": elem.get("sourceName"),
                    "metadata_json": None,
                }
            )
        elem.clear()

    qn = store.upsert_quantities(quantities)
    cn = store.upsert_categories(categories)
    wn = store.upsert_workouts(workouts)
    mark_imported(path, digest)
    return {
        "skipped": False,
        "path": str(path),
        "imported": {"quantities": qn, "categories": cn, "workouts": wn},
    }


def _optional_float(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None
