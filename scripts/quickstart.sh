#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON=${PYTHON:-python3}
VENV_DIR=${VENV_DIR:-venv}

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[quickstart] Creating venv: $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "[quickstart] Installing Stratum (editable + dev deps)"
pip install -U pip >/dev/null
pip install -e ".[dev]" >/dev/null

echo "[quickstart] Starting GROBID container (if not already running)"
if ! curl -fsS http://127.0.0.1:8070/api/isalive >/dev/null 2>&1; then
  docker run -d --rm --name stratum-grobid -p 8070:8070 lfoppiano/grobid:0.8.0 >/dev/null
  echo "[quickstart] Waiting for GROBID to become healthy..."
  for i in {1..30}; do
    if curl -fsS http://127.0.0.1:8070/api/isalive >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

echo "[quickstart] Running: stratum doctor"
stratum doctor

echo ""
echo "[quickstart] Ready. Example run:"
echo "  stratum analyze <DOI> --max-depth 2 --max-citations 3"
echo ""
