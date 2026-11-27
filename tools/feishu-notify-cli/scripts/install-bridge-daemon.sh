#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$(command -v python3)}"
WORKSPACE="${WORKSPACE:-$HOME/Code/MyWikiTools}"
HOME_DIR="${HOME}"
LABEL="com.fnotify.bridge"
AGENTS_DIR="$HOME_DIR/Library/LaunchAgents"
PLIST="$AGENTS_DIR/$LABEL.plist"
TEMPLATE="$REPO_ROOT/scripts/com.fnotify.bridge.plist.template"
ENV_FILE="$HOME_DIR/.config/fnotify/bridge.env"
EXAMPLE="$HOME_DIR/.config/fnotify/bridge.env.example"

mkdir -p "$HOME_DIR/.config/fnotify/logs" "$AGENTS_DIR"

if [[ ! -f "$ENV_FILE" ]] && [[ -n "${HTTP_PROXY:-}${HTTPS_PROXY:-}" ]]; then
  {
    echo "# launchd 不会继承终端代理；Codex 连 OpenAI 需要与你在终端里一致"
    [[ -n "${HTTP_PROXY:-}" ]] && echo "HTTP_PROXY=${HTTP_PROXY}"
    [[ -n "${HTTPS_PROXY:-}" ]] && echo "HTTPS_PROXY=${HTTPS_PROXY}"
    [[ -n "${ALL_PROXY:-}" ]] && echo "ALL_PROXY=${ALL_PROXY}"
    echo "NO_PROXY=${NO_PROXY:-localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8}"
  } >"$ENV_FILE"
  echo "Wrote $ENV_FILE from current shell proxy."
fi

if [[ ! -f "$EXAMPLE" ]]; then
  cat >"$EXAMPLE" <<'EOF'
# Copy to bridge.env and restart daemon: launchctl kickstart -k gui/$(id -u)/com.fnotify.bridge
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
ALL_PROXY=socks5://127.0.0.1:7890
NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8
EOF
fi

EXTRA_ENV_PLIST=""
if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    val="${val#"${val%%[![:space:]]*}"}"
    [[ -z "$key" ]] && continue
    val="${val//&/&amp;}"
    val="${val//</&lt;}"
    val="${val//>/&gt;}"
    EXTRA_ENV_PLIST+="    <key>${key}</key>
    <string>${val}</string>
"
  done <"$ENV_FILE"
fi

TMP_PLIST="$(mktemp)"
sed \
  -e "s|@PYTHON@|$PYTHON|g" \
  -e "s|@WORKSPACE@|$WORKSPACE|g" \
  -e "s|@PYTHONPATH@|$REPO_ROOT/src|g" \
  -e "s|@HOME@|$HOME_DIR|g" \
  "$TEMPLATE" >"$TMP_PLIST"
python3 - "$TMP_PLIST" "$PLIST" "$EXTRA_ENV_PLIST" <<'PY'
import sys
from pathlib import Path

src, dst, extra = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
text = src.read_text(encoding="utf-8")
text = text.replace("@EXTRA_ENV_PLIST@", extra)
dst.write_text(text, encoding="utf-8")
PY
rm -f "$TMP_PLIST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl start "$LABEL" 2>/dev/null || true

echo "Installed $PLIST (KeepAlive). Logs: ~/.config/fnotify/logs/bridge-daemon.log"
echo "Proxy env: ${ENV_FILE} (edit + kickstart to apply)"
echo "Dev auto-reload (terminal): $REPO_ROOT/scripts/bridge-watch-reload.sh"
echo "Dev auto-reload (login): $REPO_ROOT/scripts/install-bridge-watch.sh"
echo "Stop: launchctl bootout gui/$(id -u)/com.fnotify.bridge"