# AI Audit & Compliance Assistant

AI Audit & Compliance Assistant is a full-stack compliance validation app. It lets users upload PDF, DOCX, or text documents, compare them against compliance rules, trace supporting evidence, score risk, and generate audit reports.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, JWT auth
- Frontend: Next.js, React, TypeScript, Tailwind CSS
- AI/RAG: Qdrant, sentence-transformers, BM25, optional reranking, OpenRouter/Groq/Gemini-compatible LLM providers
- Default local database: SQLite
- Optional local services: PostgreSQL and Qdrant through Docker Compose

## Project Structure

```text
backend/                FastAPI API, auth, services, agents, RAG pipeline, DB models
backend/alembic/        Database migrations
frontend/               Next.js app, dashboards, admin screens, upload/report flows
docs/                   Architecture, API, database, RAG, storage, and workflow docs
requirements.txt        Backend dependency list
docker-compose.dev.yml  Optional PostgreSQL and Qdrant local services
```

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer
- npm
- Docker Desktop, optional but recommended for PostgreSQL and Qdrant

## Quick Start

Clone the repository:

```bash
git clone https://github.com/Vikilokhande/rule-assitance.git
cd rule-assitance
```

Create the backend environment:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create your environment file:

```bash
copy .env.example .env
```

For a first local run, the defaults in `.env.example` use SQLite and local storage. Set `JWT_SECRET_KEY` to any strong random value before sharing the app.

Run database migrations:

```bash
alembic upgrade head
```

Start the backend:

```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the app:

```text
http://localhost:3000
```

The first registered user becomes an admin automatically. Later users are normal users unless their email is listed in `DEFAULT_ADMIN_EMAILS`.

## Full Local Services

To run PostgreSQL and Qdrant locally:

```bash
docker compose -f docker-compose.dev.yml up -d
```

Then update `.env`:

```env
DATABASE_URL=postgresql+psycopg://audit_user:audit_password@127.0.0.1:5432/audit_compliance
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=
```

Run migrations again after switching databases:

```bash
alembic upgrade head
```

## Environment Variables

Important backend values:

```env
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
CORS_ORIGINS=http://localhost:3000
DATABASE_URL=sqlite:///./audit_compliance_local.db
JWT_SECRET_KEY=change-this-local-secret
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_RULE_COLLECTION=compliance_rules
QDRANT_UPLOAD_COLLECTION=audit_document_chunks
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4.1-mini
GROQ_API_KEY=
GEMINI_API_KEY=
DEFAULT_ADMIN_EMAILS=
```

Important frontend values:

```env
NEXT_PUBLIC_API_BASE_URL=/api/backend
BACKEND_API_URL=http://127.0.0.1:8000/api/v1
```

`frontend/next.config.ts` proxies `/api/backend/*` to the FastAPI backend, so the frontend can run without extra browser CORS setup.

## Useful Commands

Backend:

```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
alembic revision --autogenerate -m "message"
alembic upgrade head
```

Frontend:

```bash
cd frontend
npm run dev
npm run build
npm run start
```

## API

Backend API docs are available after starting FastAPI:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

Main route groups:

- `/api/v1/auth`
- `/api/v1/users`
- `/api/v1/documents`
- `/api/v1/rules`
- `/api/v1/audits`
- `/api/v1/reports`
- `/api/v1/admin`
- `/api/v1/health`

## Notes

- `.env`, virtual environments, `node_modules`, logs, uploaded files, generated reports, and local storage are intentionally ignored.
- SQLite is enough to open and test the app locally.
- Qdrant and an LLM API key are required for complete AI/RAG audit analysis.
- Detailed system docs are in [docs/README.md](docs/README.md).
