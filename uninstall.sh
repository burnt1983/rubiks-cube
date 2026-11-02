#!/usr/bin/env bash
set -euo pipefail
rm -f \
  "${HOME}/.local/bin/rubik-cube" \
  "${HOME}/.local/share/applications/rubiks-cube.desktop"
rm -rf "${HOME}/.local/share/rubiks-cube"
echo "Removed Rubik's Cube. The window position in ~/.config/rubik-cube was left in place."
