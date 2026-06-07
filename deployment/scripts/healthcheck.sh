#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1}"
BACKEND_HEALTH="${BACKEND_HEALTH:-${BASE_URL}/api/backend/health}"
FRONTEND_URL="${FRONTEND_URL:-${BASE_URL}/login}"

check_http() {
  local name="$1"
  local url="$2"
  local expected="${3:-200}"
  local status

  status="$(curl -fsS -o /tmp/deployment-healthcheck.out -w "%{http_code}" "$url" || true)"
  if [ "$status" != "$expected" ]; then
    echo "FAIL ${name}: expected HTTP ${expected}, got ${status:-none} at ${url}" >&2
    if [ -s /tmp/deployment-healthcheck.out ]; then
      cat /tmp/deployment-healthcheck.out >&2 || true
      echo >&2
    fi
    return 1
  fi
  echo "OK   ${name}: ${url}"
}

check_http "nginx" "${BASE_URL}/healthz"
check_http "frontend" "$FRONTEND_URL"
check_http "backend" "$BACKEND_HEALTH"
check_http "database" "${BACKEND_HEALTH}/database"
check_http "vector" "${BACKEND_HEALTH}/vector"
check_http "storage" "${BACKEND_HEALTH}/storage"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose ps
fi
