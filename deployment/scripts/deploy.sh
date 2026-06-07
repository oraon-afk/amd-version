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

value_missing() {
  local value="$1"
  [ -z "$value" ] || [[ "$value" == \<* ]] || [ "$value" = "change-me" ]
}

require_var() {
  local name="$1"
  local value
  value="$(env_value "$name")"
  if value_missing "$value"; then
    missing+=("$name")
  fi
}

require_any() {
  local label="$1"
  shift
  local name value
  for name in "$@"; do
    value="$(env_value "$name")"
    if ! value_missing "$value"; then
      return 0
    fi
  done
  missing+=("$label")
}

required_vars=(
  DATABASE_URL
  POSTGRES_PASSWORD
  JWT_SECRET_KEY
  QDRANT_URL
)

missing=()
for name in "${required_vars[@]}"; do
  require_var "$name"
done

primary_provider="$(env_value PRIMARY_LLM_PROVIDER)"
if value_missing "$primary_provider"; then
  primary_provider="$(env_value LLM_PROVIDER)"
fi
if value_missing "$primary_provider"; then
  primary_provider="openrouter"
fi

case "${primary_provider,,}" in
  openrouter)
    require_var OPENROUTER_API_KEY
    require_var OPENROUTER_BASE_URL
    require_any "PRIMARY_MODEL or PRIMARY_LLM_MODEL or OPENROUTER_MODEL or LLM_MODEL" \
      PRIMARY_MODEL PRIMARY_LLM_MODEL OPENROUTER_MODEL LLM_MODEL
    ;;
  groq)
    require_var GROQ_API_KEY
    require_var GROQ_BASE_URL
    require_any "PRIMARY_MODEL or PRIMARY_LLM_MODEL or GROQ_MODEL or LLM_MODEL" \
      PRIMARY_MODEL PRIMARY_LLM_MODEL GROQ_MODEL LLM_MODEL
    ;;
  gemini|google|google-gemini)
    require_var GEMINI_API_KEY
    require_var GEMINI_API_URL
    require_any "PRIMARY_MODEL or PRIMARY_LLM_MODEL or GEMINI_MODEL or LLM_MODEL" \
      PRIMARY_MODEL PRIMARY_LLM_MODEL GEMINI_MODEL LLM_MODEL
    ;;
  *)
    missing+=("SUPPORTED_PRIMARY_LLM_PROVIDER")
    ;;
esac

require_any "AWS_ACCESS_KEY_ID or S3_ACCESS_KEY" AWS_ACCESS_KEY_ID S3_ACCESS_KEY
require_any "AWS_SECRET_ACCESS_KEY or S3_SECRET_KEY" AWS_SECRET_ACCESS_KEY S3_SECRET_KEY
require_any "AWS_REGION or S3_REGION" AWS_REGION S3_REGION
require_any "S3_RULE_BUCKET or S3_BUCKET" S3_RULE_BUCKET S3_BUCKET
require_any "S3_TEMP_UPLOAD_BUCKET or S3_TEMP_BUCKET or S3_BUCKET" S3_TEMP_UPLOAD_BUCKET S3_TEMP_BUCKET S3_BUCKET
require_any "S3_REPORT_BUCKET or S3_BUCKET" S3_REPORT_BUCKET S3_BUCKET

if [ "${#missing[@]}" -gt 0 ]; then
  echo "Required variables need values in .env: ${missing[*]}" >&2
  exit 1
fi

docker compose pull postgres qdrant nginx || true
docker compose build
docker compose up -d
"$ROOT_DIR/deployment/scripts/healthcheck.sh"
