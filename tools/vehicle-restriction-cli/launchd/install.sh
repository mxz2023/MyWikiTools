#!/bin/sh
set -eu

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This installer requires macOS launchd." >&2
  exit 1
fi

CLI_PATH=$(command -v vehicle-restriction || true)
if [ -z "$CLI_PATH" ]; then
  echo "vehicle-restriction was not found on PATH. Install the CLI with pipx first." >&2
  exit 1
fi
"$CLI_PATH" --help >/dev/null

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STATE_DIR="$HOME/.local/share/vehicle-restriction-cli"
HELPER="$STATE_DIR/scheduler.py"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST="$PLIST_DIR/com.mxz2023.vehicle-restriction.refresh.plist"
LABEL="com.mxz2023.vehicle-restriction.refresh"
mkdir -p "$STATE_DIR" "$PLIST_DIR"
cp "$SCRIPT_DIR/scheduler.py" "$HELPER"
chmod 700 "$HELPER"

python3 - "$CLI_PATH" "$HELPER" "$STATE_DIR/state.json" "$STATE_DIR" "$PLIST" "$LABEL" <<'PLIST_PY'
from pathlib import Path
import plistlib
import sys

cli, helper, state, state_dir, plist_path, label = sys.argv[1:]
payload = {
    "Label": label,
    "ProgramArguments": ["/usr/bin/python3", helper, cli, state],
    "RunAtLoad": True,
    "KeepAlive": True,
    "EnvironmentVariables": {"TZ": "Asia/Shanghai"},
    "StandardOutPath": str(Path(state_dir) / "refresh.stdout.log"),
    "StandardErrorPath": str(Path(state_dir) / "refresh.stderr.log"),
}
path = Path(plist_path)
with path.open("wb") as stream:
    plistlib.dump(payload, stream, sort_keys=True)
path.chmod(0o600)
PLIST_PY

if command -v plutil >/dev/null 2>&1; then
  plutil -lint "$PLIST"
fi
uid=$(id -u)
launchctl bootout "gui/$uid" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$uid" "$PLIST"
echo "Installed $LABEL. It reads the CLI city registry and waits for each registered city's stored check date."
echo "Logs: $STATE_DIR/refresh.stdout.log and $STATE_DIR/refresh.stderr.log"
