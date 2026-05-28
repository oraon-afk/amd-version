# Workers

Background workflow runners:

- Audit workflow
- Rule indexing workflow
- Temporary upload cleanup workflow

Use a simple runner for the MVP. Keep the interface replaceable by Celery or RQ later.

