from datetime import datetime, timedelta
import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.db.models.audit import Finding, EvidenceLink, AuditRun
from backend.app.db.models.ai_features import FindingExplanationCache
from backend.app.db.models.user import User
from backend.app.services.llm_service import llm_service

logger = get_logger(__name__)

class FindingExplanationService:
    async def get_explanation(
        self,
        *,
        db: Session,
        user: User,
        finding_id: str,
    ) -> dict:
        # 1. Fetch the finding
        finding = db.get(Finding, finding_id)
        if not finding:
            raise ValueError("Finding not found")

        # 2. Authorization check
        audit = db.get(AuditRun, finding.audit_id)
        is_privileged = (user.role or "").upper() in {"ADMIN", "REVIEWER"}
        is_owner = audit and audit.user_id == user.id
        if not (is_privileged or is_owner):
            raise PermissionError("Not authorized to access explanations for this finding")

        # 3. Check database cache (valid for 24 hours)
        cache_stmt = select(FindingExplanationCache).where(FindingExplanationCache.finding_id == finding_id)
        cache_entry = db.scalar(cache_stmt)
        if cache_entry and (datetime.utcnow() - cache_entry.created_at < timedelta(hours=24)):
            return {
                "finding_id": finding_id,
                "explanation_text": cache_entry.explanation_text,
                "evidence_list": cache_entry.evidence_list,
                "confidence_score": cache_entry.confidence_score,
            }

        # 4. Gather evidence links
        evidence_links = list(
            db.scalars(select(EvidenceLink).where(EvidenceLink.finding_id == finding_id))
        )
        
        citations_text = ""
        for i, link in enumerate(evidence_links, 1):
            citations_text += (
                f"[{i}] Section: {link.section_title or 'N/A'}, Page: {link.page_number or 'N/A'}, "
                f"Text: \"{link.citation_text}\"\n"
            )

        # 5. Call LLM to generate structured explanation
        system_prompt = (
            "You are a regulator-grade compliance audit explainer. Your job is to analyze a compliance finding and "
            "provide a detailed, natural-language explanation of why this finding was flagged as a violation, "
            "along with a list of matching evidences. You must return your response in JSON format with "
            "the following keys:\n"
            "- 'explanation_text': a comprehensive, clear explanation of the mismatch between the compliance rule and the document evidence.\n"
            "- 'evidence_list': a list of objects, each containing 'text' (the exact text segment), 'page' (integer or null), and 'section' (string or null) representing specific citations.\n"
            "- 'confidence_score': a float between 0.0 and 1.0 representing your confidence in this explanation.\n"
        )
        
        user_prompt = (
            f"Compliance Finding Details:\n"
            f"Rule Violated: {finding.violated_rule}\n"
            f"Finding Details: {finding.explanation}\n"
            f"Recommendation: {finding.recommendation}\n\n"
            f"Document Citations:\n"
            f"{citations_text or 'No direct citations available.'}\n\n"
            f"Generate the structured JSON response now."
        )

        try:
            llm_result = llm_service.generate_json(
                system=system_prompt,
                user=user_prompt,
                audit_id=finding.audit_id,
                document_id=finding.document_id,
                required_keys={"explanation_text", "evidence_list", "confidence_score"},
            )
        except Exception as exc:
            logger.error("LLM generation failed for finding explanation %s: %s", finding_id, exc)
            # Graceful fallback: construct simple explanation from finding itself
            llm_result = {
                "explanation_text": f"This finding was flagged because the document failed to satisfy: {finding.violated_rule}. Details: {finding.explanation}",
                "evidence_list": [
                    {
                        "text": link.citation_text,
                        "page": link.page_number,
                        "section": link.section_title,
                    }
                    for link in evidence_links
                ],
                "confidence_score": finding.confidence_score or 0.7,
            }

        # Validate structure of llm_result
        explanation_text = llm_result.get("explanation_text") or f"Finding flagged for rule violation: {finding.violated_rule}"
        evidence_list = llm_result.get("evidence_list") or []
        confidence_score = float(llm_result.get("confidence_score") or finding.confidence_score or 0.8)

        # 6. Save/update cache
        if cache_entry:
            cache_entry.explanation_text = explanation_text
            cache_entry.evidence_list = evidence_list
            cache_entry.confidence_score = confidence_score
            cache_entry.created_at = datetime.utcnow()
        else:
            cache_entry = FindingExplanationCache(
                finding_id=finding_id,
                explanation_text=explanation_text,
                evidence_list=evidence_list,
                confidence_score=confidence_score,
            )
            db.add(cache_entry)
        
        db.commit()

        return {
            "finding_id": finding_id,
            "explanation_text": explanation_text,
            "evidence_list": evidence_list,
            "confidence_score": confidence_score,
        }

finding_explanation_service = FindingExplanationService()
