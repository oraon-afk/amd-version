# Repository Audit

## Scope

Scanned source paths:

- Backend: `backend/**`, including `app`, `api`, `auth`, `core`, `db`, `services`, `agents`, `workers`, `storage`, and `rag`.
- Frontend: `frontend/**`, including `src/app`, `components`, `features`, `services`, `lib`, and framework config.
- Existing deployment-adjacent files: `docker-compose.dev.yml`, `requirements.txt`, `backend/pyproject.toml`, `frontend/package.json`, `frontend/package-lock.json`, `.env.example`.

Ignored generated paths during audit: `.venv`, `frontend/node_modules`, `frontend/.next`, `__pycache__`, `.pytest_cache`, logs, and runtime `storage`.

## Backend Runtime

- Framework: FastAPI application at `backend.app.main:app`.
- API router prefix: `API_V1_PREFIX`, default `/api/v1`.
- Production command added: `gunicorn backend.app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`.
- Health endpoints detected:
  - `/api/v1/health`
  - `/api/v1/health/database`
  - `/api/v1/health/vector`
  - `/api/v1/health/storage`
  - `/api/v1/health/llm`
  - `/api/v1/health/embeddings`
  - `/api/v1/health/auth`
  - `/api/v1/health/config`

## Frontend Runtime

- Framework: Next.js app router in `frontend/src/app`.
- Production build command: `npm run build`.
- Production runtime command: `npm start`.
- API access:
  - Browser client default: `NEXT_PUBLIC_API_BASE_URL` or `/api/backend`.
  - Next rewrite upstream: `BACKEND_API_URL` or `http://127.0.0.1:8000/api/v1`.

## Third-Party Backend Imports

Detected production packages:

- FastAPI stack: `fastapi`, `uvicorn`, `starlette`, `pydantic`, `pydantic-settings`, `python-multipart`, `email-validator`.
- Database stack: `sqlalchemy`, `psycopg`, `alembic`.
- Auth stack: `bcrypt`, `passlib`, `python-jose`, `cryptography`.
- Storage stack: `boto3`, `botocore`.
- Vector stack: `qdrant-client`, `sentence-transformers`.
- AI stack: `openai`, `json-repair`, `langgraph`, `langchain-text-splitters`.
- Retrieval and parsing: `rank-bm25`, `pymupdf`, `pdfplumber`, `pypdf`, `python-docx`.
- Websocket-capable server transport: `uvicorn[standard]` includes websocket dependencies, but no application WebSocket route was detected.

## Frontend Imports

External package imports detected:

- `next`, `react`, `react-dom`
- `@tanstack/react-query`
- `axios`
- `framer-motion`
- `lucide-react`
- `react-hook-form`
- `@hookform/resolvers`
- `zod`
- `recharts`
- `class-variance-authority`
- `clsx`
- `tailwind-merge`
- Build toolchain: `tailwindcss`, `@tailwindcss/postcss`, `postcss`, `autoprefixer`, `typescript`, `eslint`, `eslint-config-next`

Path alias `@/*` resolves to `frontend/src/*` through the existing TypeScript/Next setup.

## Services Detected

Included in production compose:

- `backend`: FastAPI API and workflow runtime.
- `frontend`: Next.js production server.
- `nginx`: edge reverse proxy, gzip, cache headers, and API routing.
- `postgres`: required when `DATABASE_URL` points at the local compose database.
- `qdrant`: required vector database.

External services configured by environment:

- S3-compatible object storage through AWS SDK variables and bucket variables.
- OpenRouter, Groq, or Gemini LLM providers.
- Hugging Face model download/runtime through `sentence-transformers` model names.

Services not added because code usage was not detected:

- Redis
- Chroma
- MinIO
- Supabase client SDK
- Dedicated WebSocket service

## Database

- SQLAlchemy engine is created from `DATABASE_URL`.
- PostgreSQL and SQLite URLs are supported by code.
- Production compose provides PostgreSQL 16.
- The app can auto-create tables when `AUTO_CREATE_TABLES=true`; no schema or migration code was changed.

## Vector Database

- Qdrant client uses `QDRANT_URL`, optional `QDRANT_API_KEY`, and collection names from environment.
- Collections detected:
  - `QDRANT_RULE_COLLECTION`
  - `QDRANT_UPLOAD_COLLECTION`

## Storage

- Local runtime storage root is controlled by `STORAGE_ROOT`.
- S3-compatible storage is configured with AWS/S3 environment variables.
- Production compose mounts `backend_storage` at `/app/storage`.

## AI Providers

Detected providers:

- OpenRouter through OpenAI-compatible client.
- Groq through OpenAI-compatible client.
- Gemini through direct HTTP provider handling.

At least one configured provider is required for complete audit analysis.

## Deployment Decision

The package adds only deployment infrastructure:

- Dockerfiles, compose files, Nginx config, scripts, VM setup, monitoring assets, reports, and deployment README.
- `.env.example` was updated to include safe deployment defaults and compose variables.
- No business logic, routes, schema, auth flow, agent workflow, frontend pages, or backend services were modified.
