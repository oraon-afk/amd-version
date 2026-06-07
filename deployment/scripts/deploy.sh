#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Run: bash deployment/vm/setup_vm.sh" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is not installed. Run: bash deployment/vm/setup_vm.sh" >&2
  exit 1
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Fill required secrets, then rerun this script." >&2
  exit 1
fi

required_vars=(
  DATABASE_URL
  POSTGRES_PASSWORD
  JWT_SECRET_KEY
  QDRANT_URL
)

missing=()
for name in "${required_vars[@]}"; do
  if ! grep -Eq "^${name}=.+" .env || grep -Eq "^${name}=<" .env; then
    missing+=("$name")
  fi
done

if [ "${#missing[@]}" -gt 0 ]; then
  echo "Required variables need values in .env: ${missing[*]}" >&2
  exit 1
fi

docker compose pull postgres qdrant nginx || true
docker compose build
docker compose up -d
"$ROOT_DIR/deployment/scripts/healthcheck.sh"
