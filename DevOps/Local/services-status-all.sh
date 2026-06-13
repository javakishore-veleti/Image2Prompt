#!/usr/bin/env bash
# Show status of all Python microservices.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Services status"
for entry in "${SERVICES[@]}"; do
  IFS=":" read -r name port path <<<"$entry"
  status_proc "$name" "$port"
done
