from __future__ import annotations

from pathlib import Path

FNP_VERSION = 1
CONFIG_DIR = Path.home() / ".config" / "fnotify"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

EXIT_OK = 0
EXIT_VALIDATION = 2
EXIT_CONFIG = 3
EXIT_DELIVERY = 5
EXIT_RENDER = 10

VALID_STATUSES = frozenset(
    {"success", "partial", "failed", "cancelled", "running", "info"}
)
VALID_FORMATS = frozenset({"auto", "text", "card"})
VALID_IDENTITIES = frozenset({"auto", "bot", "user"})