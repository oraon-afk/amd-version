from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = (
    "You are an enterprise compliance auditor. Analyze only the uploaded document "
    "chunks and retrieved rules provided in the prompt. Return ONLY valid JSON. "
    "No markdown. No explanations. No code fences. Output must be parseable by "
    "Python json.loads(). Do not truncate. Do not invent rules, evidence, citations, "
    "or findings."
)


def build_compliance_prompt(
    *,
    domain: str | None,
    document_chunks: list[dict[str, Any]],
    rule_context: list[dict[str, Any]],
    max_context_chars: int = 7000,
) -> str:
    document_chunks, rule_context = _budget_context(
        document_chunks=document_chunks,
        rule_context=rule_context,
        max_context_chars=max_context_chars,
    )
    payload = {
        "domain": domain or "general",
        "uploaded_document_chunks": document_chunks,
        "retrieved_compliance_rules": rule_context,
        "required_output_schema": {
            "compliance_score": "number between 0 and 1",
            "summary": "string",
            "findings": [
                {
                    "violated_rule": "string",
                    "severity": "low|medium|high",
                    "confidence_score": "number between 0 and 1",
                    "evidence": "exact uploaded-document excerpt or concise absence statement",
                    "recommendation": "string",
                    "citation": "rule citation/source string",
                    "matched_section": "uploaded document section or rule section",
                    "finding_type": "missing_clause|contradiction|weak_clause|risk",
                    "matched_rule_text": "exact rule excerpt",
                    "matched_uploaded_text": "exact uploaded-document excerpt when present",
                }
            ],
            "metadata": {
                "domain": "string",
                "retrieved_rules": "integer",
                "analyzed_chunks": "integer",
            },
        },
    }
    return (
        "Compare the uploaded document against the retrieved compliance rules.\n"
        "Identify only evidence-backed missing clauses, contradictions, weak clauses, or material risks.\n"
        "If the document satisfies a rule, do not create a finding for that rule.\n"
        "Severity must be one of low, medium, or high.\n"
        "Confidence scores must be numeric values from 0 to 1.\n"
        "Return ONLY valid JSON. No markdown, explanations, comments, or code fences.\n"
        "The response must be parseable by Python json.loads() and must not be truncated.\n"
        "Return exactly one JSON object with keys: compliance_score, summary, findings, metadata.\n\n"
        f"INPUT:\n{json.dumps(payload, ensure_ascii=True)}"
    )


def _budget_context(
    *,
    document_chunks: list[dict[str, Any]],
    rule_context: list[dict[str, Any]],
    max_context_chars: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    max_context_chars = max(1500, int(max_context_chars or 7000))
    document_budget = int(max_context_chars * 0.58)
    rule_budget = max_context_chars - document_budget
    return (
        _budget_text_items(document_chunks, text_key="text", total_chars=document_budget),
        _budget_text_items(rule_context, text_key="text", total_chars=rule_budget),
    )


def _budget_text_items(
    items: list[dict[str, Any]],
    *,
    text_key: str,
    total_chars: int,
) -> list[dict[str, Any]]:
    if not items:
        return []
    per_item = max(350, total_chars // max(len(items), 1))
    budgeted: list[dict[str, Any]] = []
    for item in items:
        copied = dict(item)
        copied[text_key] = _trim_text(str(copied.get(text_key) or ""), per_item)
        budgeted.append(copied)
    return budgeted


def _trim_text(text: str, limit: int) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if len(normalized) <= limit:
        return normalized
    clipped = normalized[:limit].rstrip()
    sentence_end = max(clipped.rfind("."), clipped.rfind(";"), clipped.rfind("\n"))
    if sentence_end >= max(120, int(limit * 0.5)):
        return clipped[: sentence_end + 1].strip()
    return clipped
