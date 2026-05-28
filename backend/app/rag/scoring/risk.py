from __future__ import annotations


def classify_risk(*, confidence_score: float, finding_type: str) -> str:
    if finding_type == "violation" and confidence_score >= 0.75:
        return "HIGH"
    if confidence_score >= 0.7:
        return "MEDIUM"
    return "LOW"

