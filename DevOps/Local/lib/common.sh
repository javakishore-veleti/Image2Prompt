#!/usr/bin/env bash
# Shared helpers + topology for the Local DevOps scripts.
# Sourced by the start/stop/status scripts; not meant to be run directly.

set -euo pipefail

SCRIPT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DIR="$(cd "$SCRIPT_LIB_DIR/.." && pwd)"
REPO_ROOT="$(cd "$LOCAL_DIR/../.." && pwd)"
RUN_DIR="$LOCAL_DIR/.run"
mkdir -p "$RUN_DIR"

# First-run convenience: seed the repo-root .env from .env.example when missing,
# so `npm run local:*:start-all` works on a fresh clone without a manual copy.
# (Runs before the .env is sourced below; .env is gitignored.)
if [[ ! -f "$REPO_ROOT/.env" && -f "$REPO_ROOT/.env.example" ]]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  printf '\033[32m%s\033[0m\n' "  created .env from .env.example (edit it to add real secrets)"
fi

# Load the global repo-root .env if present (single source of truth for local
# dev: DATABASE_URL, JWT_SECRET, OTEL_*, CAF_SECRET_*, etc.). A DevOps/Local/.env
# is still honored as an optional override layered on top.
for envfile in "$REPO_ROOT/.env" "$LOCAL_DIR/.env"; do
  if [[ -f "$envfile" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$envfile"
    set +a
  fi
done

PG_PORT="${PG_PORT:-5432}"

# Python services in start order (dependencies before the gateway).
# Format: "name:port:relative_path"
SERVICES=(
  "admin-service:8001:services/admin-service"
  "customer-service:8002:services/customer-service"
  "ai-adapters:8003:services/ai-adapters"
  "image-processing-service:8004:services/image-processing-service"
  "gateway:8000:services/gateway"
)

# Angular portals. Format: "name:port:relative_path"
PORTALS=(
  "customer-portal:4200:portals/customer-portal"
  "admin-portal:4300:portals/admin-portal"
)

# Observability stacks. Format: "name:port:container:compose_path_relative_to_LOCAL_DIR"
OBS_NETWORK="img2pmpt-observability"
OBSERVABILITY_STACKS=(
  "otel-collector:4317:img2pmpt-otel-collector:Observability/otel-collector/docker-compose.yaml"
  "jaeger:16686:img2pmpt-jaeger:Observability/jaeger/docker-compose.yaml"
  "prometheus:9090:img2pmpt-prometheus:Observability/prometheus/docker-compose.yaml"
  "grafana:3000:img2pmpt-grafana:Observability/grafana/docker-compose.yaml"
)

# Path to the python interpreter used to run services (override via PYTHON env).
PYTHON_BIN="${PYTHON:-$REPO_ROOT/.venv/bin/python}"

c_green() { printf '\033[32m%s\033[0m\n' "$1"; }
c_red()   { printf '\033[31m%s\033[0m\n' "$1"; }
c_dim()   { printf '\033[2m%s\033[0m\n' "$1"; }

port_in_use() {
  local port="$1"
  if command -v nc >/dev/null 2>&1; then
    nc -z localhost "$port" >/dev/null 2>&1
  else
    (exec 3<>"/dev/tcp/localhost/$port") >/dev/null 2>&1
  fi
}

pid_file()  { echo "$RUN_DIR/$1.pid"; }
log_file()  { echo "$RUN_DIR/$1.log"; }

is_running() {
  local name="$1" pf
  pf="$(pid_file "$name")"
  [[ -f "$pf" ]] && kill -0 "$(cat "$pf")" >/dev/null 2>&1
}

# start_proc <name> <workdir> <command...>
start_proc() {
  local name="$1"; shift
  local workdir="$1"; shift
  if is_running "$name"; then
    c_dim "  $name already running (pid $(cat "$(pid_file "$name")"))"
    return 0
  fi
  ( cd "$workdir" && nohup "$@" >"$(log_file "$name")" 2>&1 & echo $! >"$(pid_file "$name")" )
  sleep 0.3
  if is_running "$name"; then
    c_green "  started $name (pid $(cat "$(pid_file "$name")")) -> $(log_file "$name")"
  else
    c_red "  FAILED to start $name (see $(log_file "$name"))"
  fi
}

stop_proc() {
  local name="$1" pf
  pf="$(pid_file "$name")"
  if is_running "$name"; then
    kill "$(cat "$pf")" >/dev/null 2>&1 || true
    sleep 0.3
    c_green "  stopped $name"
  else
    c_dim "  $name not running"
  fi
  rm -f "$pf"
}

status_proc() {
  local name="$1" port="$2"
  if is_running "$name"; then
    c_green "  $name: RUNNING (pid $(cat "$(pid_file "$name")"), port $port)"
  elif port_in_use "$port"; then
    c_dim "  $name: port $port in use (not managed by these scripts)"
  else
    c_red "  $name: stopped"
  fi
}

# --- Docker container / observability-stack helpers ---
container_running() {
  docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^$1$"
}

ensure_obs_network() {
  docker network inspect "$OBS_NETWORK" >/dev/null 2>&1 || docker network create "$OBS_NETWORK" >/dev/null
}

# Start a stack only if neither our container nor anything else holds the port.
# ensure_stack <name> <port> <container> <compose_rel>
ensure_stack() {
  local name="$1" port="$2" container="$3" compose="$LOCAL_DIR/$4"
  if container_running "$container"; then
    c_dim "  $name: already running (ours: $container)"
  elif port_in_use "$port"; then
    c_dim "  $name: port $port already used by another container — reusing it (not starting ours)"
  else
    c_green "  $name: starting our container ($container)"
    docker compose -f "$compose" up -d
  fi
}

# Stop ONLY our container; never touch an external one.
# stop_stack <name> <container> <compose_rel>
stop_stack() {
  local name="$1" container="$2" compose="$LOCAL_DIR/$3"
  if container_running "$container"; then
    docker compose -f "$compose" down
    c_green "  $name: stopped ($container)"
  else
    c_dim "  $name: no '$container' running — left untouched (external/none)"
  fi
}

# status_stack <name> <port> <container>
status_stack() {
  local name="$1" port="$2" container="$3"
  if container_running "$container"; then
    c_green "  $name: RUNNING (ours: $container, port $port)"
  elif port_in_use "$port"; then
    c_dim "  $name: external container in use on port $port (another project)"
  else
    c_red "  $name: not running"
  fi
}
