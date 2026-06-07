#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Fill secrets before starting services." >&2
  exit 1
fi

bash deployment/scripts/start.sh
bash deployment/scripts/healthcheck.sh
