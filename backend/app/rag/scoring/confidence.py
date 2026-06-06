from __future__ import annotations


def clamp_score(score: float) -> float:
    return max(0.0, min(1.0, round(score, 4)))


def finding_confidence(*, retrieval_score: float, evidence_score: float, overlap_score: float) -> float:
    return clamp_score((0.45 * retrieval_score) + (0.35 * evidence_score) + (0.20 * overlap_score))

