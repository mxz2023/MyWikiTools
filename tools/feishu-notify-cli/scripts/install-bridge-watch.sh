#!/usr/bin/env bash
# Login-time file watcher: kickstart com.fnotify.bridge when feishu-notify-cli sources change.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$(command -v python3)}"
HOME_DIR="${HOME}"
LABEL="com.fnotify.bridge-watch"
AGENTS_DIR="$HOME_DIR/Library/LaunchAgents"
PLIST="$AGENTS_DIR/$LABEL.plist"
TEMPLATE="$REPO_ROOT/scripts/com.fnotify.bridge-watch.plist.template"
WATCH_SCRIPT="$REPO_ROOT/scripts/bridge-watch-reload.py"
CONFIG_FILE="${FNOTIFY_CONFIG_FILE:-$HOME_DIR/.config/fnotify/config.yaml}"

mkdir -p "$HOME_DIR/.config/fnotify/logs" "$AGENTS_DIR"

if [[ ! -f "$WATCH_SCRIPT" ]]; then
  echo "Missing $WATCH_SCRIPT" >&2
  exit 1
fi

TMP_PLIST="$(mktemp)"
sed \
  -e "s|@PYTHON@|$PYTHON|g" \
  -e "s|@WATCH_SCRIPT@|$WATCH_SCRIPT|g" \
  -e "s|@CONFIG_FILE@|$CONFIG_FILE|g" \
  -e "s|@REPO_ROOT@|$REPO_ROOT|g" \
  -e "s|@HOME@|$HOME_DIR|g" \
  "$TEMPLATE" >"$TMP_PLIST"
mv "$TMP_PLIST" "$PLIST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl start "$LABEL" 2>/dev/null || true

echo "Installed $PLIST (KeepAlive + RunAtLoad)."
echo "Watches: $REPO_ROOT/src/feishu_notify, tests, and $CONFIG_FILE (not runs.json)"
echo "Logs: ~/.config/fnotify/logs/bridge-watch.log"
echo "Stop: launchctl bootout gui/$(id -u)/$LABEL"
echo "Requires com.fnotify.bridge (install-bridge-daemon.sh)."