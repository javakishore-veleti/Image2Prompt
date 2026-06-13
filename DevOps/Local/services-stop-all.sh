#!/usr/bin/env bash
# Stop all Python microservices (reverse start order).
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Services: stopping all"
for (( idx=${#SERVICES[@]}-1 ; idx>=0 ; idx-- )); do
  IFS=":" read -r name port path <<<"${SERVICES[$idx]}"
  stop_proc "$name"
done
