# Functional RFP: AACA Enhancement Project – AI-Powered Business Features & System Improvements

**Date:** June 16, 2026  
**RFP ID:** AACA-ENH-2026-001  
**Issuing Organization:** [Your Organization Name]  

---

## 1. Introduction

### 1.1 Background
The **AI-Driven Audit & Compliance Assistant (AACA)** is an enterprise GRC platform that automates policy evaluation against regulatory frameworks (GDPR, HIPAA, SOC2, PCI-DSS). Built with Next.js 15 and FastAPI, it leverages RAG, LLMs (via OpenRouter/Gemini/Ollama), and hybrid storage (PostgreSQL, Qdrant, S3/MinIO).

### 1.2 Objective
This RFP seeks proposals to enhance AACA with a set of AI‑powered business features and foundational improvements that:

- **Empower business users** (auditors, compliance managers, policy owners) with intuitive, self‑service AI tools.
- **Strengthen security & separation of duties** by introducing a `REVIEWER` role.
- **Improve system performance** via a caching layer and establish measurable performance benchmarks.

The enhancements must integrate seamlessly with the existing architecture and preserve all current functionalities.

---

## 2. Scope of Work

The vendor shall deliver the following components as part of this engagement:

1. **Foundational Improvements**  
   - Add `REVIEWER` role with appropriate permissions.  
   - Implement a Redis‑based caching layer for frequent database queries.  
   - Define, document, and baseline performance benchmarks with specific targets.

2. **AI‑Powered Features**  
   - **Explain Finding** – Interactive drill‑down with human‑readable chain‑of‑thought.  
   - **Remediation Plans** – Automated step‑by‑step corrective action plans.  
   - **Natural Rule Creation** – Generate structured compliance rules from plain‑English descriptions.  
   - **Gap Analysis** – Compare current policies against regulatory frameworks and recommend missing controls.  
   - **Report Builder** – Create tailored compliance reports with AI‑generated narratives for different audiences.

All features must be exposed via REST APIs and integrated into the existing Next.js frontend, adhering to the current design system (TailwindCSS, Framer Motion).

---

## 3. Functional Requirements

### 3.1 Foundational Improvements

#### 3.1.1 Reviewer Role
| ID | Requirement | Acceptance Criteria |
|----|-------------|----------------------|
| **REQ‑ROLE‑01** | Introduce a new role `REVIEWER` in the user model and authentication system. | User table has `REVIEWER` as a valid enum; existing ADMIN and USER roles remain unchanged. |
| **REQ‑ROLE‑02** | `REVIEWER` can view findings and diagnostics for any audit. | Endpoints `GET /audits/{id}/findings` and `GET /audits/{id}/diagnostics/full` allow access for `REVIEWER`. |
| **REQ‑ROLE‑03** | `REVIEWER` can perform review actions (Accept, Reject, Modify) on findings. | Endpoint `POST /findings/{finding_id}/review` is accessible to `REVIEWER` and `ADMIN`. |
| **REQ‑ROLE‑04** | `REVIEWER` cannot publish reports, manage rules, manage users, or configure system settings. | Corresponding endpoints (e.g., `POST /reports/{id}/publish`, `POST /admin/compliance-rules`) are forbidden to `REVIEWER`. |
| **REQ‑ROLE‑05** | Frontend adapts to show/hide actions based on role; reviewers see a dedicated dashboard. | UI elements (buttons, menus) are conditionally rendered based on the logged‑in user’s role. |

#### 3.1.2 Caching Layer
| ID | Requirement | Acceptance Criteria |
|----|-------------|----------------------|
| **REQ‑CACHE‑01** | Implement a Redis cache to store frequently read data. | Redis instance is integrated (via Docker Compose for all deployment modes). |
| **REQ‑CACHE‑02** | Cache active compliance rules with a TTL of 5 minutes; invalidate on rule creation/update/archive. | After updating a rule, the next request retrieves fresh data. |
| **REQ‑CACHE‑03** | Cache document metadata lists (and individual metadata) with TTL of 1 minute; invalidate on upload/delete. | Document list updates within 1 minute after changes. |
| **REQ‑CACHE‑04** | Cache dashboard summary statistics with TTL of 30 seconds. | Dashboard data is nearly real‑time and does not hit the database on every page load. |
| **REQ‑CACHE‑05** | Provide a toggle to enable/disable caching for debugging. | Admin can disable cache via environment variable or API. |

#### 3.1.3 Performance Benchmarks
| ID | Requirement | Acceptance Criteria |
|----|-------------|----------------------|
| **REQ‑PERF‑01** | Define and document specific performance targets for key operations under baseline load (100 concurrent users, 1,000 documents, 10,000 rules). | Targets: audit initiation <500ms; status polling <100ms; dashboard load <1.5s; full audit (<50 pages) <2 min; report generation <1s. |
| **REQ‑PERF‑02** | Set up a performance testing suite (e.g., k6, Locust) that runs in CI/CD. | Tests are executed on every release candidate; reports are generated. |
| **REQ‑PERF‑03** | Demonstrate that the system meets all targets after caching and other optimizations. | Performance test results are provided as part of the final deliverable. |

---

### 3.2 AI‑Powered Business Features

