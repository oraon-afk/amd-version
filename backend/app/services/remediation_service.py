from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.logging import get_logger
from backend.app.db.models.audit import Finding, AuditRun
from backend.app.db.models.ai_features import RemediationPlan
from backend.app.db.models.user import User
from backend.app.services.llm_service import llm_service
from backend.app.schemas.remediation import RemediationPlanUpdateRequest

logger = get_logger(__name__)

class RemediationService:
    async def get_remediation_plan(
        self,
        *,
        db: Session,
        user: User,
        finding_id: str,
    ) -> RemediationPlan | None:
        """Fetch the remediation plan if it exists."""
        finding = db.get(Finding, finding_id)
        if not finding:
            raise ValueError("Finding not found")

        # Authorization check
        audit = db.get(AuditRun, finding.audit_id)
        is_privileged = (user.role or "").upper() in {"ADMIN", "REVIEWER"}
        is_owner = audit and audit.user_id == user.id
        if not (is_privileged or is_owner):
            raise PermissionError("Not authorized to access remediation plans for this finding")

        stmt = select(RemediationPlan).where(RemediationPlan.finding_id == finding_id)
        return db.scalar(stmt)

    async def generate_remediation_plan(
        self,
        *,
        db: Session,
        user: User,
        finding_id: str,
    ) -> RemediationPlan:
        """Generate a new remediation plan using LLM and save it."""
        finding = db.get(Finding, finding_id)
        if not finding:
            raise ValueError("Finding not found")

        # Authorization check
        audit = db.get(AuditRun, finding.audit_id)
        is_privileged = (user.role or "").upper() in {"ADMIN", "REVIEWER"}
        is_owner = audit and audit.user_id == user.id
        if not (is_privileged or is_owner):
            raise PermissionError("Not authorized to generate remediation plans for this finding")

        # Check if one already exists
        existing = await self.get_remediation_plan(db=db, user=user, finding_id=finding_id)
        if existing:
            return existing

        # Generate using LLM
        system_prompt = (
            "You are an expert compliance officer and systems engineer. Your task is to generate a structured, "
            "actionable remediation plan to correct a policy violation finding.\n"
            "You must return a JSON object with the following keys:\n"
            "- 'steps': a list of clear, sequential, actionable string steps to remediate/resolve the finding.\n"
            "- 'estimated_effort_hours': an integer representing the estimated total hours required to execute the remediation steps.\n"
            "- 'priority': a string, either 'HIGH', 'MEDIUM', or 'LOW', based on the severity and impact of the violation.\n"
            "- 'suggested_owner_role': a string representing the typical job role (e.g., 'Security Officer', 'Systems Administrator', 'Compliance Lead') that should own the execution of this plan.\n"
        )
        
        user_prompt = (
            f"Compliance Finding Details:\n"
            f"Rule Violated: {finding.violated_rule}\n"
            f"Severity: {finding.severity}\n"
            f"Finding Details: {finding.explanation}\n"
            f"Recommendation: {finding.recommendation}\n\n"
            f"Generate the structured JSON response now."
        )

        try:
            llm_result = llm_service.generate_json(
                system=system_prompt,
                user=user_prompt,
                audit_id=finding.audit_id,
                document_id=finding.document_id,
                required_keys={"steps", "estimated_effort_hours", "priority", "suggested_owner_role"},
            )
        except Exception as exc:
            logger.error("LLM remediation plan generation failed for finding %s: %s", finding_id, exc)
            # Graceful fallback
            llm_result = {
                "steps": [
                    f"Review the compliance requirement: {finding.violated_rule}",
                    f"Analyze why it was violated: {finding.explanation}",
                    f"Implement the recommended action: {finding.recommendation}",
                    "Verify the correction with a follow-up compliance scan."
                ],
                "estimated_effort_hours": 8,
                "priority": finding.severity if finding.severity in ("HIGH", "MEDIUM", "LOW") else "MEDIUM",
                "suggested_owner_role": "Compliance Officer"
            }

        steps = llm_result.get("steps") or ["Analyze and fix the violation."]
        try:
            estimated_effort_hours = int(llm_result.get("estimated_effort_hours") or 4)
        except (ValueError, TypeError):
            estimated_effort_hours = 4
        
        priority = str(llm_result.get("priority") or finding.severity or "MEDIUM").upper()
        if priority not in ("HIGH", "MEDIUM", "LOW"):
            priority = "MEDIUM"

        suggested_owner_role = str(llm_result.get("suggested_owner_role") or "Compliance Officer")

        plan = RemediationPlan(
            finding_id=finding_id,
            steps=steps,
            estimated_effort_hours=estimated_effort_hours,
            priority=priority,
            suggested_owner_role=suggested_owner_role,
            approved=False,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        return plan

    async def update_remediation_plan(
        self,
        *,
        db: Session,
        user: User,
        finding_id: str,
        payload: RemediationPlanUpdateRequest,
    ) -> RemediationPlan:
        """Update or approve an existing remediation plan."""
        finding = db.get(Finding, finding_id)
        if not finding:
            raise ValueError("Finding not found")

        # Authorization check: only ADMIN or REVIEWER can edit or approve plans
        if (user.role or "").upper() not in {"ADMIN", "REVIEWER"}:
            raise PermissionError("Only Admins and Reviewers are authorized to modify or approve remediation plans")

        plan = await self.get_remediation_plan(db=db, user=user, finding_id=finding_id)
        if not plan:
            raise ValueError("Remediation plan not found for this finding")

        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(plan, key, value)

        db.commit()
        db.refresh(plan)
        return plan

remediation_service = RemediationService()
