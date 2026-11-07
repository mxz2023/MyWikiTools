"""Defaults and exit codes."""

from pathlib import Path

# Default China region hosts (override via profile / env / flags)
DEFAULT_API_BASE = "https://personal.connectapi.garmin.cn"
DEFAULT_TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"

CONFIG_DIR = Path.home() / ".config" / "garmin-personal"
CONFIG_FILE = CONFIG_DIR / "config.toml"
TOKEN_CACHE_DIR = CONFIG_DIR / "tokens"

# Exit codes (documented in --help)
EXIT_OK = 0
EXIT_GENERAL = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_HTTP_4XX = 4
EXIT_HTTP_5XX = 5
