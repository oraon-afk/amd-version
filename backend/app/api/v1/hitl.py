"""
Feature 1: HITL – FastAPI router for finding review and report publish.
Feature 2: Full diagnostics endpoint.

Routes:
  POST /findings/{finding_id}/review
  POST /reports/{audit_id}/publish
  GET  /findings/{audit_id}/review-history
  GET  /audits/{audit_id}/diagnostics/full
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.schemas.audit import (
    FindingResponse,
    FindingReviewRequest,
    FindingReviewResponse,
    FullDiagnosticsResponse,
    PublishReportResponse,
    FindingExplanationResponse,
)
from backend.app.schemas.remediation import (
    RemediationPlanResponse,
    RemediationPlanUpdateRequest,
)
from backend.app.services.audit_service import audit_service
from backend.app.services.finding_review_service import finding_review_service
from backend.app.services.finding_explanation_service import finding_explanation_service
from backend.app.services.remediation_service import remediation_service

router = APIRouter(tags=["hitl"])


# ─────────────────────────────── Feature 1: HITL ─────────────────────────────

@router.post("/findings/{finding_id}/review", response_model=FindingReviewResponse)
def review_finding(
    finding_id: str,
    payload: FindingReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FindingReviewResponse:
    """Accept, reject, or modify a single HIGH-risk finding."""
    try:
        finding = finding_review_service.review_finding(
            db=db,
            user=current_user,
            finding_id=finding_id,
            action=payload.action,
            comment=payload.comment,
            modified_fields=payload.modified_fields,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return FindingReviewResponse(
        finding_id=finding.id,
        review_status=finding.review_status,
        reviewed_by=finding.reviewed_by or current_user.id,
        reviewed_at=finding.reviewed_at,
        previous_state=finding.original_finding_snapshot,
    )


@router.get("/findings/{finding_id}/explanation", response_model=FindingExplanationResponse)
async def get_finding_explanation(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FindingExplanationResponse:
    """Retrieve or generate a natural language explanation of why a finding was flagged."""
    try:
        explanation = await finding_explanation_service.get_explanation(
            db=db,
            user=current_user,
            finding_id=finding_id,
        )
        return FindingExplanationResponse(**explanation)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/reports/{audit_id}/publish", response_model=PublishReportResponse)
def publish_report(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishReportResponse:
    """Publish a report after all HIGH-risk findings are reviewed."""
    try:
        result = finding_review_service.publish_report(
            db=db,
            user=current_user,
            audit_id=audit_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PublishReportResponse(**result)


@router.get("/findings/{audit_id}/review-history", response_model=list[FindingResponse])
def get_review_history(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FindingResponse]:
    """Return the immutable review audit trail for an audit's findings."""
    try:
        findings = finding_review_service.get_review_history(
            db=db,
            user=current_user,
            audit_id=audit_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [FindingResponse.model_validate(f) for f in findings]


# ─────────────────────────── Feature 2: Full Diagnostics ─────────────────────

@router.get("/audits/{audit_id}/diagnostics/full", response_model=FullDiagnosticsResponse)
def get_full_diagnostics(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FullDiagnosticsResponse:
    """
    Return extended diagnostic data including raw prompts, LLM responses,
    per-attempt retry log, and context chunk preview.
    """
    try:
        diagnostic = audit_service.get_full_diagnostics(
            db=db,
            user=current_user,
            audit_id=audit_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FullDiagnosticsResponse.model_validate(diagnostic)


# ─────────────────────────── Feature 2.2: Remediation Plans ──────────────────

@router.get("/findings/{finding_id}/remediation-plan", response_model=RemediationPlanResponse)
async def get_remediation_plan(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RemediationPlanResponse:
    """Get the remediation plan for a finding. Auto-generates if missing."""
    try:
        plan = await remediation_service.get_remediation_plan(
            db=db,
            user=current_user,
            finding_id=finding_id,
        )
        if plan is None:
            # Auto-generate if missing to provide a smooth user experience
            plan = await remediation_service.generate_remediation_plan(
                db=db,
                user=current_user,
                finding_id=finding_id,
            )
        return plan
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/findings/{finding_id}/remediation-plan", response_model=RemediationPlanResponse)
async def generate_remediation_plan(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RemediationPlanResponse:
    """Force generate a new remediation plan using AI."""
    try:
        plan = await remediation_service.generate_remediation_plan(
            db=db,
            user=current_user,
            finding_id=finding_id,
        )
        return plan
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/findings/{finding_id}/remediation-plan", response_model=RemediationPlanResponse)
async def update_remediation_plan(
    finding_id: str,
    payload: RemediationPlanUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RemediationPlanResponse:
    """Update or approve the remediation plan (Admin/Reviewer only)."""
    try:
        plan = await remediation_service.update_remediation_plan(
            db=db,
            user=current_user,
            finding_id=finding_id,
            payload=payload,
        )
        return plan
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

