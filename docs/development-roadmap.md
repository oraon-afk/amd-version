# Development Roadmap

## Day 1

1. Set up FastAPI project and Next.js project.
2. Add PostgreSQL models and migrations.
3. Implement registration, login, JWT auth, and protected dashboard access.
4. Implement S3 upload service for temporary user documents.
5. Implement PDF/text parsing and semantic chunking.
6. Implement OpenAI embeddings and Qdrant indexing.
7. Implement compliance rule ingestion.
8. Implement vector retrieval, BM25 retrieval, hybrid merge, and reranking.

## Day 2

1. Implement audit workflow runner.
2. Implement Document, Retrieval, Compliance, Evidence, and Report agents.
3. Persist findings, evidence links, risk scores, and generated reports.
4. Build dashboard upload workflow.
5. Build violations table, evidence viewer, audit history, and report panel.
6. Add temporary upload cleanup.
7. Add focused backend tests for auth, upload, retrieval, and audit generation.
8. Run end-to-end validation with sample documents and rule documents.

## Post-MVP

- Role-based access control
- Admin rule versioning UI
- Better OCR for scanned PDFs
- Celery or RQ worker queue
- Human reviewer workflow
- PDF report export
- Evaluation suite for retrieval and citation quality

