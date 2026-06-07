#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${1:-}"
if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
  echo "Usage: bash deployment/scripts/restore.sh deployment/backups/<timestamp>" >&2
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "Missing .env. Cannot determine database credentials." >&2
  exit 1
fi

env_value() {
  local name="$1"
  local line value
  line="$(grep -E "^[[:space:]]*${name}=" .env | tail -n 1 || true)"
  if [ -z "$line" ]; then
    return 0
  fi
  value="${line#*=}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

POSTGRES_USER="$(env_value POSTGRES_USER)"
POSTGRES_USER="${POSTGRES_USER:-audit_user}"
POSTGRES_DB="$(env_value POSTGRES_DB)"
POSTGRES_DB="${POSTGRES_DB:-audit_compliance}"

if [ -f "${BACKUP_DIR}/volumes.tar.gz" ]; then
  echo "Restoring archived Docker volume contents"
  docker compose down
  docker run --rm \
    -v audit-compliance_postgres_data:/volumes/postgres_data \
    -v audit-compliance_qdrant_data:/volumes/qdrant_data \
    -v audit-compliance_backend_storage:/volumes/backend_storage \
    -v "$(pwd)/${BACKUP_DIR}:/backup:ro" \
    alpine:3.20 \
    sh -c "tar -xzf /backup/volumes.tar.gz -C /volumes"
elif [ -f "${BACKUP_DIR}/postgres.sql" ]; then
  docker compose up -d postgres qdrant
  echo "Restoring PostgreSQL from ${BACKUP_DIR}/postgres.sql"
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "${BACKUP_DIR}/postgres.sql"
fi

docker compose up -d
echo "Restore complete."
