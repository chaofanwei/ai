#!/usr/bin/env bash
# md-2-pdf entry script.
# Usage:
#   ./md2pdf.sh <input.md> [output.pdf]
#
# Auto-installs node deps on first run.
# Auto-detects system Chrome (override with CHROME_PATH env var).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Optional: load user shared env (paths to node etc.) if present
if [ -f "$HOME/ai/shells/init.sh" ]; then
  # shellcheck disable=SC1090,SC1091
  source "$HOME/ai/shells/init.sh"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[md2pdf] ERROR: node not found in PATH" >&2
  exit 1
fi

if [ ! -d node_modules ]; then
  echo "[md2pdf] first run: installing node dependencies (this may take ~30s) ..."
  if command -v npm >/dev/null 2>&1; then
    PUPPETEER_SKIP_DOWNLOAD=true PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true npm install --no-audit --no-fund --loglevel=error
  else
    echo "[md2pdf] ERROR: npm not found in PATH" >&2
    exit 1
  fi
fi

if [ $# -lt 1 ]; then
  echo "Usage: $(basename "$0") <input.md> [output.pdf]" >&2
  exit 1
fi

exec node convert.mjs "$@"
