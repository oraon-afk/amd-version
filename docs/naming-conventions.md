# Naming Conventions

## Python

- Files and modules: `snake_case`
- Classes: `PascalCase`
- Functions: `snake_case`
- Services: `AuditService`, `RuleService`, `DocumentService`
- Agents: `DocumentAgent`, `RetrievalAgent`, `ComplianceAgent`

## TypeScript

- Components: `PascalCase`
- Hooks: `useSomething`
- API files: `api.ts`
- Feature types: `types.ts`

## API

- Use plural nouns: `/documents`, `/audits`, `/rulesets`
- Use nested resources only when the child cannot stand alone: `/audits/{audit_id}/findings`

## Database

- Tables: plural `snake_case`
- Columns: `snake_case`
- Primary keys: `id`
- Foreign keys: `{entity}_id`

## S3

- Lowercase path segments
- Always scope by tenant
- Uploaded documents must include audit ID and expiry metadata

## Qdrant

- Collections: `snake_case`
- Payload keys: `snake_case`
- Chunk IDs should be deterministic where possible:

```text
{document_id}:{page_number}:{chunk_index}:{text_hash}
```

