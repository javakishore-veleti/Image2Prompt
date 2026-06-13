#!/usr/bin/env bash
# Bring up local containers (Postgres). Starts our Postgres container ONLY if no
# Postgres is already running on this laptop — otherwise the existing one is reused
# (services just create their img2pmpt_* schemas in it).
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

echo "==> Containers: bringing up Postgres"
if port_in_use "$PG_PORT"; then
  c_dim "  Postgres already listening on :$PG_PORT — reusing it (not starting our container)."
else
  c_green "  No Postgres on :$PG_PORT — starting img2pmpt-postgres container."
  docker compose -f "$LOCAL_DIR/postgres/docker-compose.yaml" up -d
  echo "  waiting for Postgres to accept connections..."
  for _ in $(seq 1 30); do
    if port_in_use "$PG_PORT"; then c_green "  Postgres is up on :$PG_PORT"; break; fi
    sleep 1
  done
fi
