"""SQLite cache for synced Mi Fitness data."""

from __future__ import annotations

import json
import sqlite3
import stat
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from mi_fitness.config import ensure_data_dir
from mi_fitness.constants import DB_FILE

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    type TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    inserted INTEGER DEFAULT 0,
    updated INTEGER DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS daily_activity (
    day TEXT PRIMARY KEY,
    steps INTEGER,
    distance_m REAL,
    calories REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS sleep_records (
    id TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    start_at TEXT,
    end_at TEXT,
    total_min INTEGER,
    deep_min INTEGER,
    light_min INTEGER,
    rem_min INTEGER,
    awake_min INTEGER,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_sleep_day ON sleep_records(day);

CREATE TABLE IF NOT EXISTS heart_rate_daily (
    day TEXT PRIMARY KEY,
    avg_bpm REAL,
    max_bpm REAL,
    min_bpm REAL,
    resting_bpm REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS workouts (
    id TEXT PRIMARY KEY,
    sport TEXT,
    start_at TEXT NOT NULL,
    end_at TEXT,
    duration_sec INTEGER,
    distance_m REAL,
    calories REAL,
    avg_hr REAL,
    max_hr REAL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_workouts_start ON workouts(start_at);

CREATE TABLE IF NOT EXISTS body_measurements (
    id TEXT PRIMARY KEY,
    measured_at TEXT NOT NULL,
    weight_kg REAL,
    bmi REAL,
    body_fat_pct REAL,
    muscle_kg REAL,
    composition_json TEXT,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_body_measured ON body_measurements(measured_at);
"""


def _chmod_db(path: Path) -> None:
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def init_db() -> None:
    ensure_data_dir()
    with connect() as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_data_dir()
    init_needed = not DB_FILE.exists()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        if init_needed:
            conn.executescript(_SCHEMA)
            _chmod_db(DB_FILE)
        yield conn
        conn.commit()
    finally:
        conn.close()


def start_sync_run(sync_type: str | None, start: date, end: date) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO sync_runs (started_at, type, start_date, end_date)
            VALUES (?, ?, ?, ?)
            """,
            (now, sync_type, start.isoformat(), end.isoformat()),
        )
        return int(cur.lastrowid)


def finish_sync_run(
    run_id: int,
    *,
    inserted: int,
    updated: int,
    error: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            """
            UPDATE sync_runs
            SET finished_at = ?, inserted = ?, updated = ?, error = ?
            WHERE id = ?
            """,
            (now, inserted, updated, error, run_id),
        )


def upsert_daily_activity(rows: list[dict[str, Any]]) -> tuple[int, int]:
    ins, upd = 0, 0
    with connect() as conn:
        for row in rows:
            day = row["day"]
            existed = conn.execute(
                "SELECT 1 FROM daily_activity WHERE day = ?", (day,)
            ).fetchone()
            conn.execute(
                """
                INSERT INTO daily_activity (day, steps, distance_m, calories, raw_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(day) DO UPDATE SET
                  steps = excluded.steps,
                  distance_m = excluded.distance_m,
                  calories = excluded.calories,
                  raw_json = excluded.raw_json
                """,
                (
                    day,
                    row.get("steps"),
                    row.get("distance_m"),
                    row.get("calories"),
                    json.dumps(row.get("raw"), ensure_ascii=False),
                ),
            )
            if existed:
                upd += 1
            else:
                ins += 1
    return ins, upd


def upsert_sleep(rows: list[dict[str, Any]]) -> tuple[int, int]:
    ins, upd = 0, 0
    with connect() as conn:
        for row in rows:
            rid = row["id"]
            existed = conn.execute("SELECT 1 FROM sleep_records WHERE id = ?", (rid,)).fetchone()
            conn.execute(
                """
                INSERT INTO sleep_records (
                    id, day, start_at, end_at, total_min, deep_min, light_min,
                    rem_min, awake_min, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  day = excluded.day,
                  start_at = excluded.start_at,
                  end_at = excluded.end_at,
                  total_min = excluded.total_min,
                  deep_min = excluded.deep_min,
                  light_min = excluded.light_min,
                  rem_min = excluded.rem_min,
                  awake_min = excluded.awake_min,
                  raw_json = excluded.raw_json
                """,
                (
                    rid,
                    row["day"],
                    row.get("start_at"),
                    row.get("end_at"),
                    row.get("total_min"),
                    row.get("deep_min"),
                    row.get("light_min"),
                    row.get("rem_min"),
                    row.get("awake_min"),
                    json.dumps(row.get("raw"), ensure_ascii=False),
                ),
            )
            if existed:
                upd += 1
            else:
                ins += 1
    return ins, upd


def upsert_heart_rate_daily(rows: list[dict[str, Any]]) -> tuple[int, int]:
    ins, upd = 0, 0
    with connect() as conn:
        for row in rows:
            day = row["day"]
            existed = conn.execute(
                "SELECT 1 FROM heart_rate_daily WHERE day = ?", (day,)
            ).fetchone()
            conn.execute(
                """
                INSERT INTO heart_rate_daily (
                    day, avg_bpm, max_bpm, min_bpm, resting_bpm, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(day) DO UPDATE SET
                  avg_bpm = excluded.avg_bpm,
                  max_bpm = excluded.max_bpm,
                  min_bpm = excluded.min_bpm,
                  resting_bpm = excluded.resting_bpm,
                  raw_json = excluded.raw_json
                """,
                (
                    day,
                    row.get("avg_bpm"),
                    row.get("max_bpm"),
                    row.get("min_bpm"),
                    row.get("resting_bpm"),
                    json.dumps(row.get("raw"), ensure_ascii=False),
                ),
            )
            if existed:
                upd += 1
            else:
                ins += 1
    return ins, upd


def upsert_workouts(rows: list[dict[str, Any]]) -> tuple[int, int]:
    ins, upd = 0, 0
    with connect() as conn:
        for row in rows:
            wid = row["id"]
            existed = conn.execute("SELECT 1 FROM workouts WHERE id = ?", (wid,)).fetchone()
            conn.execute(
                """
                INSERT INTO workouts (
                    id, sport, start_at, end_at, duration_sec, distance_m,
                    calories, avg_hr, max_hr, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  sport = excluded.sport,
                  start_at = excluded.start_at,
                  end_at = excluded.end_at,
                  duration_sec = excluded.duration_sec,
                  distance_m = excluded.distance_m,
                  calories = excluded.calories,
                  avg_hr = excluded.avg_hr,
                  max_hr = excluded.max_hr,
                  raw_json = excluded.raw_json
                """,
                (
                    wid,
                    row.get("sport"),
                    row["start_at"],
                    row.get("end_at"),
                    row.get("duration_sec"),
                    row.get("distance_m"),
                    row.get("calories"),
                    row.get("avg_hr"),
                    row.get("max_hr"),
                    json.dumps(row.get("raw"), ensure_ascii=False),
                ),
            )
            if existed:
                upd += 1
            else:
                ins += 1
    return ins, upd


def upsert_body(rows: list[dict[str, Any]]) -> tuple[int, int]:
    ins, upd = 0, 0
    with connect() as conn:
        for row in rows:
            bid = row["id"]
            existed = conn.execute(
                "SELECT 1 FROM body_measurements WHERE id = ?", (bid,)
            ).fetchone()
            comp = row.get("composition") or {}
            conn.execute(
                """
                INSERT INTO body_measurements (
                    id, measured_at, weight_kg, bmi, body_fat_pct, muscle_kg,
                    composition_json, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  measured_at = excluded.measured_at,
                  weight_kg = excluded.weight_kg,
                  bmi = excluded.bmi,
                  body_fat_pct = excluded.body_fat_pct,
                  muscle_kg = excluded.muscle_kg,
                  composition_json = excluded.composition_json,
                  raw_json = excluded.raw_json
                """,
                (
                    bid,
                    row["measured_at"],
                    row.get("weight_kg"),
                    row.get("bmi"),
                    row.get("body_fat_pct"),
                    row.get("muscle_kg"),
                    json.dumps(comp, ensure_ascii=False),
                    json.dumps(row.get("raw"), ensure_ascii=False),
                ),
            )
            if existed:
                upd += 1
            else:
                ins += 1
    return ins, upd


def db_status() -> dict[str, Any]:
    with connect() as conn:
        counts = {}
        for table in (
            "daily_activity",
            "sleep_records",
            "heart_rate_daily",
            "workouts",
            "body_measurements",
        ):
            row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            counts[table] = row["c"] if row else 0
        last = conn.execute(
            "SELECT * FROM sync_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return {
            "db_path": str(DB_FILE),
            "counts": counts,
            "last_sync": dict(last) if last else None,
        }


def query_steps(since: date, until: date) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT day, steps, distance_m, calories
            FROM daily_activity
            WHERE day >= ? AND day <= ?
            ORDER BY day
            """,
            (since.isoformat(), until.isoformat()),
        ).fetchall()
    return [dict(r) for r in rows]


def query_sleep(since: date, until: date) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, day, start_at, end_at, total_min, deep_min, light_min,
                   rem_min, awake_min, raw_json
            FROM sleep_records
            WHERE day >= ? AND day <= ?
            ORDER BY day, start_at
            """,
            (since.isoformat(), until.isoformat()),
        ).fetchall()
    return [_row_with_optional_raw(r) for r in rows]


def query_heart_rate(since: date, until: date) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT day, avg_bpm, max_bpm, min_bpm, resting_bpm
            FROM heart_rate_daily
            WHERE day >= ? AND day <= ?
            ORDER BY day
            """,
            (since.isoformat(), until.isoformat()),
        ).fetchall()
    return [dict(r) for r in rows]


def query_workouts(since: date, until: date) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, sport, start_at, end_at, duration_sec, distance_m,
                   calories, avg_hr, max_hr, raw_json
            FROM workouts
            WHERE date(start_at) >= ? AND date(start_at) <= ?
            ORDER BY start_at DESC
            """,
            (since.isoformat(), until.isoformat()),
        ).fetchall()
    return [_row_with_optional_raw(r) for r in rows]


def query_weight(since: date, until: date, *, full: bool = False) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, measured_at, weight_kg, bmi, body_fat_pct, muscle_kg,
                   composition_json, raw_json
            FROM body_measurements
            WHERE date(measured_at) >= ? AND date(measured_at) <= ?
            ORDER BY measured_at DESC
            """,
            (since.isoformat(), until.isoformat()),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        if not full:
            item.pop("composition_json", None)
            item.pop("raw_json", None)
        else:
            item["composition"] = json.loads(item.pop("composition_json") or "{}")
        out.append(item)
    return out


def _row_with_optional_raw(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    if "raw_json" in d and d["raw_json"]:
        try:
            d["raw"] = json.loads(d["raw_json"])
        except json.JSONDecodeError:
            pass
        del d["raw_json"]
    return d
