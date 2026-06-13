#!/usr/bin/env bash
# Full local shutdown: portals, then services, then containers.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Full local shutdown"
bash "$DIR/portals-stop-all.sh"   || true
bash "$DIR/services-stop-all.sh"  || true
bash "$DIR/all-down.sh"           || true
echo "==> Done."
