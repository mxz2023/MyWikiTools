"""Defaults and exit codes."""

from pathlib import Path

DATA_DIR = Path.home() / ".local" / "share" / "apple-health"
DB_FILE = DATA_DIR / "health.db"

EXIT_OK = 0
EXIT_GENERAL = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
