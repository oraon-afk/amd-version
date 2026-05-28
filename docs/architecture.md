# Architecture

## Architectural Style

Use a lean modular monolith. Keep one FastAPI backend and one Next.js frontend. Avoid event buses, microservices, Kubernetes complexity, autonomous agents, and symbolic rule engines for the MVP.

```text
Frontend
  -> FastAPI API
  -> Service layer
  -> Workflow agents
  -> PostgreSQL, S3, Qdrant, OpenAI
```

## Backend Layers

```text
api/
  HTTP contracts, request validation, response shaping

services/
  Business operations, database transactions, audit lifecycle

agents/
  Lightweight workflow steps for document processing, retrieval, compliance,
  evidence tracing, and reporting

rag/
  Ingestion, chunking, embeddings, hybrid retrieval, reranking, scoring

db/
  SQLAlchemy models and repositories

storage/
  S3 paths, uploads, retention, lifecycle handling

workers/
  Simple background workflow runners for audits and cleanup
```

## Agent Workflow

```text
Document Agent
  -> Retrieval Agent
  -> Compliance Agent
  -> Evidence Agent
  -> Report Agent
```

## Main Design Priorities

1. Retrieval accuracy
2. Grounded compliance findings
3. High-quality citations
4. Clear evidence tracing
5. Confidence and risk scoring
6. Simple maintainable modules
7. Secure temporary document handling

## MVP Boundaries

Include:

- Email/password registration and login
- JWT authentication
- Protected dashboard
- PDF/text upload
- Temporary S3 storage for user uploads
- Permanent S3 storage for compliance rules
- PostgreSQL metadata
- Qdrant rule and upload chunk collections
- Hybrid retrieval with vector search, BM25, merging, reranking
- Evidence-linked findings and reports

Defer:

- Full RBAC
- Multi-region deployment
- Complex queues
- Human approval workflow
- Advanced legal ontology
- Voice/chat features
- Autonomous planner agents

