#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "${SCRIPT_DIR}/ops"
docker compose -f docker-compose.ops.yml up -d

if ! python3 bootstrap_openobserve_assets.py; then
  echo "warning: OpenObserve dashboard bootstrap failed" >&2
fi
