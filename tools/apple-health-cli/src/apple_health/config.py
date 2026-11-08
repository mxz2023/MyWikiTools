"""Local data directories."""

from __future__ import annotations

from apple_health.constants import DATA_DIR


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
