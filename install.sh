#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/plugin"
DST="$HOME/.gemini/config/plugins/media-traffic-guard"

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -rf "$DST"
  echo "[OK] Uninstalled media-traffic-guard from $DST"
  exit 0
fi

PY_BIN="python3"
if ! command -v python3 >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PY_BIN="python"
  else
    echo "[ERROR] Python 3.8+ is required." >&2
    exit 1
  fi
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[WARN] ffmpeg not found in PATH. Install ffmpeg (e.g. brew install ffmpeg / apt install ffmpeg)." >&2
fi

mkdir -p "$DST/rules" "$DST/scripts"
cp "$SRC/plugin.json" "$DST/plugin.json"
cp "$SRC/rules/AGENTS.md" "$DST/rules/AGENTS.md"
cp "$SRC/scripts/media_guard.py" "$DST/scripts/media_guard.py"
sed "s|python \./scripts/media_guard.py|$PY_BIN ./scripts/media_guard.py|g" \
  "$SRC/hook-config.template.json" > "$DST/hooks.json"

echo "[OK] Installed media-traffic-guard to $DST (python=$PY_BIN)"
echo "     Start a new Antigravity conversation to activate. Uninstall: ./install.sh --uninstall"
