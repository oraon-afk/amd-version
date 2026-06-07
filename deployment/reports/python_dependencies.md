# Python Dependencies

## Generated File

Created `requirements-production.txt` with pinned production dependencies.

## Method

Inputs:

- `requirements.txt`
- `backend/pyproject.toml`
- Backend Python import scan
- Optional lazy imports in document parsing and embedding code
- Local package versions available from the current Python environment

## Production Dependency Groups

- FastAPI server: `fastapi`, `uvicorn[standard]`, `gunicorn`, `pydantic`, `pydantic-settings`, `python-multipart`, `email-validator`.
- Database: `sqlalchemy`, `psycopg[binary]`, `alembic`.
- Auth: `bcrypt`, `passlib`, `python-jose[cryptography]`.
- Storage: `boto3`.
- Vector DB and embeddings: `qdrant-client`, `sentence-transformers`.
- AI providers and workflow: `openai`, `json-repair`, `langgraph`, `langchain-text-splitters`.
- Retrieval and document parsing: `rank-bm25`, `pymupdf`, `pdfplumber`, `pypdf`, `python-docx`.

## Validation

Command run:

```bash
.venv/Scripts/python.exe -m pip install -r requirements-production.txt
```

Result: passed.

Packages installed during validation because they were missing locally:

- `gunicorn==23.0.0`
- `pdfplumber==0.11.4`
- `python-docx==1.1.2`
- Transitive packages: `pdfminer.six`, `pypdfium2`, `lxml`

Import smoke test:

```bash
python -c "import fastapi, uvicorn, gunicorn, sqlalchemy, psycopg, alembic, boto3, qdrant_client, openai, json_repair, langgraph, rank_bm25, fitz, pdfplumber, pypdf, docx, sentence_transformers; import backend.app.main"
```

Result: passed.

## Notes

- The backend lazily imports `sentence_transformers`, `pdfplumber`, and `docx`; they are still included because production upload and RAG paths can use them.
- `uvicorn[standard]` includes websocket transport packages even though no application WebSocket route was detected.
- Docker build could not be run locally because Docker is not installed on this workstation.
