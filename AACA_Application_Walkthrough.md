# AI Audit & Compliance Assistant (AACA) - User & Admin Guide

Welcome to the **AI Audit & Compliance Assistant (AACA)**. This walkthrough is designed to guide business users, reviewers, and GRC administrators through the application's features, objectives, and workflows.

---

## 1. Executive Summary & Application Scope

### Why AACA Was Developed
Traditional compliance auditing is manual, expensive, and error-prone. Organizations struggle to manually review thousands of operational logs, vendor agreements, and internal policies against complex regulatory standards like **GDPR, HIPAA, SOC 2, and PCI-DSS**. 

AACA was developed to:
- **Automate Policy Validation:** Instantly cross-reference uploaded documents against compliance guidelines.
- **Trace Evidence Precisely:** Pinpoint specific page numbers and paragraphs (citations) supporting audit results.
- **Leverage AI for Remediation:** Generate clear, human-readable corrective actions when gaps are found.
- **Provide Actionable Insights:** Bridge compliance gaps with semantic framework mapping and tailored executive reports.

### Application Scope
AACA is a full-stack, enterprise-grade GRC platform combining:
1. **Hybrid RAG Retrieval:** Powered by **Qdrant Vector DB** (for semantic concept matching) and **PostgreSQL** (for relational metadata).
2. **Flexible LLM Integration:** Supporting deep reasoning models (via Gemini and OpenRouter) to evaluate policies and generate narratives.
3. **Role-Based Workflows:** Separating duties across standard Users, Reviewers (Auditors), and System Administrators.
4. **Permanent Rule Library:** Hosting regulatory compliance constraints mapped across GRC categories (Banking, Finance, Healthcare, HR Policy, Legal, Security).

---

## 2. GRC User Roles & Access Matrix

AACA implements a strict **Role-Based Access Control (RBAC)** model to enforce separation of duties:

| User Role | Operations | Limitations |
| :--- | :--- | :--- |
| **USER (Standard)** | Upload documents, trigger audits, request finding explanations, view remediation steps, download reports. | Cannot manage the Rule Library, perform Gap Analysis, or override auditor reviews. |
| **REVIEWER (Auditor)** | Review findings (Accept/Reject/Modify), view raw LLM chain-of-thought diagnostics, view audits. | Cannot edit the Rule Library, manage user configurations, or publish final reports. |
| **ADMIN (GRC Lead)** | Manage compliance rules, run Semantic Gap Analysis, build custom reports, view audit logs, check system health. | Full read-write permissions across the entire platform. |

---

## 3. USER Walkthrough: Policies & Audits

The standard GRC User is typically a policy owner, operations manager, or business analyst who needs to audit operational files.

### Step 3.1: Dashboard Overview
- Upon logging in, the User is greeted by the **Main Dashboard**.
- High-level metric cards display the **Compliance Score**, **Total Audited Files**, and **Pending Action Items**.
- The main table lists all uploaded files, showing their **Processing Status** (Uploaded, Processing, Indexed, or Pending Review).

### Step 3.2: Uploading Audit Documents
1. Go to the **Upload Document** section.
2. Select your file (PDF, DOCX, or TXT) or paste raw text.
3. Choose the **Target Domain Mapping** (e.g., `Finance`, `Security`, `Banking`, `Healthcare`, `HR-Policy`, `Legal`).
4. Give the upload a clear title and click **Start Compliance Audit**.
   - *Under the hood:* The system uploads the document to S3, splits it into chunks, embeds them, and indexes them into Qdrant.

### Step 3.3: Viewing Audit Results
1. Navigate to **Audits** and select your processed document.
2. Review the **Compliance Score** (0-100%) and **Risk Level** (High, Medium, Low).
3. The dashboard highlights **Compliance Findings**:
   - **Compliant:** Policies matching active standard rules.
   - **Non-Compliant:** Policies missing required controls or violating constraints.

