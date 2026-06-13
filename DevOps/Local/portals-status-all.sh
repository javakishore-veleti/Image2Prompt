#!/usr/bin/env bash
# Show status of all Angular portals.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Portals status"
for entry in "${PORTALS[@]}"; do
  IFS=":" read -r name port path <<<"$entry"
  status_proc "$name" "$port"
done
