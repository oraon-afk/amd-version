# Frontend Architecture

## Runtime Shape

The frontend is a Next.js application with feature-based modules. Pages compose feature components, but business UI state stays inside feature folders.

```text
src/app
  Route-level composition.

src/features
  Feature APIs, hooks, components, and local types.

src/components
  Shared layout and UI primitives.

src/lib
  API client, auth helpers, constants, formatting.

src/types
  Cross-feature TypeScript contracts.
```

## Main Routes

```text
/login
/register
/dashboard
/audits
/audits/[auditId]
/rules
/settings
```

## Dashboard Layout

The dashboard should be operational and scannable:

```text
Top navigation
Left navigation
Main workspace
  Upload panel
  Processing status
  Risk summary
  Violations table
  Evidence viewer
  Report panel
  Audit history
```

Avoid marketing sections, decorative hero pages, and oversized cards. This is an enterprise workflow surface.

## Frontend Data Flow

```text
Page
  -> feature hook
  -> API client
  -> FastAPI endpoint
```

Recommended state tools:

```text
TanStack Query for server state
React Hook Form for forms
Zod for validation
HttpOnly cookie or secure token handling for auth
```

## Expected Components

```text
Auth:
  LoginForm
  RegisterForm
  ProtectedRoute

Uploads:
  UploadDropzone
  ProcessingTimeline

Audits:
  AuditHistoryTable
  AuditStatusBadge
  RiskSummary

Findings:
  ViolationsTable
  FindingDetailPanel

Evidence:
  EvidenceViewer
  CitationCard
  SourceSnippet

Reports:
  AuditReportPanel
  ReportExportButton

Rules:
  RuleSetSelector
  RuleUploadPanel
```