### Step 3.4: Drilling Down & Remediation
- **Explain Finding:** Click **"Explain"** on any violation. A side panel slide-out reveals the exact standard reference, the evidence text found in the document, and the LLM's step-by-step reasoning explaining the gap.
- **Remediation Plans:** Click **"Generate Plan"** on a finding. A corrective checklist appears with step-by-step actions, estimated effort hours, severity, and suggested owner roles (e.g., "IT Security Lead"). Users can update and save these steps.

---

## 4. REVIEWER Walkthrough: Audit Validation

The Reviewer performs human-in-the-loop validation on automated finding drafts before final GRC reporting.

### Step 4.1: Accessing Audits
- Reviewers log in to a dedicated dashboard focusing on documents awaiting review.
- Under **Report Audits**, select an audit flagged as `pending_review`.

### Step 4.2: Audit Finding Verification
- For each triggered violation, the Reviewer inspects:
  - The exact clause from the document.
  - The confidence score.
  - The detailed LLM reasoning.
- **Review Actions:**
  - **Accept:** Confirm the violation is valid.
  - **Reject:** Dismiss the finding (e.g., if it is a false positive).
  - **Modify:** Edit the finding title, severity, or description to match auditor context.
  - *Auto-Advance:* When the Reviewer submits the last pending finding, the system automatically rebuilds the compliance matrix, updates the audit status to `completed`, and updates the report payload.

---

## 5. ADMIN Walkthrough: GRC Operations

The GRC Admin manages the core compliance library, gap assessments, and report outputs.

### Step 5.1: Managing the Rule Library
- Navigate to **Rule Management** under the admin menu.
- **Manual Rule Creation:** Enter a title, category (`Banking`, `Finance`, `Healthcare`, `HR-Policy`, `Legal`, `Security`), control reference (e.g., GDPR Art. 5), version, and precise rule text.
- **AI Rule Builder:** Describe a rule in plain English (e.g., *"Passwords must be 12 characters and change every 90 days"*). Click **Generate Rule Structure**. The LLM automatically structures the input into compliant fields. Edit and save the rule.
- **Bulk Upload Rules:** Drop a batch of policy PDFs. Specify target category overrides and version labels. The system staging queue processes and vector-indexes them sequentially.

### Step 5.2: Semantic Gap Analysis
- Go to the **Gap Analysis** dashboard.
- Select a standard framework (e.g., **SOC 2** or **HIPAA**).
- Click **Analyze**. The system matches the framework controls against all rules in the library using vector cosine similarity.
- **Coverage Summary Cards:** Look at metrics for *Fully Covered*, *Partially Covered*, and *Missing Controls*.
- **Reviewing Gaps & Auto-Mapping:**
  - For each *Missing* or *Partial* control, AACA presents an AI-suggested rule draft.
  - Choose the correct target domain from the **Target Domain Mapping dropdown** (which displays all active domains in the system).
  - Click **Apply & Index Rule**. The new rule is instantly indexed and mapped, updating the compliance score immediately.

### Step 5.3: Custom Report Narrative Builder
- Select a finalized audit report and navigate to the **Custom Report Builder**.
- Configure the **Audience Tone** (e.g., *Executive Summary*, *Board Presentation*, *Auditor-Ready*, *Technical Detail*).
- Select the sections to include (e.g., Overview, Executive Summary, Findings, Remediation Appendices).
- Click **Generate Narrative**. The LLM rewrites raw data into a coherent, high-level narrative suited for that audience.
- Edit the markdown draft directly in the preview editor and click **Save**.
- Click **Download PDF** or **Download Word (DOCX)** to export professional GRC reports.

### Step 5.4: Monitoring & Diagnostics
- Navigate to **System Health**.
- Check real-time connectivity status for Qdrant Collections, S3 Buckets, and PostgreSQL tables.
- View **Audit Logs** showing GRC actions (e.g., who uploaded rules, who modified findings, and when parameters were reloaded).
