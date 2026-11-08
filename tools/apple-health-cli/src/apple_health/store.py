"""SQLite cache for synced Health samples and workouts."""

from __future__ import annotations

import json
import sqlite3
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from apple_health.constants import DATA_DIR, DB_FILE


def _secure_db_dir() -> None:
    DATA_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)


def _chmod_db(path: Path) -> None:
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def init_db() -> None:
    _secure_db_dir()
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS quantity_samples (
                uuid TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                source_name TEXT,
                source_bundle TEXT,
                metadata_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_quantity_kind_start
                ON quantity_samples(kind, start_at);

            CREATE TABLE IF NOT EXISTS category_samples (
                uuid TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                value TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                source_name TEXT,
                source_bundle TEXT,
                metadata_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_category_kind_start
                ON category_samples(kind, start_at);

            CREATE TABLE IF NOT EXISTS workouts (
                uuid TEXT PRIMARY KEY,
                activity_type TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                duration_sec REAL,
                energy_kcal REAL,
                distance_m REAL,
                source_name TEXT,
                metadata_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_workouts_start ON workouts(start_at);

            CREATE TABLE IF NOT EXISTS import_log (
                path TEXT PRIMARY KEY,
                sha256 TEXT NOT NULL,
                imported_at TEXT NOT NULL
            );
            """
        )


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    _secure_db_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
        _chmod_db(DB_FILE)
    finally:
        conn.close()


def upsert_quantities(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    init_db()
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO quantity_samples (
                uuid, kind, value, unit, start_at, end_at,
                source_name, source_bundle, metadata_json
            ) VALUES (
                :uuid, :kind, :value, :unit, :start_at, :end_at,
                :source_name, :source_bundle, :metadata_json
            )
            ON CONFLICT(uuid) DO UPDATE SET
                kind=excluded.kind,
                value=excluded.value,
                unit=excluded.unit,
                start_at=excluded.start_at,
                end_at=excluded.end_at,
                source_name=excluded.source_name,
                source_bundle=excluded.source_bundle,
                metadata_json=excluded.metadata_json
            """,
            rows,
        )
    return len(rows)


def upsert_categories(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    init_db()
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO category_samples (
                uuid, kind, value, start_at, end_at,
                source_name, source_bundle, metadata_json
            ) VALUES (
                :uuid, :kind, :value, :start_at, :end_at,
                :source_name, :source_bundle, :metadata_json
            )
            ON CONFLICT(uuid) DO UPDATE SET
                kind=excluded.kind,
                value=excluded.value,
                start_at=excluded.start_at,
                end_at=excluded.end_at,
                source_name=excluded.source_name,
                source_bundle=excluded.source_bundle,
                metadata_json=excluded.metadata_json
            """,
            rows,
        )
    return len(rows)


def upsert_workouts(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    init_db()
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO workouts (
                uuid, activity_type, start_at, end_at, duration_sec,
                energy_kcal, distance_m, source_name, metadata_json
            ) VALUES (
                :uuid, :activity_type, :start_at, :end_at, :duration_sec,
                :energy_kcal, :distance_m, :source_name, :metadata_json
            )
            ON CONFLICT(uuid) DO UPDATE SET
                activity_type=excluded.activity_type,
                start_at=excluded.start_at,
                end_at=excluded.end_at,
                duration_sec=excluded.duration_sec,
                energy_kcal=excluded.energy_kcal,
                distance_m=excluded.distance_m,
                source_name=excluded.source_name,
                metadata_json=excluded.metadata_json
            """,
            rows,
        )
    return len(rows)


def query_quantities(
    kind: str,
    start: str,
    end: str,
    *,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT uuid, kind, value, unit, start_at, end_at,
                   source_name, source_bundle, metadata_json
            FROM quantity_samples
            WHERE kind = ? AND start_at >= ? AND start_at < ?
            ORDER BY start_at
            LIMIT ?
            """,
            (kind, start, end, limit),
        )
        return [_row_quantity(r) for r in cur.fetchall()]


def query_categories(
    kind: str,
    start: str,
    end: str,
    *,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT uuid, kind, value, start_at, end_at,
                   source_name, source_bundle, metadata_json
            FROM category_samples
            WHERE kind = ? AND start_at >= ? AND start_at < ?
            ORDER BY start_at
            LIMIT ?
            """,
            (kind, start, end, limit),
        )
        return [_row_category(r) for r in cur.fetchall()]


def query_workouts(
    start: str,
    end: str,
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT uuid, activity_type, start_at, end_at, duration_sec,
                   energy_kcal, distance_m, source_name, metadata_json
            FROM workouts
            WHERE start_at >= ? AND start_at < ?
            ORDER BY start_at DESC
            LIMIT ?
            """,
            (start, end, limit),
        )
        return [_row_workout(r) for r in cur.fetchall()]


def db_stats() -> dict[str, Any]:
    init_db()
    with connect() as conn:
        def count(table: str) -> int:
            row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            return int(row["c"]) if row else 0

        return {
            "db_path": str(DB_FILE),
            "quantity_samples": count("quantity_samples"),
            "category_samples": count("category_samples"),
            "workouts": count("workouts"),
        }


def _row_quantity(row: sqlite3.Row) -> dict[str, Any]:
    meta = row["metadata_json"]
    return {
        "uuid": row["uuid"],
        "kind": row["kind"],
        "value": row["value"],
        "unit": row["unit"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "source_name": row["source_name"],
        "source_bundle": row["source_bundle"],
        "metadata": json.loads(meta) if meta else None,
    }


def _row_category(row: sqlite3.Row) -> dict[str, Any]:
    meta = row["metadata_json"]
    return {
        "uuid": row["uuid"],
        "kind": row["kind"],
        "value": row["value"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "source_name": row["source_name"],
        "source_bundle": row["source_bundle"],
        "metadata": json.loads(meta) if meta else None,
    }


def _row_workout(row: sqlite3.Row) -> dict[str, Any]:
    meta = row["metadata_json"]
    return {
        "uuid": row["uuid"],
        "activity_type": row["activity_type"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "duration_sec": row["duration_sec"],
        "energy_kcal": row["energy_kcal"],
        "distance_m": row["distance_m"],
        "source_name": row["source_name"],
        "metadata": json.loads(meta) if meta else None,
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
