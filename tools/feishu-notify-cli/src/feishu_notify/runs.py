from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feishu_notify.constants import CONFIG_DIR


def _runs_path() -> Path:
    return CONFIG_DIR / "runs.json"


@dataclass
class RunBinding:
    run_id: str
    message_id: str
    identity: str
    route: str
    scene: str
    updated_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "message_id": self.message_id,
            "identity": self.identity,
            "route": self.route,
            "scene": self.scene,
            "updated_at": self.updated_at,
        }


def _load_store(path: Path | None = None) -> dict[str, Any]:
    p = path or _runs_path()
    if not p.is_file():
        return {"runs": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"runs": {}}
    runs = data.get("runs")
    if not isinstance(runs, dict):
        data["runs"] = {}
    return data


def _save_store(data: dict[str, Any], path: Path | None = None) -> None:
    p = path or _runs_path()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_binding(run_id: str, *, store_path: Path | None = None) -> RunBinding | None:
    if not run_id:
        return None
    row = (_load_store(store_path).get("runs") or {}).get(run_id)
    if not isinstance(row, dict) or not row.get("message_id"):
        return None
    return RunBinding(
        run_id=run_id,
        message_id=str(row["message_id"]),
        identity=str(row.get("identity") or "bot"),
        route=str(row.get("route") or "dm_self"),
        scene=str(row.get("scene") or "agent.progress"),
        updated_at=str(row.get("updated_at") or ""),
    )


def put_binding(binding: RunBinding, *, store_path: Path | None = None) -> None:
    data = _load_store(store_path)
    runs = data.setdefault("runs", {})
    runs[binding.run_id] = {
        "message_id": binding.message_id,
        "identity": binding.identity,
        "route": binding.route,
        "scene": binding.scene,
        "updated_at": binding.updated_at or datetime.now(timezone.utc).isoformat(),
    }
    _save_store(data, store_path)


def clear_binding(run_id: str, *, store_path: Path | None = None) -> bool:
    data = _load_store(store_path)
    runs = data.get("runs") or {}
    if run_id not in runs:
        return False
    del runs[run_id]
    data["runs"] = runs
    _save_store(data, store_path)
    return True


def list_bindings(*, store_path: Path | None = None) -> list[dict[str, str]]:
    runs = _load_store(store_path).get("runs") or {}
    out: list[dict[str, str]] = []
    for rid, row in sorted(runs.items()):
        if isinstance(row, dict) and row.get("message_id"):
            out.append(
                {
                    "run_id": rid,
                    "message_id": str(row["message_id"]),
                    "scene": str(row.get("scene") or ""),
                    "updated_at": str(row.get("updated_at") or ""),
                }
            )
    return out