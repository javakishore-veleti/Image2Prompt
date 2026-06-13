#!/usr/bin/env bash
# Show status of local containers (Postgres).
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Containers status"
if port_in_use "$PG_PORT"; then
  c_green "  Postgres: listening on :$PG_PORT"
else
  c_red "  Postgres: not listening on :$PG_PORT"
fi
if docker ps --format '{{.Names}}' | grep -q '^img2pmpt-postgres$'; then
  c_green "  img2pmpt-postgres container: running"
else
  c_dim "  img2pmpt-postgres container: not running (external Postgres may be in use)"
fi
