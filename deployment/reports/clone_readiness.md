# Clone Readiness

## Target Flow

Fresh VM flow:

```bash
git clone <repo>
cd <repo>
cp .env.example .env
# configure .env secrets
docker compose up -d
```

The root `docker-compose.yml` includes `deployment/compose/docker-compose.prod.yml`, so the root command is available.

Fallback for older Compose versions:

```bash
docker compose -f deployment/compose/docker-compose.prod.yml up -d --build
```

## Checks Performed Locally

- Repository source scan: passed.
- Python production dependency install: passed.
- Python production import smoke test: passed.
- Frontend lockfile dry run: passed.
- Frontend production build: passed.
- Deployment YAML syntax parse: passed.

## Checks Blocked Locally

- `docker build`: not run because Docker is not installed on this workstation.
- `docker compose up`: not run because Docker is not installed on this workstation.

Docker availability check result:

```text
docker: The term 'docker' is not recognized...
```

The VM scripts install Docker and Docker Compose on Ubuntu before startup.

## Missing Files

No required deployment package files are missing.

## Missing Imports

No missing Python imports after installing `requirements-production.txt`.

No unresolved frontend imports detected during `npm run build`.

## Missing Environment Values

The repository provides placeholders only. A VM operator must fill:

- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY`
- LLM provider credentials and models
- S3 credentials and buckets
- `QDRANT_API_KEY` if the chosen Qdrant deployment requires one

## Startup Scripts

Detected and added:

- `deployment/scripts/start.sh`
- `deployment/scripts/stop.sh`
- `deployment/scripts/deploy.sh`
- `deployment/scripts/healthcheck.sh`
- `deployment/scripts/backup.sh`
- `deployment/scripts/restore.sh`
- `deployment/vm/setup_vm.sh`

## Readiness Result

Clone readiness: conditionally ready.

The repository is ready for a fresh Ubuntu VM after `.env` is configured. Local Docker execution could not be verified on this Windows workstation because Docker is not installed.
