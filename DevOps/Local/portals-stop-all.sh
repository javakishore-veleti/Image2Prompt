#!/usr/bin/env bash
# Stop all Angular portals.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Portals: stopping all"
for entry in "${PORTALS[@]}"; do
  IFS=":" read -r name port path <<<"$entry"
  stop_proc "$name"
done
