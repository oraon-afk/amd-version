# Production Deployment

This package adds deployment infrastructure only. It does not change backend routes, frontend pages, auth flow, database schema, business logic, or agent workflow.

## 1. VM Requirements

Recommended Ubuntu VM:

- Ubuntu 22.04 LTS or 24.04 LTS
- 4 vCPU minimum, 8 vCPU recommended
- 16 GB RAM minimum because `sentence-transformers` and model loading can be memory-heavy
- 40 GB disk minimum, more for document uploads and Qdrant data
- Inbound port `80` open
- Outbound internet access for container image pulls, Python packages, npm packages, LLM providers, S3, and model downloads

## 2. Clone Instructions

```bash
git clone <repo>
cd <repo>
```

Install VM dependencies and Docker:

```bash
bash deployment/vm/setup_vm.sh
```

## 3. Environment Setup

Create `.env`:

```bash
cp .env.example .env
nano .env
```

Fill at minimum:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `QDRANT_URL`
- At least one LLM provider key/base URL/model
- S3 credentials and bucket names for full storage workflow

For the bundled compose database:

```text
DATABASE_URL=postgresql+psycopg://audit_user:<set-postgres-password>@postgres:5432/audit_compliance
POSTGRES_DB=audit_compliance
POSTGRES_USER=audit_user
POSTGRES_PASSWORD=<set-postgres-password>
QDRANT_URL=http://qdrant:6333
NEXT_PUBLIC_API_BASE_URL=/api/backend
BACKEND_API_URL=http://backend:8000/api/v1
```

## 4. Docker Build

Build all production services:

```bash
docker compose build
```

Build directly from the deployment compose file:

```bash
docker compose -f deployment/compose/docker-compose.prod.yml build
```

## 5. Docker Compose

Start from the repository root:

```bash
docker compose up -d
```

View status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

## 6. Production Startup

Recommended startup:

```bash
bash deployment/scripts/deploy.sh
```

Simple startup:

```bash
bash deployment/scripts/start.sh
```

The production stack includes:

- `postgres`
- `qdrant`
- `backend`
- `frontend`
- `nginx`

The app is served through Nginx on `http://<vm-host>/`.

## 7. Backup And Restore

Create a backup:

```bash
bash deployment/scripts/backup.sh
```

Restore from a backup:

```bash
bash deployment/scripts/restore.sh deployment/backups/<timestamp>
```

The backup script captures:

- PostgreSQL SQL dump
- Docker volume archive for Postgres, Qdrant, and backend local storage

For S3-backed objects, keep bucket lifecycle and versioning policies at the provider level.

## 8. Monitoring

Monitoring assets:

- `deployment/monitoring/prometheus.yml`
- `deployment/monitoring/grafana-dashboard.json`
- `deployment/monitoring/logging.md`

Current compose does not start Prometheus/Grafana by default because they are optional operational tooling. Add them to a separate monitoring compose profile if needed.

Health check:

```bash
bash deployment/scripts/healthcheck.sh
```

## 9. Troubleshooting

Check containers:

```bash
docker compose ps
```

Backend logs:

```bash
docker compose logs -f backend
```

Frontend logs:

```bash
docker compose logs -f frontend
```

Nginx logs:

```bash
docker compose logs -f nginx
```

Common issues:

- `DATABASE_URL is not configured`: fill `.env`.
- Database hostname errors: use `postgres` as the hostname inside compose.
- Qdrant errors: use `QDRANT_URL=http://qdrant:6333` for bundled Qdrant.
- LLM warnings: configure provider API key, base URL, and model.
- S3 warnings: configure credentials and bucket variables.
- Frontend cannot reach API: keep `NEXT_PUBLIC_API_BASE_URL=/api/backend` and `BACKEND_API_URL=http://backend:8000/api/v1`.

## 10. Upgrade Procedure

```bash
git pull
docker compose build
docker compose up -d
bash deployment/scripts/healthcheck.sh
```

Before a major upgrade:

```bash
bash deployment/scripts/backup.sh
```
