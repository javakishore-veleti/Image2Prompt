#!/usr/bin/env bash
# Stop our local Postgres container. If Postgres was an external/pre-existing one
# (we never started a container), this is a no-op for that server.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Containers: stopping img2pmpt-postgres (if we started it)"
if docker ps -a --format '{{.Names}}' | grep -q '^img2pmpt-postgres$'; then
  docker compose -f "$LOCAL_DIR/postgres/docker-compose.yaml" down
  c_green "  img2pmpt-postgres stopped"
else
  c_dim "  no img2pmpt-postgres container found (external Postgres left untouched)"
fi
