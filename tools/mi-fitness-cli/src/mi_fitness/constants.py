"""Paths, defaults, and exit codes."""

from pathlib import Path

HEALTH_API_BASE = "https://hlth.io.mi.com"

CONFIG_DIR = Path.home() / ".config" / "mi-fitness"
SESSION_FILE = CONFIG_DIR / "session.json"
DATA_DIR = Path.home() / ".local" / "share" / "mi-fitness"
DB_FILE = DATA_DIR / "health.db"

SYNC_TYPES = (
    "daily_activity",
    "sleep",
    "heart_rate",
    "workouts",
    "body_measurements",
)

EXIT_GENERAL = 1
EXIT_CONFIG = 3
EXIT_AUTH = 4
