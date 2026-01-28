#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR=${VENV_DIR:-venv}

if [[ ! -x "$VENV_DIR/bin/stratum" ]]; then
  echo "[run] Stratum venv not ready. Run: ./scripts/quickstart.sh" >&2
  exit 1
fi

exec "$VENV_DIR/bin/stratum" "$@"
