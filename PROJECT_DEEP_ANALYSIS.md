# AI Audit & Compliance Assistant — Complete Project Deep Analysis

> **Generated:** June 16, 2026 | **Stack:** Next.js 15 (Frontend) + FastAPI Python 3.11 (Backend) + Supabase PostgreSQL + Qdrant Cloud + AWS S3

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [Backend API — Complete Route Reference](#3-backend-api--complete-route-reference)
4. [Frontend Pages — Complete Catalog](#4-frontend-pages--complete-catalog)
5. [Frontend KPIs & Backend Data Mapping](#5-frontend-kpis--backend-data-mapping)
6. [Backend Functional Modules](#6-backend-functional-modules)
7. [Data Models](#7-data-models)
8. [AI/ML Pipeline](#8-aiml-pipeline)
9. [Enterprise Features](#9-enterprise-features)

---

## 1. Architecture Overview

```
[Frontend: Next.js 15 - Port 3000]
 App Router | TanStack Query v5 | TypeScript | TailwindCSS | Framer Motion | Axios
      |
      | HTTP /api/v1/* (Axios + JWT Bearer)
      |
[Backend: FastAPI Python 3.11 - Port 8000]
 Uvicorn ASGI | SQLAlchemy 2.x ORM | Pydantic v2 | JWT HS256 | bcrypt | APScheduler | httpx
      |
      +-- Supabase PostgreSQL (Remote) - Primary relational database
      +-- Qdrant Cloud - Vector DB (2 collections)
      +-- AWS S3 - File Storage (PDF/DOCX/TXT uploads + reports)
      +-- LLM APIs - Gemini 2.5 Flash (primary) / OpenRouter (secondary)
```

### Qdrant Collections

| Collection | Purpose |
|---|---|
| `compliance_rules` | Indexed rule chunks for RAG retrieval |
| `audit_document_chunks` | Chunked policy document embeddings |

### LLM Stack

| Role | Model | Provider |
|---|---|---|
| Primary LLM | `google/gemini-2.5-flash` | OpenRouter |
| Secondary LLM | `poolside/laguna-m.1:free` | OpenRouter |
| Tertiary LLM | `gemini-2.5-flash-lite` | Gemini API |
| Embedding | `BAAI/bge-small-en-v1.5` | sentence-transformers (local, 384-dim) |
| Reranker | `BAAI/bge-reranker-base` | sentence-transformers (optional) |

---

## 2. Authentication & Authorization

### JWT Token Flow

```
POST /api/v1/auth/register  ->  Returns { access_token, refresh_token }
POST /api/v1/auth/login     ->  Returns { access_token, refresh_token }
GET  /api/v1/auth/me        ->  Returns current user profile
```

### Roles

| Role | Permissions |
|---|---|
| `ADMIN` | Full access: all user data, all audits, admin panel, rule management, webhooks, deployment |
| `USER` | Own documents, own audits, own evidence collectors |

### Role Assignment Rules

- **First registered user** → automatically assigned `ADMIN`
- Users in `DEFAULT_ADMIN_EMAIL_LIST` (.env) → assigned `ADMIN`
- All other users → assigned `USER`
- Invalid role requests default to `USER`

### API Key Auth (Inbound Webhook)

- `POST /webhooks/trigger-audit` uses `X-API-Key` header instead of JWT Bearer
- API key looked up in `api_keys` table, user identity resolved from `user_id` FK

---

## 3. Backend API — Complete Route Reference

> **Base URL:** `http://localhost:8000/api/v1`
> **Auth:** All routes require `Authorization: Bearer <token>` unless noted.

---

### 3.1 Health Checks

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Overall system health (DB + Qdrant + S3 + LLM + Embedding) |
| `GET` | `/health/database` | None | PostgreSQL connectivity check |
| `GET` | `/health/vector` | None | Qdrant roundtrip ping |
| `GET` | `/health/storage` | None | AWS S3 / MinIO roundtrip |
| `GET` | `/health/llm` | None | LLM API availability |
| `GET` | `/health/embeddings` | None | BGE embedding model status |
| `GET` | `/health/auth` | None | JWT signing key status |
| `GET` | `/health/config` | None | Full startup diagnostic dump |

**Sample `GET /health` Response:**
```json
{
  "status": "ok",
  "components": {
    "database": { "status": "ok", "latency_ms": 45 },
    "vector_store": { "status": "ok" },
    "storage": { "status": "ok" },
    "llm": { "status": "ok" },
    "embeddings": { "status": "ok" }
  }
}
```

---

### 3.2 Authentication (`/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | None | Register new user (201 Created) |
| `POST` | `/auth/login` | None | Login → JWT access + refresh tokens |
| `GET` | `/auth/me` | Bearer | Get current user profile |

**`POST /auth/register` Request:**
```json
{ "email": "user@example.com", "password": "secret", "full_name": "John Doe", "role": "USER" }
```

**`POST /auth/login` Response:**
```json
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer" }
```

**`GET /auth/me` Response:**
```json
{ "id": "uuid", "email": "user@example.com", "name": "John Doe", "role": "ADMIN", "is_active": true, "created_at": "..." }
```

---

### 3.3 Documents (`/documents`, `/batches`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/documents/upload` | Bearer | Upload a single PDF/DOCX/TXT policy document |
| `POST` | `/documents/bulk-upload` | Bearer | Bulk upload up to 2,000 documents (async batch) |
| `GET` | `/documents` | Bearer | List all user's uploaded documents |
| `GET` | `/documents/domains` | Bearer | List available compliance domains |
| `GET` | `/batches/{batch_id}` | Bearer | Poll bulk upload batch status |

**`POST /documents/upload` (multipart/form-data):**
- Fields: `title` (str), `domain` (str), `file` (File, optional), `raw_text` (str, optional)
- Pipeline: file upload → S3 store → text extraction → chunking → BGE embedding → Qdrant index
- Returns: `DocumentResponse` with (id, title, domain, status, chunk_count, created_at)

**`GET /documents` Response:**
```json
[{
  "id": "uuid",
  "title": "GDPR Policy",
  "domain": "GDPR",
  "status": "indexed",
  "chunk_count": 42,
  "s3_key": "docs/uuid/filename.pdf",
  "created_at": "2026-06-16T07:00:00Z"
}]
```

**`GET /documents/domains` Response:**
```json
[{ "id": "uuid", "name": "GDPR", "description": "General Data Protection Regulation", "created_at": "..." }]
```

---

### 3.4 Audits (`/audits`, `/audit`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/audits` | Bearer | Create + start a new audit run (async background) |
| `GET` | `/audits` | Bearer | List all user's audits |
| `GET` | `/audits/{audit_id}` | Bearer | Get single audit status + metadata |
| `GET` | `/audits/{audit_id}/findings` | Bearer | Get all findings for an audit |
| `GET` | `/audits/{audit_id}/evidence` | Bearer | Get all evidence links for an audit |
| `GET` | `/audits/{audit_id}/report` | Bearer | Get the compiled audit report |
| `GET` | `/audits/{audit_id}/diagnostics` | Bearer | Get score diagnostics (summary) |
| `POST` | `/audit/run` | Bearer | Compat alias for `POST /audits` |
| `GET` | `/audit/report/{id}` | Bearer | Compat alias for audit report by id |

**`POST /audits` Request:**
```json
{ "document_id": "uuid", "rule_set_id": "default" }
```

**`GET /audits/{id}` Response (`AuditResponse`):**
```json
{
  "id": "uuid",
  "document_id": "uuid",
  "user_id": "uuid",
  "status": "completed",
  "overall_risk": "HIGH",
  "confidence_score": 0.82,
  "error_message": null,
  "created_at": "2026-06-16T07:00:00Z",
  "updated_at": "2026-06-16T07:02:00Z"
}
```

**Audit Status Values:**

| Status | Meaning |
|---|---|
| `queued` | Created, waiting for background worker |
| `processing` | Active in audit pipeline (12 stages) |
| `completed` | Finished, report available |
| `pending_review` | Has HIGH-risk findings requiring HITL review |
| `failed` | Pipeline error — see `error_message` |

**`GET /audits/{id}/findings` Response:**
```json
[{
  "id": "uuid",
  "audit_id": "uuid",
  "rule_id": "uuid",
  "severity": "HIGH",
  "risk_level": "HIGH",
  "category": "Data Protection",
  "explanation": "Policy lacks explicit data retention clause...",
  "recommendation": "Add a data retention policy section...",
  "confidence_score": 0.88,
  "needs_review": true,
  "review_status": "pending",
  "reviewed_by": null,
  "reviewed_at": null,
  "review_comment": null,
  "original_finding_snapshot": null,
  "is_active": true
}]
```

**`GET /audits/{id}/evidence` Response:**
```json
[{
  "id": "uuid",
  "audit_id": "uuid",
  "finding_id": "uuid",
  "citation_text": "The policy states that data is stored for the lifetime of the product...",
  "citation_label": "Section 3.2 — Data Storage",
  "page_number": 12,
  "section_title": "Data Retention",
  "confidence_score": 0.91,
  "source_type": "document_chunk"
}]
```

**`GET /audits/{id}/report` Response (`ReportResponse`):**
```json
{
  "id": "uuid",
  "audit_id": "uuid",
  "summary": "AI-generated narrative summary of compliance status...",
  "status": "published",
  "report_payload": {
    "compliance_score": 0.73,
    "risk_counts": { "CRITICAL": 0, "HIGH": 2, "MEDIUM": 3, "LOW": 1 },
    "finding_count": 6,
    "key_risks": ["Missing data retention clause", "No breach notification SLA"],
    "recommendations": ["Add Section 3.4 on data retention..."],
    "findings": [{ "rule_violated": "...", "severity": "HIGH", "..." : "..." }],
    "score_diagnostics": {
      "score_reasoning": "Score is 0.73 because...",
      "rules_evaluated": 8,
      "rules_matched": 5,
      "rules_failed": 3,
      "match_confidence": 0.84
    }
  },
  "report_json_s3_uri": "s3://bucket/reports/uuid.json",
  "created_at": "2026-06-16T07:02:00Z"
}
```

---

### 3.5 Reports (`/reports`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/reports/{audit_id}` | Bearer | Get report (alias for audits/{id}/report) |
| `GET` | `/reports/{audit_id}/download/json` | Bearer | Download full report as JSON file |
| `GET` | `/reports/{audit_id}/download/pdf` | Bearer | Download report as PDF (pure PDF 1.4 text) |

---

### 3.6 HITL Review — Feature 1

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/findings/{finding_id}/review` | Bearer | Accept / Reject / Modify a HIGH-risk finding |
| `POST` | `/reports/{audit_id}/publish` | Bearer | Publish report after all reviews complete |
| `GET` | `/findings/{audit_id}/review-history` | Bearer | Fetch immutable review audit trail |

**`POST /findings/{id}/review` Request:**
```json
{
  "action": "accept",
  "comment": "Reviewed and accepted per policy v2.1",
  "modified_fields": {
    "risk_level": "MEDIUM",
    "severity": "MEDIUM",
    "explanation": "Updated explanation after investigation"
  }
}
```

**Response:**
```json
{
  "finding_id": "uuid",
  "review_status": "reviewed",
  "reviewed_by": "user_uuid",
  "reviewed_at": "2026-06-16T07:00:00Z",
  "previous_state": { "severity": "HIGH", "explanation": "Original explanation..." }
}
```

**`POST /reports/{audit_id}/publish` Response:**
```json
{
  "report_id": "uuid",
  "status": "published",
  "published_at": "2026-06-16T07:00:00Z",
  "download_urls": {
    "json": "/reports/{audit_id}/download/json",
    "pdf": "/reports/{audit_id}/download/pdf"
  }
}
```

---

### 3.7 Full Diagnostics — Feature 2

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/audits/{audit_id}/diagnostics/full` | Bearer | Full LLM audit trail with prompts, responses, retry log |

**Response (`FullDiagnosticsResponse`):**
```json
{
  "audit_id": "uuid",
  "score_reasoning": "Score is 0.73 because 2 HIGH findings were detected...",
  "rules_evaluated": 8,
  "rules_matched": 5,
  "rules_failed": 3,
  "match_confidence": 0.84,
  "llm_attempts": [
    {
      "attempt_number": 1,
      "prompt_text": "You are a compliance auditor. Evaluate the following policy...",
      "llm_response": "{ \"compliance_score\": 0.73, \"findings\": [...] }",
      "success": true,
      "error_message": null,
      "tokens_used": 1850
    }
  ],
  "context_chunks": ["chunk1 text excerpt...", "chunk2 text excerpt..."],
  "raw_llm_output": { "compliance_score": 0.73 }
}
```

---

### 3.8 Evidence Collectors — Feature 3

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/evidence-collectors` | Bearer | List all user's collectors |
| `POST` | `/evidence-collectors` | Bearer | Create a new collector (HTTP/SQL/Script) |
| `DELETE` | `/evidence-collectors/{id}` | Bearer | Delete a collector |
| `POST` | `/evidence-collectors/{id}/run` | Bearer | Manually trigger a collector execution |
| `GET` | `/evidence-collectors/{id}/results` | Bearer | Get all evidence collected by a collector |

**`POST /evidence-collectors` Request:**
```json
{
  "name": "AWS Secrets Scanner",
  "collector_type": "http",
  "config": {
    "url": "https://api.github.com/repos/org/repo/secret-scanning/alerts",
    "method": "GET",
    "headers": { "Authorization": "Bearer ghp_xxx" },
    "response_mapping": { "evidence_text": "$.number", "citation_label": "$.html_url" }
  },
  "schedule": "0 */12 * * *",
  "target_domain": "Security"
}
```

**Collector Types:**

| Type | Config Fields | Description |
|---|---|---|
| `http` | url, method, headers, response_mapping | Call a REST API endpoint |
| `sql` | db_url, query, response_mapping | Run SQL SELECT on any database |
| `script` | script_path, response_mapping | Execute a local Python/Shell script |

**`GET /evidence-collectors/{id}/results` Response:**
```json
[{
  "id": "uuid",
  "collector_id": "uuid",
  "audit_id": null,
  "finding_id": null,
  "evidence_text": "ALERT: Open secret found in repo/file.py line 42",
  "citation_label": "https://github.com/org/repo/security/alerts/1",
  "confidence_score": 0.85,
  "source_type": "external_collector",
  "collected_at": "2026-06-16T07:00:00Z"
}]
```

---

### 3.9 Webhooks & API Keys — Feature 6

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/webhooks` | Admin | List configured webhooks |
| `POST` | `/admin/webhooks` | Admin | Create a new outbound webhook |
| `DELETE` | `/admin/webhooks/{id}` | Admin | Delete a webhook |
| `POST` | `/admin/webhooks/{id}/test` | Admin | Send a test ping to webhook URL |
| `GET` | `/admin/webhooks/{id}/deliveries` | Admin | Get delivery log for a webhook |
| `GET` | `/admin/api-keys` | Admin | List API keys |
| `POST` | `/admin/api-keys` | Admin | Create an API key (returned once in plaintext) |
| `DELETE` | `/admin/api-keys/{id}` | Admin | Revoke an API key |
| `POST` | `/webhooks/trigger-audit` | X-API-Key | Trigger audit from external system |

**`POST /admin/webhooks` Request:**
```json
{
  "name": "Slack Compliance Bot",
  "url": "https://hooks.slack.com/services/...",
  "events": ["audit.completed", "finding.critical"],
  "secret": "optional_signing_secret"
}
```

**Webhook Events Supported:**

| Event | Trigger |
|---|---|
| `audit.completed` | Audit pipeline finishes successfully |
| `audit.failed` | Audit pipeline encounters an error |
| `audit.pending_review` | Audit has HIGH findings requiring HITL review |
| `finding.critical` | A CRITICAL severity finding is detected |
| `rule.changed` | A compliance rule is created/updated/archived |

**`POST /admin/api-keys` Response:**
```json
{
  "id": "uuid",
  "name": "Jenkins CI Auditor",
  "is_active": true,
  "created_at": "2026-06-16T07:00:00Z",
  "raw_key": "ak_live_xxxxxxxxxxxxxxxxxxxx"
}
```
> `raw_key` is shown ONCE on creation. Store it securely — it cannot be retrieved again.

---

### 3.10 Digital Twin (`/digital-twin`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/digital-twin` | Bearer | Get or build the org compliance digital twin |
| `POST` | `/digital-twin/rebuild` | Bearer | Force rebuild the digital twin from current data |
| `GET` | `/digital-twin/history` | Bearer | Get historical snapshots of the twin |

**`GET /digital-twin` Response:**
```json
{
  "id": "uuid",
  "maturity_score": 0.65,
  "coverage_percent": 72.0,
  "total_policies": 14,
  "covered_policies": 10,
  "missing_domains": ["HIPAA", "PCI-DSS"],
  "risk_heatmap": { "GDPR": "MEDIUM", "SOC2": "HIGH", "ISO27001": "LOW" },
  "policy_inventory": [
    { "domain": "GDPR", "document_count": 3, "avg_score": 0.78, "last_audit": "..." }
  ],
  "recommendations": ["Add HIPAA policy documents", "Remediate SOC2 HIGH findings"],
  "snapshot_at": "2026-06-16T07:00:00Z"
}
```

---

### 3.11 Admin Panel (`/admin`) — Admin-only

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/users` | Admin | List all system users |
| `GET` | `/admin/documents` | Admin | List all uploaded docs + rule docs |
| `POST` | `/admin/rules/upload` | Admin | Upload a rule document (PDF/DOCX → Qdrant) |
| `POST` | `/admin/rules/bulk-upload` | Admin | Bulk upload rule files (async batch) |
| `GET` | `/admin/rule-batches/{batch_id}` | Admin | Poll rule upload batch status |
| `POST` | `/admin/documents/upload` | Admin | Admin upload any document |
| `DELETE` | `/admin/document/{doc_id}` | Admin | Delete document + S3 object + Qdrant chunks |
| `GET` | `/admin/audit-reports` | Admin | List all audit reports across all users |
| `DELETE` | `/admin/audits/{audit_id}` | Admin | Delete an audit and all its related data |
| `GET` | `/admin/compliance-rules` | Admin | List all compliance rules |
| `POST` | `/admin/compliance-rules` | Admin | Create a new compliance rule |
| `PATCH` | `/admin/compliance-rules/{rule_id}` | Admin | Update/version a compliance rule |
| `POST` | `/admin/compliance-rules/{rule_id}/test` | Admin | Test rule against sample text |
| `POST` | `/admin/compliance-rules/{rule_id}/archive` | Admin | Archive a rule (soft delete) |
| `DELETE` | `/admin/compliance-rules/{rule_id}` | Admin | Hard delete a rule |
| `GET` | `/admin/rule-categories` | Admin | List rule categories |
| `POST` | `/admin/rule-categories` | Admin | Create a rule category |
| `GET` | `/admin/analytics` | Admin | Platform-wide analytics |
| `GET` | `/admin/logs` | Admin | Audit log entries (all system events) |
| `GET` | `/admin/storage` | Admin | S3/MinIO storage stats |
| `GET` | `/admin/qdrant` | Admin | Qdrant collection stats and health |
| `GET` | `/admin/deployment/config` | Admin | Current deployment mode config |
| `POST` | `/admin/deployment/reload` | Admin | Hot-reload deployment configuration |

**`POST /admin/compliance-rules` Request:**
```json
{
  "category": "Data Protection",
  "title": "Data Retention Policy Requirement",
  "description": "All personal data must have a defined retention period",
  "rule_text": "The organization must define and implement data retention and disposal procedures...",
  "reference": "GDPR Article 5(1)(e)",
  "version": "v1",
  "custom_attributes": { "framework": "GDPR", "severity_default": "HIGH" },
  "effectivity_date": "2026-01-01",
  "expiry_date": "2027-12-31"
}
```

**`POST /admin/compliance-rules/{id}/test` Request:**
```json
{ "sample_document_text": "Our company stores personal data indefinitely without review..." }
```

**Response:**
```json
{
  "rule_id": "uuid",
  "matched": true,
  "confidence": 0.91,
  "explanation": "The sample text indicates indefinite storage which violates the retention rule.",
  "matched_chunks": ["... stores personal data indefinitely ..."]
}
```

**`GET /admin/analytics` Response:**
```json
{
  "total_users": 5,
  "total_documents": 23,
  "total_audits": 18,
  "completed_audits": 14,
  "failed_audits": 2,
  "pending_review_audits": 1,
  "total_findings": 67,
  "high_risk_findings": 12,
  "total_rules": 45,
  "active_rules": 40
}
```

---

## 4. Frontend Pages — Complete Catalog

> **42 total pages** across 3 route groups: Public, Dashboard (USER), Admin (ADMIN)

---

### 4.1 Public / Auth Pages

#### `/` — Landing Page
- Simple redirect to `/login` or `/dashboard`
- No backend calls

#### `/login` — Login Page
- **Backend calls:** `POST /auth/login`
- **Actions:** Email + password form; stores JWT in localStorage
- **On success:** Redirects to `/dashboard`
- **Error handling:** 401 → "Invalid email or password", 403 → "Account inactive"

#### `/register` — Registration Page
- **Backend calls:** `POST /auth/register`
- **Fields:** Full name, email, password, role (USER/ADMIN)
- **Note:** First registered user → auto ADMIN

---

### 4.2 User Dashboard Pages (`/dashboard/*`)

All dashboard pages use `DashboardShell` layout with sidebar navigation.

#### `/dashboard` — Executive Dashboard (Home)

**Backend calls:**
- `GET /audits` — All audit records
- `GET /documents` — Document library
- `GET /documents/domains` — Domain count
- `GET /audits/{latest_completed_id}/report` — Score, risk counts

**KPIs Displayed:**

| KPI Card | Source | Field Path |
|---|---|---|
| Compliance Score | `report.report_payload` | `compliance_score` → normalized to % |
| Active Audits | `audits` | `filter(isActive).length` |
| Documents | `documents` | `.length` |
| Critical Findings | `report_payload.risk_counts` | `.HIGH` or `.CRITICAL` |
| Compliance Domains | `domains` | `.length` |
| Completed Audits | `audits` | `filter(status=completed).length` |
| Open Risk Assessments | `audits` | `filter(overall_risk ∈ {HIGH,MEDIUM}).length` |
| Latest Result Date | `latestCompletedAudit` | `.created_at` |

**Backend Signals Panel:**
- Compliance domains count (from `GET /documents/domains`)
- Completed audits / total audits ratio
- Open risk assessment count
- Latest result timestamp

**Recent Activity Feed** (per audit):
- Document title & domain (joined from `GET /documents`)
- Audit status badge (`completed`/`failed`)
- Overall risk badge (`HIGH`/`MEDIUM`/`LOW`)
- Analysis confidence (`audit.confidence_score`)
- Link to report detail page

---

#### `/dashboard/upload` — Single Document Upload
- **Backend calls:** `GET /documents/domains`, `POST /documents/upload`
- **Fields:** Document title, compliance domain dropdown, file (PDF/DOCX/TXT) or raw text paste
- **On success:** Redirects to audit status page

#### `/dashboard/bulk-upload` — Bulk Document Upload
- **Backend calls:** `POST /documents/bulk-upload`, `GET /batches/{batch_id}` (polling)
- **Features:** Multi-file drag-drop, per-file domain assignment, batch progress tracking
- **KPIs:** Batch status, files processed vs total, failed file count

#### `/dashboard/audits` — Audit Runs Tracker
- **Backend calls:** `GET /audits`, `GET /documents`
- **KPIs:** Total audits, active/queued, completed, failed counts
- **Per-audit:** status, risk level, confidence score, document title, domain, date
- **Features:** Real-time polling (1.5s interval for active audits), link to report

#### `/dashboard/reports` — Reports Library
- **Backend calls:** `GET /audits`, `GET /documents`
- **KPIs:** Total completed audits, high-risk count; per-report: compliance status, risk level, doc name, date
- **Features:** Search/filter by status and risk level; link to report detail

---

#### `/dashboard/reports/[id]` — Report Detail Page ⭐ (Most Complex)

**Backend calls:**

| Query | Endpoint | Interval |
|---|---|---|
| `getAudit(id)` | `GET /audits/{id}` | 1.5s while active |
| `getReport(id)` | `GET /audits/{id}/report` | Once (when ready) |
| `getFindings(id)` | `GET /audits/{id}/findings` | Once (when ready) |
| `getEvidence(id)` | `GET /audits/{id}/evidence` | Once (when ready) |
| `listDocuments` | `GET /documents` | Once |

**KPIs Displayed:**

| Section | KPI | Backend Source |
|---|---|---|
| Top Metrics (5 cards) | Overall Compliance Score | `report_payload.compliance_score` (tries 8 key names) |
| Top Metrics | Risk Level | `report_payload.risk_level` / `audit.overall_risk` |
| Top Metrics | Findings Count | `report_payload.finding_count` / `findings.length` |
| Top Metrics | Confidence | `audit.confidence_score` / avg of finding confidences |
| Top Metrics | Audit Status | `audit.status` |
| Executive Summary | Compliance Status | Derived: "Compliant" / "Non-Compliant" / "Partial" |
| Executive Summary | Critical / High / Medium counts | `report_payload.risk_counts` |
| Executive Summary | Key Risks | `report_payload.key_risks[]` |
| Executive Summary | AI Summary | `report.summary` |
| Score Panel | Score Progress Bar | `compliance_score * 100` |
| Score Panel | Score Reasoning | `report_payload.score_diagnostics.score_reasoning` |
| Score Panel | Rules Evaluated | `score_diagnostics.rules_evaluated` |
| Score Panel | Rules Matched | `score_diagnostics.rules_matched` |
| Score Panel | Rules Failed | `score_diagnostics.rules_failed` |
| Score Panel | Match Confidence | `score_diagnostics.match_confidence` |
| Risk Breakdown | CRITICAL / HIGH / MEDIUM / LOW bars | `risk_counts` with % calculation |
| Finding Cards | Rule Violated | `finding.explanation` / `report_payload.findings[].rule_violated` |
| Finding Cards | Severity Badge | `finding.severity` |
| Finding Cards | Risk Level | `finding.risk_level` |
| Finding Cards | Confidence Badge | `finding.confidence_score` |
| Finding Cards | Source Page | `evidence[].page_number` |
| Finding Cards | Evidence Text | `finding.explanation` / `evidence[].citation_text` |
| Finding Cards | Matched Policy Section | `evidence[].section_title` |
| Finding Cards | Impact | `report_payload.findings[].impact` |
| Finding Cards | Recommendation | `report_payload.findings[].recommendation` |
| Finding Cards | Review Status | `finding.review_status` (pending/reviewed/rejected) |
| Evidence Cards | Document Section | `evidence.section_title` |
| Evidence Cards | Extracted Text | `evidence.citation_text` (keyword highlighted) |
| Evidence Cards | Source Type | `evidence.source_type` |
| Evidence Cards | Confidence | `evidence.confidence_score` |
| Recommended Actions | Action Items | `report_payload.recommendations[]` |
| Assessment Context | Audit ID, Document, Domain, Status, Date | Audit + Document join |

**Special Features:**
- **HITL Tab:** When `audit.status === "pending_review"` → shows "Review Findings" tab with pending count badge
- **Diagnostics Drawer:** `GET /audits/{id}/diagnostics/full` → LLM prompts, responses, retry log, JSON tree view
- **Review History Drawer:** `GET /findings/{audit_id}/review-history` → timeline of all reviewer actions
- **Publish Button:** `POST /reports/{audit_id}/publish` → appears when all pending reviews completed
- **Export Center:** JSON download (`GET /reports/{id}/download/json`) and PDF (`GET /reports/{id}/download/pdf`)
- **Expandable Evidence Viewer:** Per-finding expandable panel: document section, extracted text with keyword highlight, matched rule, violation reason, source citations with page numbers

---

#### `/dashboard/evidence-collectors` — Agentic Evidence Collectors

**Backend calls:**

| Action | Endpoint |
|---|---|
| Load collectors list | `GET /evidence-collectors` |
| Create new collector | `POST /evidence-collectors` |
| Delete collector | `DELETE /evidence-collectors/{id}` |
| Run collector | `POST /evidence-collectors/{id}/run` |
| View evidence logs | `GET /evidence-collectors/{id}/results` |

**KPIs per Collector Card:**
- Collector type badge (HTTP / SQL / Script)
- Cron schedule (or "Manual only")
- Target compliance domain
- Last run status badge: `success` (green) / `failed` (red) / `Never Run` (gray)

**Evidence Log Fields Displayed:**
- Citation label, evidence text (truncated), confidence score (%), collection date, source type

---

#### `/dashboard/evidence` — Evidence Library
- **Backend calls:** `GET /audits`, then `GET /audits/{id}/evidence` per completed audit
- **KPIs:** Total evidence count; per-evidence: citation text, section title, page number, confidence, source type

#### `/dashboard/digital-twin` — Compliance Digital Twin
- **Backend calls:** `GET /digital-twin`, `POST /digital-twin/rebuild`

**KPIs Displayed:**

| KPI | Source |
|---|---|
| Maturity Score | `digital_twin.maturity_score` (0.0–1.0) |
| Policy Coverage % | `digital_twin.coverage_percent` |
| Total Policies | `digital_twin.total_policies` |
| Covered Policies | `digital_twin.covered_policies` |
| Missing Domains | `digital_twin.missing_domains[]` |
| Risk Heatmap | `digital_twin.risk_heatmap` (domain → HIGH/MEDIUM/LOW) |
| Policy Inventory | `digital_twin.policy_inventory[]` (domain, count, avg score, last audit) |
| Recommendations | `digital_twin.recommendations[]` |

#### `/dashboard/violations` — Violations Tracker
- **Backend calls:** `GET /audits`, `GET /audits/{id}/findings` (all completed audits)
- **KPIs:** Total HIGH/CRITICAL findings, findings grouped by rule category

#### `/dashboard/risk` — Risk Assessment
- **Backend calls:** `GET /audits`, `GET /documents`
- **KPIs:** Risk distribution (HIGH/MEDIUM/LOW counts), average confidence by domain

#### `/dashboard/rules` — Compliance Rules View
- **Backend calls:** `GET /admin/compliance-rules`
- **KPIs:** Total rules, active/archived rules, rules by category/domain

#### `/dashboard/chat` — AI Compliance Chat
- **Features:** Natural language Q&A about compliance findings via RAG/LLM

#### `/dashboard/history` — Audit History
- **Backend calls:** `GET /audits`, `GET /documents`
- **KPIs:** Timeline of all audit runs with status, risk, date

#### `/dashboard/team` — Team Members
- **Backend calls:** `GET /admin/users`
- **KPIs:** Total users, roles, registration dates, active/inactive status

#### `/dashboard/settings` — User Settings
- **Backend calls:** `GET /auth/me`
- **Features:** Profile display, account info

---

### 4.3 Admin Pages (`/admin/*`)

All admin pages use `AdminShell` layout with admin-specific sidebar navigation.

#### `/admin` — Admin Dashboard

**Backend calls:** `GET /admin/analytics`, `GET /admin/users`, `GET /admin/documents`, `GET /admin/audit-reports`

**KPIs Displayed:**

| KPI | Source |
|---|---|
| Total Users | `analytics.total_users` |
| Total Documents | `analytics.total_documents` |
| Total Audits | `analytics.total_audits` |
| Completed Audits | `analytics.completed_audits` |
| Failed Audits | `analytics.failed_audits` |
| Pending Review | `analytics.pending_review_audits` |
| Total Findings | `analytics.total_findings` |
| High-Risk Findings | `analytics.high_risk_findings` |
| Total Rules | `analytics.total_rules` |
| Active Rules | `analytics.active_rules` |

#### `/admin/users` — User Management
- **Backend calls:** `GET /admin/users`
- **KPIs:** User list with ID, name, email, role, active status, registration date

#### `/admin/reports` — All Reports (Admin)
- **Backend calls:** `GET /admin/audit-reports`, `GET /admin/documents`
- **KPIs:** All reports across all users with compliance scores, risk levels

#### `/admin/reports/[id]` — Report Detail (Admin view)
- Same component as `/dashboard/reports/[id]` — detects `isAdminPath`
- Uses `GET /admin/documents` instead of `GET /documents` for document lookup

#### `/admin/rules` — Rules Management
- **Backend calls:** `GET /admin/compliance-rules`, `GET /admin/rule-categories`
- **Actions:** Archive, delete rules; view version history modal
- **KPIs:** Total rules, active/archived count, by category/domain

#### `/admin/rules/builder` — Rule Builder ⭐
- **Backend calls:** `POST /admin/compliance-rules`, `POST /admin/compliance-rules/{id}/test`
- **Form fields:** Category, title, description, rule text, reference, version, custom attributes (JSON), effectivity/expiry dates
- **Test Panel:** Paste sample document text → see confidence score, match explanation, matched chunks

**KPIs After Test:**
- Match result (Matched / No Match)
- Confidence % (e.g., "91%")
- LLM explanation of why it matched
- Highlighted matched text snippets

#### `/admin/rules/bulk-upload` — Bulk Rule Upload
- **Backend calls:** `POST /admin/rules/bulk-upload`, `GET /admin/rule-batches/{batch_id}`
- **Features:** Upload PDF/DOCX rule documents in bulk; async batch processing + polling
- **KPIs:** Batch status, rules indexed count, failed count

#### `/admin/rules/versions` — Rule Version History
- **Backend calls:** `GET /admin/compliance-rules` (filtered by `parent_rule_id`)
- **KPIs:** Version number, created date, diff of `rule_text` between versions

#### `/admin/rules/domains` — Rule Domains
- **Backend calls:** `GET /admin/rule-categories`, `POST /admin/rule-categories`

#### `/admin/compliance-rules` — Compliance Rules Full View
- **Backend calls:** `GET /admin/compliance-rules`
- Full rule management with CRUD operations

#### `/admin/analytics` — Platform Analytics
- **Backend calls:** `GET /admin/analytics`, `GET /admin/logs`
- **KPIs:** Full platform metrics + paginated audit log stream

#### `/admin/webhooks` — Webhooks & API Keys ⭐

**Backend calls:**

| Action | Endpoint |
|---|---|
| Load webhooks | `GET /admin/webhooks` |
| Create webhook | `POST /admin/webhooks` |
| Delete webhook | `DELETE /admin/webhooks/{id}` |
| Test webhook | `POST /admin/webhooks/{id}/test` |
| View delivery log | `GET /admin/webhooks/{id}/deliveries` |
| Load API keys | `GET /admin/api-keys` |
| Create API key | `POST /admin/api-keys` |
| Revoke API key | `DELETE /admin/api-keys/{id}` |

**KPIs per Webhook:**
- Name, URL (monospace), subscribed events list
- Last triggered timestamp, active status

**Delivery Log Fields:**
- Event name, timestamp, HTTP status code (green/red), success flag, retry count

**API Key Fields:**
- Name, created date, last used date, active status
- `raw_key` shown in copy-to-clipboard panel once on creation

#### `/admin/deployment` — Deployment Settings ⭐
- **Backend calls:** `GET /admin/deployment/config`, `POST /admin/deployment/reload`

**KPIs Displayed:**

| KPI | Source |
|---|---|
| Deployment Mode | `config.deployment_mode` (cloud/hybrid/onprem) |
| LLM Provider | `config.llm_provider` |
| LLM Model | `config.llm_model` |
| Embedding Model | `config.embedding_model` |
| Vector Store URL | `config.qdrant_url` |
| Storage Backend | `config.s3_endpoint` |
| Database | `config.database_url` (masked) |
| Ollama Endpoint | `config.ollama_url` (if onprem) |

**Features:** Switch mode between cloud/hybrid/onprem, hot-reload specific components

#### `/admin/settings` — Admin Settings
- **Backend calls:** `GET /auth/me`, `GET /admin/analytics`

#### `/admin/digital-twin` — Digital Twin (Admin)
- **Backend calls:** `GET /digital-twin`, `POST /digital-twin/rebuild`, `GET /digital-twin/history`
- **KPIs:** Same as `/dashboard/digital-twin` + historical snapshots comparison table

---

### 4.4 Standalone Pages

#### `/audits/[auditId]` — Audit Status Page
- **Backend calls:** `GET /audits/{auditId}` (polling 1.5s while active)
- **KPIs:** Real-time processing stage (12 named stages), current step text, progress %, estimated completion

---

## 5. Frontend KPIs & Backend Data Mapping

### 5.1 Primary Dashboard KPIs

| KPI Name | Page | Backend Endpoint | Field | Transform |
|---|---|---|---|---|
| Compliance Score | Dashboard, Report | `GET /audits/{id}/report` | `report_payload.compliance_score` | `*100` → "73%" |
| Active Audits | Dashboard | `GET /audits` | `filter(isAuditActive(status))` | Count |
| Documents Uploaded | Dashboard | `GET /documents` | `.length` | Count |
| Critical Findings | Dashboard | `GET /audits/{id}/report` | `risk_counts.HIGH` or `CRITICAL` | Count |
| Compliance Domains | Dashboard | `GET /documents/domains` | `.length` | Count |
| Completed Audits | Dashboard | `GET /audits` | `filter(status=completed).length` | Count |
| Open Risk Assessments | Dashboard | `GET /audits` | `filter(overall_risk ∈ {HIGH,MEDIUM}).length` | Count |

### 5.2 Report Detail KPIs

| KPI | Endpoint | Field | Notes |
|---|---|---|---|
| Overall Score | `/report` | `compliance_score` / `audit_score` / `score` | Tries 8 key names |
| Risk Level | `/report` + audit | `risk_level` / `audit.overall_risk` | Graceful fallback |
| Findings Count | `/report` + `/findings` | `finding_count` / `findings.length` | |
| Confidence | audit + `/findings` | `confidence_score` / avg findings | |
| Audit Status | audit | `status` | Includes HITL states |
| Score Reasoning | `/report` | `score_diagnostics.score_reasoning` | Narrative text |
| Rules Evaluated | `/report` | `score_diagnostics.rules_evaluated` | Integer |
| Rules Matched | `/report` | `score_diagnostics.rules_matched` | Integer |
| Rules Failed | `/report` | `score_diagnostics.rules_failed` | Integer |
| Match Confidence | `/report` | `score_diagnostics.match_confidence` | Percent |
| Risk Counts | `/report` | `risk_counts.{CRITICAL,HIGH,MEDIUM,LOW}` | Integer per severity |
| AI Summary | `/report` | `report.summary` | Full narrative |
| Key Risks | `/report` | `report_payload.key_risks[]` | String array |
| Recommendations | `/report` | `report_payload.recommendations[]` | String array |

### 5.3 Finding Card KPIs

| KPI | Source | Field |
|---|---|---|
| Rule Violated | finding + report_payload | `explanation` / `rule_violated` |
| Severity | finding | `severity` |
| Risk Level | finding | `risk_level` |
| Confidence | finding | `confidence_score` |
| Source Page | evidence[] | `page_number` |
| Evidence Text | finding + evidence[] | `explanation` / `citation_text` |
| Matched Policy Section | evidence[] | `section_title` |
| Impact | report_payload.findings[] | `impact` |
| Recommendation | report_payload.findings[] | `recommendation` |
| Review Status | finding | `review_status` (pending/reviewed/rejected) |
| Reviewed By | finding | `reviewed_by` + `reviewed_at` |

### 5.4 Digital Twin KPIs

| KPI | Source |
|---|---|
| Maturity Score | `digital_twin.maturity_score` (0.0–1.0) |
| Coverage % | `digital_twin.coverage_percent` |
| Policies Covered | `digital_twin.covered_policies` / `total_policies` |
| Missing Domains | `digital_twin.missing_domains[]` |
| Risk Heatmap | `digital_twin.risk_heatmap` (domain → HIGH/MEDIUM/LOW) |
| Policy Inventory | `digital_twin.policy_inventory[]` |
| Recommendations | `digital_twin.recommendations[]` |

### 5.5 Admin Analytics KPIs

| KPI | Source |
|---|---|
| Total Users | `analytics.total_users` |
| Total Documents | `analytics.total_documents` |
| Total / Completed / Failed / Pending Audits | `analytics.*_audits` |
| Total / High-Risk Findings | `analytics.*_findings` |
| Total / Active Rules | `analytics.*_rules` |

---

## 6. Backend Functional Modules

### 6.1 Audit Workflow Engine (`audit_workflow.py`)

**12 named pipeline stages:**
```
 1. document_load      → Load document record from PostgreSQL
 2. text_extraction    → Extract text from S3 (pypdf for PDF, python-docx for DOCX)
 3. chunking           → CharacterTextSplitter (chunk_size=500, overlap=50)
 4. embedding          → BAAI/bge-small-en-v1.5 → 384-dim vectors
 5. qdrant_upload      → Batch upsert to audit_document_chunks collection
 6. rule_retrieval     → Hybrid RAG: Qdrant vector + BM25 + Reciprocal Rank Fusion
 7. reranking          → Optional BGE cross-encoder reranker
 8. llm_analysis       → Gemini 2.5 Flash with structured JSON prompt
 9. findings_parse     → Parse and validate LLM JSON response
10. evidence_link      → Map evidence chunks to findings in DB
11. report_generate    → Create ReportRecord + ComplianceScoreDiagnostic in DB
12. webhook_dispatch   → Fire audit.completed or audit.failed webhook events
```

**Retry Logic:**
- Attempt 1: 5 rule candidates, 700 max output tokens
- Attempt 2: 3 rule candidates, 650 max output tokens
- Attempt 3: 2 rule candidates, 600 max output tokens
- LLM fallback: Gemini 2.5 Flash → Poolside Laguna M.1 → Gemini 2.0 Flash

**HITL Gate:** If any finding has `severity=HIGH` or `risk_level=HIGH`:
- Audit `status` → `pending_review`
- Finding `needs_review=True`, `review_status="pending"`
- Report blocked from publication until all reviewed

### 6.2 RAG Pipeline

```
Document Text
  → CharacterTextSplitter (chunk_size=500, overlap=50)
  → BAAI/bge-small-en-v1.5 (384-dim embeddings)
  → Qdrant upsert (audit_document_chunks)

At query time (per compliance rule):
  → Embed rule text → dense vector
  → Qdrant hybrid search:
      Dense: cosine similarity, top-K=5
      Sparse: BM25 keyword, top-K=5
      Fusion: Reciprocal Rank Fusion
  → Optional BGE reranker (cross-encoder score)
  → Top N chunks → LLM prompt context
```

### 6.3 LLM Analysis Engine

**Prompt Structure:**
```
System: You are a compliance auditor. Analyze the policy document against the compliance rules.

Context Rules:
[rule_text × N rules]

Policy Document Sections:
[retrieved_chunks × M chunks]

Task: Return JSON with:
  compliance_score (0.0–1.0)
  findings[] {rule_violated, severity, risk_level, explanation, recommendation, confidence}
  risk_counts {CRITICAL, HIGH, MEDIUM, LOW}
  key_risks[]
  recommendations[]
  score_reasoning
```

**Score Computation:**
- Heuristic: `(matched_rules - failed_rules) / total_rules`
- LLM: `compliance_score` from LLM JSON
- Blend: `0.4 * heuristic + 0.6 * llm_score`

### 6.4 Compliance Rule Engine

- Rules stored in **PostgreSQL** (`compliance_rules` table) + **Qdrant** (`compliance_rules` collection)
- **Versioning:** `PATCH /admin/compliance-rules/{id}` archives current, creates new row with `parent_rule_id`, increments `version_number`
- **Test endpoint:** Runs mini-RAG pipeline against sample text → returns confidence + explanation
- **Bulk upload:** PDF/DOCX → extract text → chunk → embed → index in Qdrant
- **Status lifecycle:** `active` → `archived` (soft) → hard delete

### 6.5 Finding Review Service

**Accept:** Sets `review_status="reviewed"`, `reviewed_by`, `reviewed_at`

**Reject:** Sets `is_active=False`, `review_status="rejected"`, stores mandatory comment

**Modify:** Saves `original_finding_snapshot` (JSONB pre-modification state), updates severity/risk_level/explanation, sets `review_status="reviewed"`

**Publish Gate:**
```
All findings where needs_review=True have review_status != "pending"
  → audit.status = "completed"
  → report.status = "published"
  → dispatch "audit.completed" webhook
```

### 6.6 Webhook Dispatcher

- Stored webhooks with comma-separated `events` field
- On trigger: HTTP POST to `webhook.url` with JSON payload
- Optional `X-Signature: sha256=<HMAC>` header for payload verification
- Every delivery recorded in `webhook_deliveries` with response status, success flag, retry count

### 6.7 Evidence Collector Service

| Type | Mechanism |
|---|---|
| `http` | `httpx` async GET/POST → JSONPath response mapping |
| `sql` | SQLAlchemy engine → SELECT query → column alias mapping |
| `script` | `subprocess.run()` → parse stdout as JSON |

Results saved to `external_evidence` table (`source_type="external_collector"`).

### 6.8 Digital Twin Service

```python
maturity_score = mean(audit.compliance_score for all completed audits)
coverage_percent = (domains_with_audits / total_domains) * 100
missing_domains = all_domains - audited_domains
risk_heatmap = { domain: max(finding.risk_level for findings in domain) }
policy_inventory = [{domain, doc_count, avg_score, last_audit_date}]
```

Historical snapshots saved to `compliance_twin_snapshots` per rebuild.

---

## 7. Data Models

### Core PostgreSQL Tables

| Table | Key Columns |
|---|---|
| `users` | id, email, name, password_hash, role, is_active |
| `uploaded_documents` | id, user_id, title, domain, s3_key, status, chunk_count |
| `document_chunks` | id, document_id, chunk_text, chunk_index, s3_key |
| `audit_runs` | id, document_id, user_id, status, overall_risk, confidence_score, error_message |
| `audit_results` | id, audit_id, result_type, result_payload (JSONB) |
| `findings` | id, audit_id, rule_id, severity, risk_level, explanation, recommendation, confidence_score, needs_review, review_status, reviewed_by, reviewed_at, review_comment, original_finding_snapshot (JSONB), is_active |
| `evidence_links` | id, audit_id, finding_id, citation_text, citation_label, page_number, section_title, confidence_score, source_type |
| `audit_reports` | id, audit_id, summary, status, report_payload (JSONB), report_json_s3_uri |
| `compliance_score_diagnostics` | id, audit_id, rules_evaluated, rules_matched, rules_failed, match_confidence, score_reasoning, llm_attempts (JSONB), context_chunks (JSONB) |
| `compliance_rules` | id, category, title, rule_text, description, reference, version, status, parent_rule_id, version_number, custom_attributes (JSONB), effectivity_date, expiry_date |
| `rule_documents` | id, rule_set_id, filename, category, jurisdiction, status |
| `compliance_domains` | id, name, description |
| `webhooks` | id, user_id, name, url, events, is_active, secret_hash, last_triggered_at |
| `webhook_deliveries` | id, webhook_id, event, payload (JSONB), response_status, success, retry_count |
| `api_keys` | id, user_id, name, key_hash, is_active, last_used_at, expires_at |
| `external_evidence` | id, collector_id, audit_id, finding_id, evidence_text, citation_label, confidence_score, raw_payload (JSONB), source_type |
| `evidence_collectors` | id, user_id, name, collector_type, config (JSONB), schedule, target_domain, is_active, last_run_at, last_run_status |
| `compliance_twin_snapshots` | id, user_id, maturity_score, coverage_percent, risk_heatmap (JSONB), missing_domains (JSONB), policy_inventory (JSONB), snapshot_at |
| `audit_logs` | id, user_id, action, entity_type, entity_id, metadata (JSONB), created_at |
| `batch_documents` | id, batch_id, document_id, status, error_message |

---

## 8. AI/ML Pipeline

### Embedding Pipeline

```
Input: document text (arbitrary length)
  → CharacterTextSplitter (chunk_size=500, chunk_overlap=50)
  → BAAI/bge-small-en-v1.5 via sentence-transformers → 384-dim vectors
  → Qdrant upsert with metadata: { document_id, chunk_index, domain, title, user_id }
```

### Retrieval Pipeline (at audit time)

```
For each compliance rule:
  → Embed rule text → 384-dim query vector
  → Qdrant hybrid search (collection: audit_document_chunks):
      Dense: cosine similarity, top-K=5 candidates
      Sparse: BM25 keyword index, top-K=5 candidates
      Fusion: Reciprocal Rank Fusion merges results
  → Optional: BGE reranker cross-encoder rescores merged list
  → Top N chunks → injected as context into LLM prompt
```

### Score Normalization (Frontend)

```javascript
function normalizeScore(value) {
    if (value === null || value === undefined) return null;
    if (value >= 0 && value <= 1) return value;       // Already 0–1
    if (value > 1 && value <= 100) return value / 100; // Convert from %
    return null;  // Invalid range
}
// Display: formatPercent(normalizeScore(score)) → "73%"
// Tries key names: compliance_score, complianceScore, audit_score, auditScore,
//                  overall_score, overallScore, final_score, finalScore, score
```

---

## 9. Enterprise Features

### Feature 1: Human-in-the-Loop (HITL) Review

- **Trigger:** Any finding with `severity=HIGH` or `risk_level=HIGH`
- **Gate:** Audit stays in `pending_review` until ALL HIGH findings are reviewed
- **Actions:** Accept (no change), Reject (soft-delete `is_active=False`), Modify (snapshot + update)
- **Audit trail:** `original_finding_snapshot` (JSONB) stores full pre-modification state
- **UI:** "Review Findings" tab on report detail, `FindingsReviewPanel` component with action buttons
- **Publish gate:** `POST /reports/{audit_id}/publish` → fires `audit.completed` webhook

### Feature 2: Score Diagnostics Trail

- Every audit creates a `ComplianceScoreDiagnostic` record
- Stores: all LLM prompts, raw LLM responses, retry attempts with token counts
- UI: `DiagnosticsDrawer` slides in from right with JSON tree, copy buttons per section
- Endpoint: `GET /audits/{id}/diagnostics/full`

### Feature 3: Agentic Evidence Collection

- Three collector types: HTTP REST API, SQL database query, local Python/Shell script
- Configurable cron schedule for automatic periodic execution
- JSONPath mapping for flexible response field extraction
- Evidence stored in `external_evidence` table linked to collectors, audits, findings
- UI: Collectors Registry + Collected Trace Logs side panel

### Feature 4: Configurable Rule Engine

- Create rules via UI form (Rule Builder) or bulk upload PDF/DOCX
- Version control: every update archives old version, creates new with `parent_rule_id`
- Test endpoint validates rule against sample text with confidence score before publishing
- Custom attributes (JSONB), effectivity/expiry dates, reference links
- Bulk import from PDF/DOCX → auto-extract rule chunks → embed → Qdrant index

### Feature 5: On-Prem / Hybrid Deployment

| Mode | LLM | Vector DB | Storage | Database |
|---|---|---|---|---|
| `cloud` | Gemini API / OpenRouter | Qdrant Cloud | AWS S3 | Supabase PostgreSQL |
| `hybrid` | Gemini API / OpenRouter | Qdrant local | AWS S3 | Supabase PostgreSQL |
| `onprem` | Ollama (local LLM) | Qdrant local | MinIO | SQLite / local PG |

- Hot-reload: `POST /admin/deployment/reload` swaps service factory instances without process restart
- Admin UI: Deployment Settings page shows current config, allows mode switching

### Feature 6: Webhooks & API Keys

- **Outbound webhooks:** Admin registers target URL + event list; backend POSTs on event trigger
- **HMAC signing:** Optional `secret` → `X-Signature: sha256=<HMAC>` header for payload verification
- **Delivery log:** Every attempt logged with HTTP status code, success flag, retry count in `webhook_deliveries`
- **API keys:** bcrypt-hashed in DB; plaintext returned once on creation (shown in UI for copy)
- **Inbound trigger:** `POST /webhooks/trigger-audit` with `X-API-Key` header → starts audit from CI/CD or external systems

---

*End of Analysis | Generated by Antigravity AI Agent | June 16, 2026*
