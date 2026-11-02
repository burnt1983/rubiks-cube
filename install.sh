#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
BIN="${HOME}/.local/bin"
SHARE="${HOME}/.local/share/rubiks-cube"
APPS="${HOME}/.local/share/applications"

mkdir -p "$BIN" "$SHARE" "$APPS"
install -m 0755 "$ROOT/rubik.py" "$SHARE/rubik.py"
install -m 0644 "$ROOT/index.html" "$SHARE/index.html"
mkdir -p "$SHARE/vendor"
cp -a "$ROOT/vendor/." "$SHARE/vendor/"
# Unpack beside the installed script. The page imports these local files.
python3 "$SHARE/rubik.py" --unpack
ln -sfn "$SHARE/rubik.py" "$BIN/rubik-cube"

sed "s|^Exec=rubik-cube$|Exec=${BIN}/rubik-cube|" \
    "$ROOT/data/rubiks-cube.desktop" > "$APPS/rubiks-cube.desktop"
chmod 0644 "$APPS/rubiks-cube.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi

echo "Installed Rubik's Cube."
echo "  Run: rubik-cube"
echo "  It does not start at login."
