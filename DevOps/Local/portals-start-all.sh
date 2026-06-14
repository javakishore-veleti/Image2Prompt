#!/usr/bin/env bash
# Start all Angular portals (ng serve) in the background.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Portals: starting all"
for entry in "${PORTALS[@]}"; do
  IFS=":" read -r name port path <<<"$entry"
  # Install npm deps on first run (only when node_modules is missing).
  ensure_portal_deps "$name" "$path"
  start_proc "$name" "$REPO_ROOT/$path" npm start
done
