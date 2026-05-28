# Directory Structure

```text
ai-audit-compliance-assistant/
  README.md
  .env.example
  docker-compose.dev.yml

  docs/
    architecture.md
    directory-structure.md
    api-structure.md
    rag-pipeline.md
    data-and-storage.md
    module-responsibilities.md
    development-roadmap.md
    naming-conventions.md

  backend/
    pyproject.toml
    README.md
    alembic/
    tests/
    app/
      main.py
      core/
      api/v1/
      auth/
      db/
        models/
        repositories/
      schemas/
      agents/
      rag/
        ingestion/
        retrieval/
        indexing/
        prompts/
        scoring/
      services/
      storage/
      workers/
      utils/

  frontend/
    package.json
    README.md
    src/
      app/
      features/
      components/
      lib/
      types/
```

## Structure Rule

Each folder should own one clear responsibility. If a file needs to import from too many unrelated folders, move orchestration up into `services/` or `workers/` instead of hiding business logic inside API routes or UI components.

