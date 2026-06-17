# User Dashboard KPIs & Metrics

## Introduction & Platform Scope

The **AI Audit & Compliance Assistant** is an enterprise-grade platform designed to automate the compliance validation lifecycle and directly solve the challenges of traditional auditing methods. In contrast to traditional auditing—which is extremely time-intensive (averaging 40 to 160 person-hours per audit to cross-reference policies manually), error-prone (human auditors miss about 15% to 30% of gaps due to fatigue and cognitive bias), and lacking in machine-verifiable traceability—this platform automates validation by ingesting policy documents and compliance rules, running a hybrid vector and keyword search (RAG), and generating explainable, evidence-backed findings. To secure operations and enforce separation of duties, Role-Based Access Control (RBAC) is implemented using JSON Web Tokens (JWT), allowing standard users, reviewers, and admins to safely register and login to their designated workspace views.

This document details the Key Performance Indicators (KPIs) and operational metrics displayed in the dashboard when logged in with the standard **USER** role.

Reference file: [page.tsx](file:///i:/AMD%20Hackathon/amd-version/frontend/src/app/dashboard/page.tsx)


---

## 1. Executive Summary KPIs (Main Metrics Grid)

These four primary signals are displayed at the top of the dashboard to give GRC leaders an immediate overview of the organization's compliance posture.

### 1.1 Compliance Score
- **Component**: `MetricCard`
- **Icon**: `Gauge`
- **Value**: The average score across all parsed and completed compliance audits (normalized to a percentage format, e.g., `85%`). Displays `-` if no audit runs have completed.
- **Detail Label**: `"Latest completed backend assessment"` or `"No completed result returned"`.
- **Tone**: Green/low-risk if score is $\ge 80\%$, cyan/info otherwise.

### 1.2 Active Audits
- **Component**: `MetricCard`
- **Icon**: `Activity`
- **Value**: Count of audits currently in `uploaded`, `processing`, or `indexing` status.
- **Detail Label**: `"Queued or processing now"`.

### 1.3 Documents
- **Component**: `MetricCard`
- **Icon**: `UploadCloud`
- **Value**: Total number of uploaded files in the workspace.
- **Detail Label**: `"{failedAudits} failed assessment runs"` (tracks runs that did not complete due to parsing or service issues).

### 1.4 Critical Findings
- **Component**: `MetricCard`
- **Icon**: `ShieldCheck`
- **Value**: Sum of `CRITICAL` or `HIGH` severity violations flagged across all completed reports.
- **Detail Label**: `"Critical or high-risk counts returned"`.

---

## 2. Backend Signals & Operational Indicators

These metrics are displayed in the **Backend Signals** card, helping track data indexing and overall audit volume.

### 2.1 Compliance Domains
- **Value**: Number of active compliance domains/categories registered in the database (e.g., `Banking`, `Finance`, `Healthcare`, `HR-Policy`, `Legal`, `Security`).
- **Display format**: `"{count} returned"`.

### 2.2 Completed Audits
- **Value**: The proportion of total audit runs that successfully processed to completion.
- **Display format**: `"{completed_count} of {total_count}"`.

### 2.3 Open Risk Assessments
- **Value**: The number of completed audits with an overall risk classification of `HIGH` or `MEDIUM`.

### 2.4 Latest Result
- **Value**: Timestamp of the most recently finished audit (formatted date, e.g., `June 17, 2026`).

---

## 3. Recent Activity Specific KPIs

Displayed per audit run in the **Recent Activity** history feed.

### 3.1 Analysis Confidence
- **Value**: The confidence percentage returned by the AI audit agent for that specific document's run.
- **Display format**: `"Analysis confidence: {percentage}"` (e.g. `98%`).

### 3.2 Overall Risk Level
- **Value**: The severity risk classification (`HIGH`, `MEDIUM`, `LOW`, `NONE`) calculated for the document.
- **Display format**: Styled badge with contextual coloring.

---

## 4. Compliance Check & Document Upload Workflow

Standard users can run manual compliance checks by uploading corporate policy files or by pasting raw text directly into the dashboard.

### 4.1 Compliance Check Setup
To initiate a check, standard users upload a PDF, DOCX, or TXT document or input raw text. User must select a target compliance domain mapping (such as Banking, Finance, Healthcare, HR-Policy, Legal, or Security) so that rules are correctly scoped. Submitting this form runs the file through the backend LangGraph RAG pipeline to compare the policies against compliance library rules.

### 4.2 Temporary Storage & Security
Under the standard user workflow, uploaded compliance files are stored temporarily inside the `temp-user-uploads/` folder of the S3-compatible storage bucket rather than the permanent folder. These ephemeral document records and their indexed vectors have a retention limit of 24 hours (configured by `TEMP_DOCUMENT_RETENTION_HOURS`), after which background worker scripts automatically prune them from S3, PostgreSQL, and Qdrant. During this retention window, text is extracted from the document using fallback parsers, embedded into vector chunks, and analyzed by LLM agents to generate compliance scores, trace evidence citations, and report violations.

---

## 5. Backend Ingestion & Processing Lifecycle

When a standard user uploads a corporate policy document, the backend initiates a structured multi-stage processing pipeline. First, the application uploads the file bytes directly to AWS S3 under the temporary uploads prefix while saving the initial metadata record in PostgreSQL. Next, the client registers the audit run, triggering an asynchronous worker task that handles the heavy processing in the background without blocking the user interface. The background worker parses the document text using fallback extractors, splits it into semantic chunks, generates vector embeddings, and indexes them in Qdrant Cloud. Afterward, the workflow executes a hybrid vector and keyword search to retrieve matching regulatory rules, which are reranked for precision. Finally, compliance LLM agents check the document chunks against the rules, trace exact evidence citations and page numbers, and persist the completed compliance score and findings to the database.

---

## 6. Compliance Operations & Audit Runs Page

The Audit Runs page under Compliance Operations serves as a comprehensive tracking center where standard users can monitor the lifecycle of all policy assessments in real time. The interface presents consolidated metric cards summarizing active audits (running or queued), completed assessments, high-risk items (flagged as overall high risk by the backend risk assessment engine), and failed runs. Standard users can inspect a detailed records table displaying unique run IDs, linked policy document names, domain categories, overall statuses, AI confidence scores, start times, and completion timestamps. A searchable data grid allows users to filter by specific audit states, export the logs to a CSV format, and click action shortcuts to navigate directly to completed audit reports or view active processing logs.

---

## 7. Compliance Intelligence Report Page

The Compliance Intelligence Report page, accessed under the "Compliance results" section, displays the finalized and published compliance results of a completed audit run. This screen provides an interface for auditing analysis, organizing data into evidence-backed findings, rule matches, and remediation context. It showcases a visual Gauge card of the overall Compliance Score, a summary of risk violations, and a detailed list of individual findings mapped with page numbers and exact quote excerpts from the source document. From this page, users can open interactive drawers to drill down into the findings: the "Explain Finding" drawer presents the AI's step-by-step chain-of-thought diagnostics, and the "Remediation Plan" drawer provides a clear corrective action list with owner roles and effort hour estimates. Additionally, the dashboard offers quick action buttons to download the report in standard JSON or printable PDF formats.

---

## 8. Compliance Intelligence Findings Page

The Findings page, located under the "Compliance Intelligence" section, serves as a consolidated catalog displaying all compliance violations detected across all completed audit runs. At the top of the interface, four metric cards group and count the total findings based on their severity classifications: Critical, High, Medium, and Low. Below this executive view, the page displays a detailed list card showcasing each finding with its corresponding violated rule description, severity badges, risk levels, and AI confidence ratings. Standard users can read the specific corrective recommendations for each violation, view the name and domain of the source document, check the current auditor review status, and use direct navigation links to open the full compliance intelligence report.

---

## 9. Compliance Intelligence Evidence Library Page

The Evidence Library page, found under the "Compliance Intelligence" section, serves as a central repository consolidating all verified evidence citations compiled across your compliance audits. The page layout starts with three metric cards summarizing high-level stats: Total Evidence items collected, unique Audited Documents containing evidence, and the number of High Confidence snippets showing an AI score of 80% or above. Below these statistics, the Evidence Citations list displays each individual citation card detailing the specific Document Section, page number labels, source types, and semantic confidence percentages. Standard users can inspect the raw text excerpt retrieved directly from the corporate policy files, view the name and domain of the audited document, and use quick links to open the original report where the evidence was established.

---

## 10. Administrator Role & Purpose

Within the application, the Administrator functions as both a master data manager and compliance approver. As a master data manager, the Admin holds control over the core Rule Library and framework policies, enabling them to manually draft compliance rules, upload reference regulatory PDFs, and run natural language queries to auto-generate structured rule records. Beyond database administration, the Admin serves as the final compliance approver who verifies automated RAG-based audit outputs. In this capacity, they review, modify, or reject AI-generated findings, validate traced citation snippets, and approve or customize the AI-generated remediation suggestions before publishing the final executive compliance report.

---

## 11. Administration Admin Dashboard Page

The Admin Dashboard, accessed under the "Administration" section, provides system leads with real-time visibility into the system's operational health, user activity, and vector database status. The page displays four core metric cards summarizing total system users, uploaded policy documents, completed audit runs, and high-risk audits identified across the workspace. Below these high-level statistics, the page is divided into two primary diagnostic views: Vector Storage Health and Recent System Logs. The Vector Storage Health panel displays the connection status of Qdrant Cloud and shows points and vectors counts for active collections (such as compliance rules and document chunks). The Recent System Logs panel displays a chronological list of audit logs capturing critical actions, entity types, and timestamps, allowing admins to track system changes, user operations, and pipeline activities immediately.

---

## 12. Administration Rule Builder Page

The Rule Builder page, under the "Rule Management" section, provides administrators with an interactive workspace to create, configure, and validate new compliance requirements. The page features a dual-column layout dividing rule setup from testing utilities. On the left side, admins can describe requirements in plain English using the AI-Powered Rule Generator, which automatically populates form fields including category, title, control text, and standard references. Alternatively, they can manually define the category, title, specific rule text, reference clauses, jurisdictions, and effectivity dates. Once the rule is saved and receives a unique ID, the right-side Test Rule panel allows admins to copy and paste sample policy document excerpts, running instant mock evaluations to preview whether the newly created rule successfully matches the sample text, complete with AI confidence scores, detailed explanations, and specific matching text snippets.

---

## 13. Compliance Intelligence Semantic Gap Analysis Page

The Semantic Gap Analysis page, located under the "Compliance Intelligence" section, enables administrators to cross-reference their operational compliance rules against established industry frameworks (such as SOC 2 or HIPAA). When an analysis is initiated, the backend uses AI-driven semantic embeddings to compare framework requirements against the library of indexed policy rules. At the top of the interface, the page showcases a visual framework coverage score and three metric cards displaying the total count of requirements classified as Fully Covered, Partially Covered, or Missing. Below the summaries, a detailed requirement list highlights specific gap diagnostics. For any requirement flagged as partial or missing, the tool displays an AI-suggested rule structure designed to bridge the compliance gap. Admins can review the draft, modify the target category mapping via a dropdown list populated with database domains, and click a single "Apply & Index Rule" button to instantly save and vector-index the new rule, which dynamically updates the framework coverage map.

---

## 14. Compliance Evidence Automation Live Evidence Collectors Page

The Live Evidence Collectors page, located under the "Compliance Evidence Automation" section, allows users to schedule, manage, and execute automated integrations to fetch compliance evidence from external environments. The screen features a split layout containing the Collectors Registry and the Collected Trace Logs. In the registry, users can view active connectors for HTTP REST APIs, SQL database queries, and local Python scripts, as well as their configured cron schedules (e.g., daily sweeps), target compliance domains, and last-run statuses. By toggling the add form, users can customize new collectors, set target URL endpoints, write custom SELECT queries or script paths, and map response payloads to evidence text and citation fields. Clicking the execution play button triggers the collector in the background, which queries external databases, GitHub repositories, or security agents, hashes the retrieved values, and registers the parsed citations in the real-time Collected Trace Logs panel on the right.

---

## 15. Compliance Digital Twin Page

The Organization Compliance Twin page, located under the "Compliance Digital Twin" section, provides standard users with an aggregated compliance profile of the organization compiled from all uploaded documents. The dashboard header features a "Refresh Twin" action to trigger backend updates. At the top of the interface, four metric cards showcase the Maturity Score, Coverage Score, Risk Pressure index, and the total count of historical compliance snapshots. Below this view, the page displays several panels: a Compliance Maturity card with detail progress and text summaries; a Risk Heatmap tracking policy counts and risk levels mapped across domains; a Missing Policies registry highlighting domains where rules are absent; a scrollable Policy Inventory displaying files with active scores, findings counts, and risk levels; and a Compliance History card listing chronological snapshots of the organization's compliance progression over time.




