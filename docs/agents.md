# Agent Module Structure

Agents are lightweight workflow modules. They do not self-plan, call each other recursively, or make autonomous decisions outside the audit workflow.

## Document Agent

Path:

```text
backend/app/agents/document_agent.py
```

Responsibilities:

- PDF parsing
- OCR/text extraction handoff if needed
- Text normalization
- Semantic chunking
- Metadata extraction
- Page and character span mapping

Inputs:

```text
document_id
s3_uri
content_type
tenant_id
audit_id
```

Outputs:

```text
parsed_document
document_chunks
document_metadata
```

## Retrieval Agent

Path:

```text
backend/app/agents/retrieval_agent.py
```

Responsibilities:

- Build compliance retrieval queries
- Run vector retrieval
- Run BM25 retrieval
- Merge results
- Rerank candidates
- Apply metadata filters
- Validate context quality

Outputs:

```text
retrieved_rule_chunks
retrieval_scores
context_validation_result
```

## Compliance Agent

Path:

```text
backend/app/agents/compliance_agent.py
```

Responsibilities:

- Compare uploaded document chunks against retrieved rules
- Detect violations
- Detect missing clauses
- Generate grounded explanations
- Assign finding confidence
- Classify risk level

Outputs:

```text
findings
risk_summary
confidence_summary
```

## Evidence Agent

Path:

```text
backend/app/agents/evidence_agent.py
```

Responsibilities:

- Link findings to uploaded document evidence
- Link findings to rule evidence
- Validate citation quality
- Map citations to page and span references
- Mark weak evidence as low confidence

Outputs:

```text
evidence_links
citation_quality_scores
```

## Report Agent

Path:

```text
backend/app/agents/report_agent.py
```

Responsibilities:

- Create audit summary
- Summarize violations and missing clauses
- Generate recommendations
- Create report JSON
- Prepare future PDF export payload

Outputs:

```text
audit_report
report_s3_uri
```

