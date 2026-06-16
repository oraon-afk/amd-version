# AI Audit Compliance Assistant – Enhancement Proposal

## Extending the Platform to Address Market Gaps

This document defines a set of **production‑ready functionalities** that build upon the existing AI Audit Compliance Assistant. Each feature directly targets a limitation of current commercial GRC platforms (Vanta, Drata, Sprinto, etc.) and provides a clear implementation roadmap – from frontend UI components to backend API contracts, database changes, and AI agent upgrades.

---

## Table of Contents

1. [Feature 1: Human‑in‑the‑Loop (HITL) for Critical Findings](#feature-1-human-in-the-loop-hitl-for-critical-findings)
2. [Feature 2: Complete Score Diagnostics & Audit Trail](#feature-2-complete-score-diagnostics--audit-trail)
3. [Feature 3: Agentic Evidence Collection](#feature-3-agentic-evidence-collection)
4. [Feature 4: Configurable Rule Engine](#feature-4-configurable-rule-engine)
5. [Feature 5: On‑Premise / Hybrid Deployment Support](#feature-5-on-premise--hybrid-deployment-support)
6. [Feature 6: Open Integration Model & Webhooks](#feature-6-open-integration-model--webhooks)
7. [Appendix: Cross‑Feature Database Schema Changes](#appendix-cross-feature-database-schema-changes)

---

## Feature 1: Human‑in‑the‑Loop (HITL) for Critical Findings

### 🎯 Purpose
Prevent false positives and increase trust by requiring a human compliance expert to review, confirm, or override any **HIGH** risk finding before the final audit report is published. This addresses the lack of human oversight in fully automated systems.

### 🖥️ Frontend Components to Add

| Component | Location | Description |
|-----------|----------|-------------|
| `ReviewWorkflowBadge` | Report detail page (`/dashboard/reports/[id]`) | Shows status: `pending_review` / `under_review` / `reviewed` |
| `FindingsReviewPanel` | New tab in report detail | Lists only findings with `needs_review=true`. Each finding has Accept / Reject / Modify buttons. |
| `ReviewCommentBox` | Inside each critical finding | Textarea for reviewer notes (mandatory for reject/modify). |
| `PublishReportButton` | Report header | Enabled only when all critical findings have been reviewed. |
| `ReviewHistoryDrawer` | Side panel | Shows who reviewed what, when, and before/after changes. |

### ⚡ Trigger Flow (Frontend → Backend)

1. **User opens a completed audit** → frontend fetches `GET /audits/{id}/report`. New field `review_status` indicates if HITL is required and completed.
2. **User clicks "Accept" on a finding** → `POST /findings/{finding_id}/review` with payload `{action: "accept", comment: "..."}`.
3. **User clicks "Modify"** → opens modal to change `risk_level`, `severity`, `explanation`, then submits same endpoint with `action: "modify", modified_fields: {...}`.
4. **User clicks "Publish Report"** → `POST /reports/{audit_id}/publish` – finalizes the report, moves status to `completed` (previously maybe `review_pending`), and triggers PDF/JSON finalisation.

### 📡 API Specifications

#### `POST /findings/{finding_id}/review`
**Auth:** Bearer (ADMIN or document owner)  
**Request body:**
```json
{
  "action": "accept" | "reject" | "modify",
  "comment": "Required for reject/modify, optional for accept",
  "modified_fields": {
    "risk_level": "MEDIUM",      // only if action=modify
    "severity": "MEDIUM",
    "explanation": "New explanation text"
  }
}
```
**Response:**
```json
{
  "finding_id": "uuid",
  "review_status": "reviewed",
  "reviewed_by": "user_id",
  "reviewed_at": "2026-06-15T10:00:00Z",
  "previous_state": { ... }   // snapshot before modification
}
```

#### `POST /reports/{audit_id}/publish`
**Request body:** (empty)  
**Response:**
```json
{
  "report_id": "uuid",
  "status": "published",
  "published_at": "...",
  "download_urls": {
    "json": "/reports/{audit_id}/download/json",
    "pdf": "/reports/{audit_id}/download/pdf"
  }
}
```

### 🧩 Backend Implementation Steps

1. **Database Changes** (see Appendix – add columns to `findings` table: `needs_review BOOLEAN`, `review_status`, `reviewed_by`, `reviewed_at`, `review_comment`, `original_finding_snapshot JSONB`).
2. **Extend AuditWorkflow** – after `ComplianceAgent` generates findings, if `risk_level == "HIGH"` or `severity == "HIGH"`, set `needs_review=true` and change `AuditRun.status` to `pending_review` (new state), not `completed`.
3. **Create `FindingReviewService`** – handles accept/reject/modify:
   - On accept: mark as reviewed, no changes.
   - On reject: delete finding or mark `is_active=false` (soft delete).
   - On modify: update fields, store snapshot in `original_finding_snapshot`.
4. **Modify ReportAgent** – when generating report before publish, exclude rejected findings; include modified explanations.
5. **Add background notification** – when all critical findings are reviewed, automatically mark audit as ready for publishing (optional email to user).

---

## Feature 2: Complete Score Diagnostics & Audit Trail

### 🎯 Purpose
Provide a **regulator‑ready, immutable audit trail** that records every input, prompt, LLM response, and intermediate calculation used to produce a compliance score. This eliminates the “black box” criticism of existing tools.

### 🖥️ Frontend Components

| Component | Location | Description |
|-----------|----------|-------------|
| `DiagnosticsDrawer` | Report detail page – new button "Show Diagnostics" | Side panel displaying score reasoning, rules evaluated, matched, failed, confidence breakdown. |
| `PromptViewer` | Within drawer – collapsible | Shows the exact system and user prompt sent to the LLM. |
| `LLMResponseViewer` | Within drawer – collapsible | Raw JSON returned from LLM before parsing. |
| `RetryLog` | Within drawer | List of retry attempts (if any) with reason and context size changes. |
| `ExportDiagnosticsButton` | Drawer footer | Download diagnostic data as JSON for external audit. |

### ⚡ Trigger Flow

- User clicks "Show Diagnostics" → frontend calls `GET /audits/{id}/diagnostics/full` (new endpoint) which returns the complete diagnostic object (already partially exists, now extended).
- No write triggers – purely read‑only.

### 📡 API Specifications

#### `GET /audits/{audit_id}/diagnostics/full`
**Auth:** Bearer (admin or owner)  
**Response:** (extends existing `ComplianceScoreDiagnosticResponse`)
```json
{
  "id": "uuid",
  "audit_id": "uuid",
  "created_at": "...",
  "rules_evaluated": 15,
  "rules_matched": 7,
  "rules_failed": 3,
  "match_confidence": 0.82,
  "score_reasoning": "The policy addresses access control but lacks encryption requirements...",
  "diagnostics_payload": {
    "retry_attempts": [
      {
        "attempt": 1,
        "rule_candidates": 5,
        "chunk_limit": 5,
        "max_tokens": 700,
        "prompt": "...full system prompt...",
        "llm_response_raw": "...",
        "error": null
      }
    ],
    "final_prompt": "...",
    "final_llm_response": "...",
    "heuristic_confidence": 0.75,
    "blended_confidence": 0.82,
    "context_chunks": [
      {"chunk_id": "chunk_1", "text_preview": "First 200 chars..."}
    ]
  }
}
```

### 🧩 Backend Implementation Steps

1. **Extend `ComplianceScoreDiagnostic` table** – add columns: `retry_attempts JSONB`, `final_prompt TEXT`, `final_llm_response TEXT`, `context_chunks_snapshot JSONB`.
2. **Modify `ComplianceAgent`** – after each LLM call, store the prompt, response, error (if any) into a temporary structure. After final success or failure, persist the entire diagnostic record.
3. **Create `DiagnosticsService.get_full_diagnostics()`** – joins audit, report, and diagnostic tables, returns enriched object.
4. **Add background archiving** – after 90 days, move diagnostic blobs to S3 to keep database size manageable.
5. **Security** – ensure that sensitive data (API keys) are never logged. Redact any accidental secrets from stored prompts.

---

## Feature 3: Agentic Evidence Collection

### 🎯 Purpose
Go beyond static document uploads. Allow the system to **actively fetch evidence** by calling external APIs, querying databases, or running scripts. This automates the remaining 60% of evidence that traditional tools miss (shadow IT, internal dashboards, etc.).

### 🖥️ Frontend Components

| Component | Location | Description |
|-----------|----------|-------------|
| `EvidenceCollectorList` | New page `/dashboard/evidence-collectors` | List user‑defined collectors (name, type, last run status). |
| `CreateCollectorWizard` | Modal | Step‑by‑step: choose type (HTTP / SQL / script), define parameters, test connection. |
| `TestRunButton` | Inside wizard | Executes collector once and shows sample output. |
| `CollectorSchedule` | Settings panel | Cron‑like schedule for automatic evidence refresh. |
| `EvidenceSourceBadge` | Report findings | Shows if evidence came from uploaded document or live collector. |

### ⚡ Trigger Flow

1. **User defines collector** → POST `/evidence-collectors` with type and configuration.
2. **User runs collector manually** → POST `/evidence-collectors/{id}/run`.
3. **Scheduler triggers** (background) → runs collector on schedule, stores results as `ExternalEvidence` objects linked to a document or rule.
4. **During audit** – `EvidenceAgent` can now query `ExternalEvidence` table (by document_id or domain) and use it alongside chunk‑based evidence.

### 📡 API Specifications

#### `POST /evidence-collectors`
**Request body:**
```json
{
  "name": "GitHub Secrets Scanner",
  "type": "http",   // or "sql", "script"
  "config": {
    "url": "https://api.github.com/repos/owner/repo/secret-scanning",
    "method": "GET",
    "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"},
    "response_mapping": {
      "evidence_text": "$.alerts[0].message",
      "citation_label": "$.alerts[0].secret_type"
    }
  },
  "schedule": "0 */6 * * *",   // every 6 hours
  "target_domain": "GDPR",
  "document_id": null           // optional, if collector belongs to a specific document
}
```
**Response:** `CollectorResponse` with id, status, last_run.

#### `GET /evidence-collectors/{id}/run`
**Response:**
```json
{
  "run_id": "uuid",
  "status": "success",
  "collected_evidence": [
    {
      "evidence_text": "Hardcoded API key found in file config.py",
      "citation_label": "GitHub Secret Scanning Alert",
      "confidence_score": 0.95
    }
  ]
}
```

### 🧩 Backend Implementation Steps

1. **Add tables:** `EvidenceCollector`, `ExternalEvidence` (links to audit/finding).
2. **Create `CollectorEngine`** – uses Celery or FastAPI `BackgroundTasks` to execute:
   - HTTP: `httpx` with variable substitution from environment.
   - SQL: async connection to configured database (store credentials encrypted).
   - Script: run sandboxed Python/Shell script (Docker container recommended).
3. **Scheduler** – use `APScheduler` or Celery Beat to trigger collectors.
4. **Integrate with `EvidenceAgent`** – during retrieval, also query `ExternalEvidence` by `target_domain` or `document_id` and include as context (weighted lower than direct chunks).
5. **Audit logs** – every collector run is logged with request/response (truncated) for debugging.

---

## Feature 4: Configurable Rule Engine

### 🎯 Purpose
Allow administrators to define **custom compliance rules** without uploading a document. Rules can be expressed as natural language, a simple condition template, or a custom DSL. This provides flexibility that rigid platforms lack.

### 🖥️ Frontend Components

| Component | Location | Description |
|-----------|----------|-------------|
| `RuleBuilder` | `/admin/rules/builder` | Visual form to create/edit rules: category, title, rule text, reference, version, custom attributes. |
| `RuleTestPanel` | Inside RuleBuilder | Allows testing a rule against a sample document text – shows retrieval results and sample evaluation. |
| `RuleVersionHistory` | Rule detail page | Lists previous versions (audit requirement). |
| `BulkRuleImport` | CSV/JSON upload | For migrating many rules at once. |

### ⚡ Trigger Flow

1. **Admin creates rule via UI** → `POST /admin/compliance-rules` (already exists, but extended).
2. **Rule is immediately indexed** into Qdrant (embedding generated) and stored in DB.
3. **Admin updates rule** → `PATCH /admin/compliance-rules/{id}` – version incremented automatically; old version archived but not deleted.
4. **During audit**, retrieval uses active rules only (status="active").

### 📡 API Specifications (Extended)

#### `POST /admin/compliance-rules` (Enhanced)
**Request body (additions):**
```json
{
  ... existing fields ...,
  "custom_attributes": {
    "jurisdiction": "EU",
    "framework": "GDPR",
    "risk_weight": 1.5
  },
  "effectivity_date": "2025-01-01",
  "expiry_date": null
}
```
**Response:** includes `version` (auto‑incremented from 1).

#### `POST /admin/compliance-rules/{id}/test`
**Request:**
```json
{
  "sample_document_text": "Our policy states that all data is encrypted at rest."
}
```
**Response:**
```json
{
  "rule_matched": true,
  "confidence": 0.88,
  "matched_chunks": ["...sample chunk..."],
  "explanation": "The document explicitly mentions encryption at rest which satisfies rule R-123."
}
```

### 🧩 Backend Implementation Steps

1. **Add versioning** to `ComplianceRule` table (`version INTEGER`, `parent_rule_id UUID` to link versions). Soft delete via `status='archived'`.
2. **Modify `RuleService.upsert_rule()`** – when updating existing rule, create new row with incremented version, keep old row as archived.
3. **Enhance Qdrant indexing** – store `rule_id` and `version` as payload metadata, so retrieval can filter by `status='active'`.
4. **Create `RuleTestService`** – uses the same retrieval and LLM evaluation pipeline as a full audit, but only for a single rule and sample text.
5. **Add UI for custom attributes** – these are stored as JSONB and can be used later for filtering / reporting.

---

## Feature 5: On‑Premise / Hybrid Deployment Support

### 🎯 Purpose
Enable the platform to run entirely on customer infrastructure (or in a hybrid mode). This addresses data residency concerns and the needs of highly regulated industries that cannot use cloud‑only SaaS.

### 🖥️ Frontend Components (for admin configuration)

| Component | Location | Description |
|-----------|----------|-------------|
| `DeploymentSettings` | `/admin/deployment` | Panel to switch between cloud/on‑prem modes, configure local endpoints for Qdrant, S3, LLM. |
| `HealthDashboard` (existing, enhanced) | `/admin` | Shows status of self‑hosted components (local Qdrant, local embedding model, etc.). |
| `EmbeddingModelManager` | Advanced settings | Download or select local embedding model (BGE‑small, etc.) – shows progress. |

### ⚡ Trigger Flow (Admin only)

- Admin changes environment variables or updates settings via UI → backend writes to config file / environment and triggers re‑initialisation of services (embedding model, Qdrant client, S3 client) without full restart if possible.

### 📡 API Specifications

#### `GET /admin/deployment/config` (new)
**Response:**
```json
{
  "mode": "onprem" | "hybrid" | "cloud",
  "components": {
    "vector_db": {"type": "qdrant_local", "url": "http://localhost:6333"},
    "storage": {"type": "s3_compatible", "endpoint": "http://minio:9000"},
    "embedding": {"type": "local_huggingface", "model": "BAAI/bge-small-en-v1.5"},
    "llm": {"type": "local_ollama", "model": "llama2:7b"}
  }
}
```

#### `POST /admin/deployment/reload`
**Request:** `{}` (triggers service reload)  
**Response:** `{ "status": "reloading", "components_reloaded": ["embedder", "qdrant"] }`

### 🧩 Backend Implementation Steps

1. **Abstract all external service clients** behind factory classes that read configuration from `settings.py` (which can be overridden by environment variables or database configs).
2. **Implement Local Embedding Service** – use `sentence-transformers` loaded once, with fallback to CPU if GPU not available.
3. **Support S3‑compatible storage** (MinIO, SeaweedFS) – `boto3` already supports custom endpoints via `endpoint_url`.
4. **Support local Qdrant** – connection string `http://localhost:6333` instead of cloud URL.
5. **Add Ollama / LocalAI integration** – create `LocalLLMProvider` that calls Ollama’s REST API.
6. **Provide Docker Compose manifests** – for a fully self‑contained deployment (Postgres, Qdrant, MinIO, backend, frontend, Ollama). Document clearly.

---

## Feature 6: Open Integration Model & Webhooks

### 🎯 Purpose
Let external systems **react to compliance events** (audit completed, high risk finding, rule changed) and also allow **external triggers to start audits**. This builds an ecosystem around your platform.

### 🖥️ Frontend Components

| Component | Location | Description |
|-----------|----------|-------------|
| `WebhookList` | `/admin/webhooks` | List configured webhooks (URL, events, secret). |
| `CreateWebhookForm` | Modal | Choose event types (audit.completed, finding.critical, etc.), enter URL, enable. |
| `TestWebhookButton` | Webhook row | Sends a test payload to verify connectivity. |
| `WebhookDeliveryLog` | Drawer | Shows recent attempts, status codes, response bodies. |

### ⚡ Trigger Flow

- **User defines webhook** → `POST /admin/webhooks` with event types and URL.
- **When event occurs** (e.g., audit finishes), backend dispatches HTTP POST to each matching webhook with a retry mechanism.
- **External system calls back** – e.g., `POST /api/v1/webhooks/trigger-audit` (inbound webhook) to start an audit on a document.

### 📡 API Specifications

#### `POST /admin/webhooks`
**Request:**
```json
{
  "name": "Slack Notifications",
  "url": "https://hooks.slack.com/services/...",
  "events": ["audit.completed", "finding.critical"],
  "secret": "optional_verification_header",
  "active": true
}
```
**Response:** Webhook object with `id`, `created_at`.

#### `POST /api/v1/webhooks/trigger-audit` (inbound public endpoint)
**Auth:** API Key (provided to external systems)  
**Request:**
```json
{
  "document_id": "uuid",
  "rule_set_id": "optional",
  "callback_url": "https://external.com/status"
}
```
**Response:** `{ "audit_id": "uuid", "status": "started" }`

### 🧩 Backend Implementation Steps

1. **Create `Webhook` table** – store id, name, url, events (array of strings), secret, active, created_at.
2. **Create `WebhookDelivery` table** – log each attempt: webhook_id, event, request_body, response_status, response_body, success, retry_count.
3. **Implement `WebhookDispatcher`** – on event (e.g., `audit_updated`), iterate active webhooks matching event type, send POST with payload `{event, timestamp, data: {...}}`. Use background task with exponential backoff (up to 5 retries).
4. **Create inbound webhook endpoint** – validate API key, then call `AuditService.create_audit` and return audit_id.
5. **Add API key management** – new table `ApiKey` for external systems to authenticate.

---

## Appendix: Cross‑Feature Database Schema Changes

All changes assume PostgreSQL (Supabase). Use Alembic migrations.

```sql
-- Feature 1: HITL
ALTER TABLE findings ADD COLUMN needs_review BOOLEAN DEFAULT FALSE;
ALTER TABLE findings ADD COLUMN review_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE findings ADD COLUMN reviewed_by UUID REFERENCES users(id);
ALTER TABLE findings ADD COLUMN reviewed_at TIMESTAMP;
ALTER TABLE findings ADD COLUMN review_comment TEXT;
ALTER TABLE findings ADD COLUMN original_finding_snapshot JSONB;

ALTER TABLE audit_runs ADD COLUMN review_deadline TIMESTAMP;
-- add new status 'pending_review' to audit_runs.status enum

-- Feature 2: Diagnostics
ALTER TABLE compliance_score_diagnostics ADD COLUMN retry_attempts JSONB;
ALTER TABLE compliance_score_diagnostics ADD COLUMN final_prompt TEXT;
ALTER TABLE compliance_score_diagnostics ADD COLUMN final_llm_response TEXT;
ALTER TABLE compliance_score_diagnostics ADD COLUMN context_chunks_snapshot JSONB;

-- Feature 3: Evidence Collectors
CREATE TABLE evidence_collectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'http', 'sql', 'script'
    config JSONB NOT NULL,
    schedule TEXT,
    target_domain TEXT,
    document_id UUID REFERENCES documents(id),
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    last_run_at TIMESTAMP,
    last_run_status VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE external_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collector_id UUID REFERENCES evidence_collectors(id),
    audit_id UUID REFERENCES audit_runs(id),
    finding_id UUID REFERENCES findings(id),
    evidence_text TEXT,
    citation_label TEXT,
    confidence_score FLOAT,
    collected_at TIMESTAMP DEFAULT NOW(),
    raw_payload JSONB
);

-- Feature 4: Configurable Rules (versioning)
ALTER TABLE compliance_rules ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE compliance_rules ADD COLUMN parent_rule_id UUID;
ALTER TABLE compliance_rules ADD COLUMN custom_attributes JSONB;
ALTER TABLE compliance_rules ADD COLUMN effectivity_date DATE;
ALTER TABLE compliance_rules ADD COLUMN expiry_date DATE;

-- Feature 6: Webhooks
CREATE TABLE webhooks (
    id UUID PRIMARY KEY,
    name TEXT,
    url TEXT NOT NULL,
    events TEXT[],
    secret TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP
);

CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY,
    webhook_id UUID REFERENCES webhooks(id),
    event TEXT,
    request_body TEXT,
    response_status INTEGER,
    response_body TEXT,
    success BOOLEAN,
    retry_count INTEGER,
    created_at TIMESTAMP
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT,
    key_hash TEXT NOT NULL,
    created_at TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

---

## Conclusion

The six features outlined above directly address the most significant limitations of existing compliance automation platforms. By implementing **Human‑in‑the‑Loop**, **transparent diagnostics**, **agentic evidence collection**, a **configurable rule engine**, **on‑prem deployment**, and **open webhooks**, your AI Audit Compliance Assistant will not only match but surpass commercial alternatives in flexibility, trustworthiness, and regulatory readiness.

Each feature is broken down into actionable frontend and backend tasks, complete with API contracts and database schemas. Prioritise Feature 1 (HITL) and Feature 2 (diagnostics) first, as they provide immediate compliance credibility. Then iterate on Features 3–6 based on user feedback and adoption patterns.
