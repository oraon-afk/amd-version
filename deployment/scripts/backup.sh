#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${BACKUP_DIR:-deployment/backups/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$BACKUP_DIR"

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

echo "Writing PostgreSQL backup to ${BACKUP_DIR}/postgres.sql"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "${BACKUP_DIR}/postgres.sql"

echo "Archiving Docker volumes"
docker run --rm \
  -v audit-compliance_postgres_data:/volumes/postgres_data:ro \
  -v audit-compliance_qdrant_data:/volumes/qdrant_data:ro \
  -v audit-compliance_backend_storage:/volumes/backend_storage:ro \
  -v "$(pwd)/${BACKUP_DIR}:/backup" \
  alpine:3.20 \
  sh -c "tar -czf /backup/volumes.tar.gz -C /volumes ."

echo "Backup complete: ${BACKUP_DIR}"
