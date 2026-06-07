#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

bash "$ROOT_DIR/deployment/vm/install_dependencies.sh"
bash "$ROOT_DIR/deployment/vm/install_docker.sh"

cd "$ROOT_DIR"
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example."
fi

echo "VM setup complete."
echo "Next:"
echo "  1. Edit .env and fill secrets."
echo "  2. Run: docker compose up -d"
echo "  3. Run: bash deployment/scripts/healthcheck.sh"
