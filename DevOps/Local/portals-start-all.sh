#!/usr/bin/env bash
# Start all Angular portals (ng serve) in the background.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Portals: starting all"
for entry in "${PORTALS[@]}"; do
  IFS=":" read -r name port path <<<"$entry"
  if [[ ! -d "$REPO_ROOT/$path/node_modules" ]]; then
    c_red "  $name: node_modules missing — run 'npm install' in $path first"
    continue
  fi
  start_proc "$name" "$REPO_ROOT/$path" npm start
done
