from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = (
    "Enterprise compliance auditor. Use only provided chunks and rules. Return one "
    "valid JSON object. No markdown, code fences, invented rules, evidence, citations, "
    "or findings."
)


def build_compliance_prompt(
    *,
    domain: str | None,
    document_chunks: list[dict[str, Any]],
    rule_context: list[dict[str, Any]],
    max_context_chars: int = 3000,
) -> str:
    document_chunks = _dedupe_text_items(document_chunks, text_key="text")
    rule_context = _dedupe_text_items(rule_context, text_key="text")
    document_chunks, rule_context = _budget_context(
        document_chunks=document_chunks,
        rule_context=rule_context,
        max_context_chars=max_context_chars,
    )
    payload = {
        "domain": domain or "general",
        "uploaded_document_chunks": [_compact_document_chunk(chunk) for chunk in document_chunks],
        "retrieved_compliance_rules": [_compact_rule(rule) for rule in rule_context],
    }
    return (
        "Compare document chunks to retrieved rules. Create findings only for missing_clause, "
        "contradiction, weak_clause, or risk; omit satisfied rules. Severity: low|medium|high. "
        "Confidence: 0..1. Return keys compliance_score, summary, findings, metadata. "
        "Each finding must include violated_rule, severity, confidence_score, evidence, "
        "recommendation, citation, matched_section, finding_type, matched_rule_text, "
        "matched_uploaded_text.\n"
        f"INPUT_JSON:{json.dumps(payload, ensure_ascii=True, separators=(',', ':'))}"
    )


def _budget_context(
    *,
    document_chunks: list[dict[str, Any]],
    rule_context: list[dict[str, Any]],
    max_context_chars: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    max_context_chars = max(1400, int(max_context_chars or 3000))
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
    per_item = max(240, total_chars // max(len(items), 1))
    budgeted: list[dict[str, Any]] = []
    for item in items:
        copied = dict(item)
        copied[text_key] = _trim_text(str(copied.get(text_key) or ""), per_item)
        budgeted.append(copied)
    return budgeted


def _dedupe_text_items(items: list[dict[str, Any]], *, text_key: str) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = _normalized_text_key(str(item.get(text_key) or ""))
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(item)
    return deduped


def _compact_document_chunk(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_empty(
        {
            "chunk_id": item.get("chunk_id"),
            "section": item.get("section"),
            "page_number": item.get("page_number"),
            "citation": item.get("citation_label"),
            "text": item.get("text"),
        },
    )


def _compact_rule(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_empty(
        {
            "chunk_id": item.get("chunk_id"),
            "score": item.get("score"),
            "citation": item.get("citation"),
            "domain": item.get("domain"),
            "section": item.get("section"),
            "source": item.get("source"),
            "coverage_score": item.get("coverage_score"),
            "contradiction_signals": item.get("contradiction_signals"),
            "text": item.get("text"),
        },
    )


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _normalized_text_key(text: str) -> str:
    return " ".join(str(text or "").lower().split())[:1200]


def _trim_text(text: str, limit: int) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if len(normalized) <= limit:
        return normalized
    clipped = normalized[:limit].rstrip()
    sentence_end = max(clipped.rfind("."), clipped.rfind(";"), clipped.rfind("\n"))
    if sentence_end >= max(120, int(limit * 0.5)):
        return clipped[: sentence_end + 1].strip()
    return clipped