#### 3.2.1 Explain Finding
| ID | Requirement | Acceptance Criteria |
|----|-------------|----------------------|
| **REQ‑EXPL‑01** | Provide an interactive explanation for each finding, showing why it was triggered. | Clicking “Explain” opens a side panel/modal with: rule text, evidence paragraphs, LLM reasoning (summarised), and confidence scores. |
| **REQ‑EXPL‑02** | Explanation must be generated from existing diagnostic data (stored during audit). | No additional LLM call is required if cached explanation exists; otherwise, generate on‑demand. |
| **REQ‑EXPL‑03** | Cache explanations per finding for 24 hours to avoid duplicate generation. | Repeated requests for the same finding return cached response within 24h. |
| **REQ‑EXPL‑04** | Expose a new endpoint `GET /findings/{finding_id}/explanation` returning structured JSON. | Response includes `explanation_text`, `evidence_list`, `confidence`, `source_rule`, and `raw_diagnostics_url` (optional). |
| **REQ‑EXPL‑05** | Frontend displays the explanation with collapsible sections for technical details. | Design is responsive and uses existing component library. |

#### 3.2.2 Remediation Plans
| ID | Requirement | Acceptance Criteria |
|----|-------------|----------------------|
| **REQ‑REMED‑01** | Generate a structured remediation plan for a finding, including steps, estimated effort, priority, and suggested owner. | Plan is returned as JSON with fields: `steps[]`, `estimated_effort_hours`, `priority` (HIGH/MEDIUM/LOW), `suggested_owner_role`. |
| **REQ‑REMED‑02** | The system uses LLM with context from the finding (rule, evidence, similar past findings) to generate the plan. | Output is grounded in the provided context; hallucination is minimised by strict prompt engineering. |
| **REQ‑REMED‑03** | Users can edit and approve the plan before saving. | After generation, the plan is displayed in editable form; save action stores it in the database. |
| **REQ‑REMED‑04** | Provide an API endpoint `POST /findings/{finding_id}/remediation-plan` to generate and store the plan (or update if exists). | Endpoint returns the full plan object. |
| **REQ‑REMED‑05** | Remediation plans are accessible from the finding detail view and included in reports (when selected). | The plan is linked to the finding; report builder can include it. |

#### 3.2.3 Natural Rule Creation
| ID | Requirement | Acceptance Criteria |
|----|-------------|----------------------|
| **REQ‑NAT‑01** | Allow administrators to describe a compliance requirement in plain English. | A text input field is provided in the Rule Builder UI. |
| **REQ‑NAT‑02** | The system uses an LLM to parse the description and propose structured rule fields: title, category, severity, rule_text, description, reference frameworks. | Output JSON conforms to the existing rule schema; the user can edit before saving. |
| **REQ‑NAT‑03** | Provide an API endpoint `POST /admin/compliance-rules/generate-from-text` that accepts `{ "description": string }` and returns the proposed rule. | The endpoint validates the LLM output; if invalid, it retries with error feedback. |
| **REQ‑NAT‑04** | The generated rule can be saved directly (calls the existing create rule endpoint) with appropriate versioning. | After editing, the user clicks “Save” to create a new rule (version 1). |
| **REQ‑NAT‑05** | The feature must support fallback to a manual entry mode if LLM is unavailable. | If the LLM call fails, the UI shows the manual form with the original description as a hint. |

#### 3.2.4 Gap Analysis
| ID | Requirement | Acceptance Criteria |
|----|-------------|----------------------|
| **REQ‑GAP‑01** | Provide a tool to compare the organization’s current rules and document domains against a selected regulatory framework (e.g., SOC2, HIPAA). | User selects a framework from a pre‑configured list. |
| **REQ‑GAP‑02** | The system must have a knowledge base of framework requirements (control IDs, descriptions, suggested rule templates). | The knowledge base is stored as vector‑indexed documents or a dedicated table. |
| **REQ‑GAP‑03** | For each requirement, determine coverage status: Covered, Partial, Missing, based on semantic similarity to existing rules and document domains. | Using vector similarity (threshold configurable); coverage decision is reproducible. |
| **REQ‑GAP‑04** | For Missing/Partial requirements, propose a draft rule using an LLM (based on the requirement description). | Proposed rule is similar to Natural Rule Creation output. |
| **REQ‑GAP‑05** | Expose an API endpoint `POST /admin/gap-analysis` with body `{ "framework": string }` that returns summary and details. | Response includes counts and list of each requirement with coverage status and proposed rule (if missing). |
| **REQ‑GAP‑06** | Provide a frontend page showing the gap analysis report; allow one‑click creation of proposed rules. | A “Create Rule” button next to each missing requirement that triggers the Natural Rule Creation flow. |

#### 3.2.5 Report Builder
| ID | Requirement | Acceptance Criteria |
|----|-------------|----------------------|
| **REQ‑REP‑01** | Allow users to generate a custom compliance report from an audit, choosing a template (Executive Summary, Technical Detail, Auditor‑Ready, Board). | At least three templates are available. |
| **REQ‑REP‑02** | The report must include AI‑generated narrative text tailored to the chosen template, rewritten from the raw findings and evidence. | The narrative is coherent, audience‑appropriate, and references the audit data. |
| **REQ‑REP‑03** | Users can select which sections to include (e.g., Overview, Findings, Remediation Plans, Evidence Appendix). | Checkbox selection in the UI. |
| **REQ‑REP‑04** | The generated report is returned as structured JSON; the frontend displays it for editing. | Editable text areas for each narrative section. |
| **REQ‑REP‑05** | Provide export functionality to PDF and DOCX formats. | Use reliable server‑side libraries (e.g., WeasyPrint, python‑docx). |
| **REQ‑REP‑06** | Expose an API endpoint `POST /reports/{audit_id}/custom` with body `{ template, sections }` that returns the report JSON. | The endpoint may be asynchronous for large reports; return job ID with polling option. |
| **REQ‑REP‑07** | Store the generated reports (including custom versions) in the database for later retrieval. | A new table `custom_reports` stores audit_id, template, sections, generated_json, and timestamps. |

---


