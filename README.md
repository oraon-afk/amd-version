# AI-Driven Audit & Compliance Assistant

Enterprise MVP architecture for an AI-powered audit and compliance validation platform with evidence tracing.

This repository contains a working FastAPI + Next.js implementation for an AI-powered audit and compliance validation platform with evidence tracing, JWT auth, role-based admin controls, local document lifecycle storage, PostgreSQL persistence, Qdrant retrieval, and OpenRouter LLM analysis.

## Goal

The platform validates uploaded PDF or text documents against compliance rules and regulatory policies. It uses hybrid RAG to retrieve relevant rules, compare them against uploaded documents, detect violations or missing clauses, trace evidence, generate explainable reports, and assign risk/confidence scores.

## Target Stack

- Frontend: Next.js, React, TypeScript, TailwindCSS
- Backend: Python, FastAPI
- AI/RAG: sentence-transformers embeddings, hybrid retrieval, reranking
- Database: PostgreSQL Cloud
- Vector database: Qdrant Cloud
- Storage: local `storage/temp`, `storage/rules`, `storage/compliance`, and `storage/policies` directories
- Authentication: JWT with hashed passwords

## Core Workflow

```text
Register/Login
  -> Dashboard
  -> Upload PDF/Text
  -> Document Processing
  -> Hybrid Retrieval
  -> Compliance Validation
  -> Evidence Tracing
  -> Risk Scoring
  -> Audit Report Generation
  -> History Storage
```

## Repository Map

```text
backend/      FastAPI application, agents, RAG pipeline, services, persistence
frontend/     Next.js application, dashboard, upload flow, evidence UI
docs/         Architecture, API, storage, RAG, roadmap, naming guidance
```

Start with the docs in this order:

1. [Documentation Index](docs/README.md)
2. [Architecture](docs/architecture.md)
3. [Directory Structure](docs/directory-structure.md)
4. [RAG Pipeline](docs/rag-pipeline.md)
5. [API Structure](docs/api-structure.md)
6. [Data And Storage](docs/data-and-storage.md)
7. [Development Roadmap](docs/development-roadmap.md)
8. [Database Schema](docs/database-schema.sql)

## Setup

1. Copy `.env.example` to `.env` and set `DATABASE_URL`, `JWT_SECRET_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `OPENROUTER_API_KEY`, and the two collection names:

```text
QDRANT_RULE_COLLECTION=compliance_rules
QDRANT_UPLOAD_COLLECTION=audit_document_chunks
```

2. Install backend dependencies:

```bash
python -m pip install -e backend
```

3. Start the backend from the repository root:

```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

4. Install and run the frontend:

```bash
cd frontend
npm install
npm run dev
```

5. Open `http://localhost:3000`. The first registered account becomes `ADMIN`; later registrations become `USER` unless their email is listed in `DEFAULT_ADMIN_EMAILS`.

## API Surface

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/audit/run`
- `GET /api/audit/report/{id}`
- `GET /api/admin/users`
- `GET /api/admin/documents`
- `POST /api/admin/rules/upload`
- `DELETE /api/admin/document/{id}`

Versioned routes are also available under `/api/v1`.

## Storage Lifecycle

Admin rule documents are permanent and stored under `storage/rules`, `storage/compliance`, or `storage/policies`. User uploads are stored under `storage/temp`, deleted after audit completion, and also swept by a cleanup worker after `TEMP_DOCUMENT_RETENTION_HOURS`.
