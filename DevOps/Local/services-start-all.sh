#!/usr/bin/env bash
# Start all Python microservices (uvicorn) in the background.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Services: starting all"
# Create the venv + install deps on first run (idempotent; REINSTALL=1 forces).
ensure_venv_deps
if [[ ! -x "$PYTHON_BIN" ]]; then
  c_red "  Python interpreter not found at $PYTHON_BIN"
  c_dim  "  Create it: python -m venv .venv && .venv/bin/pip install -e services/shared (+ each service's requirements)"
  exit 1
fi
for entry in "${SERVICES[@]}"; do
  IFS=":" read -r name port path <<<"$entry"
  start_proc "$name" "$REPO_ROOT/$path" \
    "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port "$port"
done
