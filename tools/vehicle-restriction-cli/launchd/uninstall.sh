#!/bin/sh
set -eu

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This uninstaller requires macOS launchd." >&2
  exit 1
fi

LABEL="com.mxz2023.vehicle-restriction.refresh"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
uid=$(id -u)
launchctl bootout "gui/$uid" "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST" "$HOME/.local/share/vehicle-restriction-cli/scheduler.py"
echo "Removed $LABEL; policy state and logs were kept."
