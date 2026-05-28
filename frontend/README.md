# Frontend

Next.js frontend for the enterprise compliance audit dashboard.

## Main Areas

```text
src/app
  Next.js routes and page composition.

src/features/auth
  Login, register, session handling.

src/features/uploads
  PDF/text upload and processing timeline.

src/features/audits
  Audit history, status, risk summary.

src/features/findings
  Violations and missing clause views.

src/features/evidence
  Evidence viewer, citations, source snippets.

src/features/reports
  Audit report panel and export controls.

src/features/rules
  Rule set selector and rule upload workflows.
```

## UI Principle

This is an enterprise workflow application. Prefer dense, scannable screens with clear status, tables, panels, and evidence mapping over marketing-style pages.

