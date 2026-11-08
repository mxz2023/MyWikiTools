"""Ingest health payloads (JSON) from iPhone push / automation."""

from __future__ import annotations

import json
from typing import Any

from apple_health import store


def apply_fetch_payload(payload: dict[str, Any]) -> dict[str, int]:
    quantities = payload.get("quantities") or []
    categories = payload.get("categories") or []
    workouts = payload.get("workouts") or []

    q_rows = []
    for r in quantities:
        q_rows.append(
            {
                "uuid": r["uuid"],
                "kind": r["kind"],
                "value": r["value"],
                "unit": r["unit"],
                "start_at": r["start_at"],
                "end_at": r["end_at"],
                "source_name": r.get("source_name"),
                "source_bundle": r.get("source_bundle"),
                "metadata_json": json.dumps(r.get("metadata")) if r.get("metadata") else None,
            }
        )
    c_rows = []
    for r in categories:
        c_rows.append(
            {
                "uuid": r["uuid"],
                "kind": r["kind"],
                "value": r["value"],
                "start_at": r["start_at"],
                "end_at": r["end_at"],
                "source_name": r.get("source_name"),
                "source_bundle": r.get("source_bundle"),
                "metadata_json": None,
            }
        )
    w_rows = []
    for r in workouts:
        w_rows.append(
            {
                "uuid": r["uuid"],
                "activity_type": r["activity_type"],
                "start_at": r["start_at"],
                "end_at": r["end_at"],
                "duration_sec": r.get("duration_sec"),
                "energy_kcal": r.get("energy_kcal"),
                "distance_m": r.get("distance_m"),
                "source_name": r.get("source_name"),
                "metadata_json": None,
            }
        )

    return {
        "quantities": store.upsert_quantities(q_rows),
        "categories": store.upsert_categories(c_rows),
        "workouts": store.upsert_workouts(w_rows),
    }


def apply_json_payload(doc: dict[str, Any]) -> dict[str, int]:
    normalized = {
        "quantities": doc.get("quantities") or doc.get("data", {}).get("quantities"),
        "categories": doc.get("categories") or doc.get("data", {}).get("categories"),
        "workouts": doc.get("workouts") or doc.get("data", {}).get("workouts"),
    }
    if normalized["quantities"] is None:
        normalized["quantities"] = []
    if normalized["categories"] is None:
        normalized["categories"] = []
    if normalized["workouts"] is None:
        normalized["workouts"] = []
    return apply_fetch_payload(normalized)


def ingest_document(doc: dict[str, Any]) -> dict[str, Any]:
    counts = apply_json_payload(doc)
    return {"upserted": counts, "cache": store.db_stats()}
