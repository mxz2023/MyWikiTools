"""Watch a folder for new export.xml / ingest JSON (iCloud, Shortcuts drops)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from apple_health import import_xml, ingest

DEFAULT_WATCH_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "AHP"


def default_watch_dir() -> Path:
    import os

    env = os.environ.get("AHP_WATCH_DIR")
    if env:
        return Path(env).expanduser()
    return DEFAULT_WATCH_DIR


def _state_path(watch_dir: Path) -> Path:
    return watch_dir / ".ahp-watch-state.json"


def _load_state(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass
    return {}


def _save_state(path: Path, state: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def scan_once(
    watch_dir: Path,
    *,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Import new/changed .xml / .json files under watch_dir."""
    watch_dir.mkdir(parents=True, exist_ok=True)
    state_path = _state_path(watch_dir)
    state = {} if force else _load_state(state_path)
    results: list[dict[str, Any]] = []

    patterns = ("*.xml", "*.json")
    files: list[Path] = []
    for pat in patterns:
        files.extend(sorted(watch_dir.glob(pat)))

    for f in files:
        if f.name.startswith(".ahp"):
            continue
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        key = str(f.resolve())
        if not force and state.get(key) == mtime:
            continue
        if f.suffix.lower() == ".xml":
            body = import_xml.import_export_xml(f)
        else:
            doc = json.loads(f.read_text(encoding="utf-8"))
            body = ingest.ingest_document(doc)
        state[key] = mtime
        results.append({"file": str(f), "result": body})

    _save_state(state_path, state)
    return results


def watch_loop(
    watch_dir: Path,
    interval_sec: float,
    *,
    on_batch: Callable[[list[dict[str, Any]]], None] | None = None,
) -> None:
    while True:
        batch = scan_once(watch_dir)
        if batch and on_batch:
            on_batch(batch)
        time.sleep(max(5.0, interval_sec))
