from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.db.models.ai_features import FrameworkRequirement
from backend.app.db.models.rule import ComplianceRule
from backend.app.rag.indexing.embeddings import embedding_service
from backend.app.rag.indexing.qdrant_store import qdrant_store
from backend.app.services.llm_service import llm_service

logger = get_logger(__name__)

class GapAnalysisService:
    def seed_framework_requirements(self, db: Session) -> None:
        """Seed baseline framework requirements if the table is empty."""
        count = db.scalar(select(FrameworkRequirement))
        if count is not None:
            return

        logger.info("Seeding baseline framework requirements for SOC2 and HIPAA...")
        baselines = [
            # SOC2 Controls
            FrameworkRequirement(
                framework="SOC2",
                control_id="CC6.1",
                title="Logical Access Controls",
                description="Logical access controls are implemented to manage access credentials, secure transmission channels, and authenticate users uniquely.",
                suggested_template="Passwords must be at least 12 characters, include a special symbol, and lock accounts after 5 failed login attempts.",
            ),
            FrameworkRequirement(
                framework="SOC2",
                control_id="CC6.2",
                title="User Registration & Termination",
                description="Review and authorize users before access permissions are granted, and revoke permissions immediately upon user separation/termination.",
                suggested_template="User access requests must be approved by IT Security management. Employee offboarding checklist must revoke application access keys within 24 hours.",
            ),
            FrameworkRequirement(
                framework="SOC2",
                control_id="CC6.3",
                title="Data Transmission & Storage Encryption",
                description="Encrypt confidential and sensitive corporate data both in transit across public networks and at rest in local/cloud databases.",
                suggested_template="All cloud databases storing personal identifiable information must be encrypted at rest using AES-256. TLS 1.3 must be enforced for public network APIs.",
            ),
            # HIPAA Controls
            FrameworkRequirement(
                framework="HIPAA",
                control_id="164.312(a)(1)",
                title="Access Control",
                description="Implement logical procedures that restrict access to systems containing Electronic Protected Health Information (ePHI) to authorized users and roles only.",
                suggested_template="Access to patient healthcare records (ePHI) is restricted to users with direct clinical care roles. Non-clinical accounts must be blocked from medical files.",
            ),
            FrameworkRequirement(
                framework="HIPAA",
                control_id="164.312(c)(1)",
                title="Integrity Controls",
                description="Implement technical policies and mechanisms to protect electronic protected health information from unauthorized alteration, destruction, or tampering.",
                suggested_template="Implement digital signatures or checksum hashing (SHA-256) on medical diagnostic uploads to verify file integrity and prevent data tampering.",
            ),
            FrameworkRequirement(
                framework="HIPAA",
                control_id="164.312(e)(1)",
                title="Transmission Security",
                description="Guard against unauthorized access to electronic protected health information (ePHI) that is being transmitted over an electronic communications network.",
                suggested_template="Patient health summaries sent over public networks must be encrypted via secure end-to-end communication channels (such as HTTPS with TLS 1.3).",
            ),
        ]
        
        db.add_all(baselines)
        db.commit()

    async def analyze_gap(self, *, db: Session, framework: str) -> list[dict]:
        """Perform semantic gap analysis for a framework by matching against active rules in Qdrant."""
        self.seed_framework_requirements(db)

        # 1. Fetch requirements
        stmt = select(FrameworkRequirement).where(FrameworkRequirement.framework == framework.upper())
        requirements = list(db.scalars(stmt).all())
        if not requirements:
            raise ValueError(f"No requirements found for framework '{framework}'. Available: SOC2, HIPAA.")

        results = []
        for req in requirements:
            # 2. Embed requirement description
            try:
                emb = embedding_service.embed_texts([req.description])[0]
                # Search Qdrant for matching compliance rules
                search_results = qdrant_store.search(
                    collection_name=settings.qdrant_rule_collection,
                    query_vector=emb,
                    filters={"rule_status": "active"},
                    top_k=3,
                )
            except Exception as exc:
                logger.error("Vector search failed during gap analysis for req %s: %s", req.control_id, exc)
                search_results = []

            # 3. Determine coverage status
            best_match = search_results[0] if search_results else None
            score = best_match.score if best_match else 0.0

            status_str = "MISSING"
            matched_rule_data = None
            
            if score >= 0.80:
                status_str = "COVERED"
            elif score >= 0.55:
                status_str = "PARTIAL"
            
            if best_match:
                # Fetch matching rule from SQL
                rule_id = best_match.payload.get("document_id")
                rule = None
                if rule_id:
                    rule = db.get(ComplianceRule, rule_id)
                    if not rule:
                        rule = db.scalar(
                            select(ComplianceRule).where(ComplianceRule.rule_document_id == rule_id)
                        )
                if rule:
                    matched_rule_data = {
                        "id": rule.id,
                        "title": rule.title,
                        "rule_text": rule.rule_text,
                        "category": rule.category,
                        "reference": rule.reference,
                    }

            # 4. Generate suggested draft rule if coverage is MISSING or PARTIAL
            suggested_rule = None
            if status_str in ("MISSING", "PARTIAL"):
                suggested_rule = await self._generate_suggested_rule(req)

            results.append({
                "control_id": req.control_id,
                "title": req.title,
                "description": req.description,
                "status": status_str,
                "match_score": round(score, 3),
                "matched_rule": matched_rule_data,
                "suggested_rule": suggested_rule,
            })

        return results

    async def _generate_suggested_rule(self, req: FrameworkRequirement) -> dict:
        """Use LLM to generate a compliant rule draft for a control gap."""
        system_prompt = (
            "You are an expert compliance architect. Write a suggested compliance rule that addresses the compliance control gap.\n"
            "You must respond with a JSON object containing exactly the following keys:\n"
            "- 'title': string (a short descriptive title)\n"
            "- 'category': string (must be one of: 'HR', 'Security', 'Finance', 'Legal', 'Insurance', 'GDPR', 'Internal Policies', 'Banking', 'Healthcare', 'HR-Policy')\n"
            "- 'rule_text': string (the specific compliance rule requirement statement)\n"
            "- 'description': string (a brief explanation of what the rule requires)\n"
            "- 'reference': string (should be the control ID, e.g. 'SOC2 CC6.1' or 'HIPAA 164.312(a)(1)')\n"
        )
        
        user_prompt = (
            f"Control Gap to Address:\n"
            f"Framework: {req.framework}\n"
            f"Control ID: {req.control_id}\n"
            f"Control Title: {req.title}\n"
            f"Control Description: {req.description}\n"
            f"Suggested Template Guideline: {req.suggested_template or 'N/A'}\n\n"
            f"Write the JSON compliance rule now."
        )

        try:
            llm_result = llm_service.generate_json(
                system=system_prompt,
                user=user_prompt,
                required_keys={"title", "category", "rule_text", "description", "reference"},
            )
        except Exception as exc:
            logger.error("Failed to generate suggested rule for gap control %s: %s", req.control_id, exc)
            llm_result = {
                "title": f"{req.title} Policy Control",
                "category": "Security" if req.framework == "SOC2" else "Legal",
                "rule_text": req.suggested_template or f"Ensure compliance with control requirements: {req.description}",
                "description": f"Enforces compliance with {req.framework} control {req.control_id}.",
                "reference": f"{req.framework} {req.control_id}"
            }

        return {
            "title": llm_result.get("title") or f"{req.title} Policy Control",
            "category": llm_result.get("category") or "Internal Policies",
            "rule_text": llm_result.get("rule_text") or f"Ensure compliance with control requirement: {req.description}",
            "description": llm_result.get("description") or f"Enforces compliance with {req.framework} control {req.control_id}.",
            "reference": llm_result.get("reference") or f"{req.framework} {req.control_id}",
        }

gap_analysis_service = GapAnalysisService()
