# Architecture Documentation Index

This folder contains the complete architecture package for the AI Audit & Compliance Assistant with Evidence Tracing.

## Requested Output Mapping

```text
1. Enterprise-grade directory structure
   docs/directory-structure.md

2. Backend architecture
   docs/backend-architecture.md

3. Frontend architecture
   docs/frontend-architecture.md

4. API structure
   docs/api-structure.md

5. Agent module structure
   docs/agents.md

6. RAG pipeline structure
   docs/rag-pipeline.md

7. Authentication structure
   docs/authentication.md

8. S3 storage structure
   docs/s3-storage.md

9. PostgreSQL schema suggestions
   docs/postgresql-schema.md

10. Qdrant organization
    docs/qdrant-organization.md

11. Workflow orchestration structure
    docs/workflow-orchestration.md

12. Dashboard module structure
    docs/dashboard.md

13. Suggested environment structure
    .env.example

14. Suggested development roadmap
    docs/development-roadmap.md

15. Suggested naming conventions
    docs/naming-conventions.md

16. Module responsibilities
    docs/module-responsibilities.md
```

## Design Position

This is intentionally a lean enterprise MVP architecture. It keeps the useful RAG ideas from the V9 reference, such as hybrid retrieval, reranking, metadata filtering, context validation, and source tracing, while avoiding the old project's tangled structure and oversized modules.

