from __future__ import annotations


def citation_quality_score(payload: dict) -> float:
    score = 0.0
    if payload.get("citation_label"):
        score += 0.35
    if payload.get("page_number"):
        score += 0.25
    if payload.get("section_title"):
        score += 0.15
    if payload.get("text"):
        score += 0.25
    return min(score, 1.0)

