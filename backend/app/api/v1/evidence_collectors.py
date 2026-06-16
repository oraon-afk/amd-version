"""
Feature 3: Agentic Evidence Collection – API router.

Endpoints:
  GET    /evidence-collectors
  POST   /evidence-collectors
  DELETE /evidence-collectors/{id}
  POST   /evidence-collectors/{id}/run
  GET    /evidence-collectors/{id}/results
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.collector import ExternalEvidence
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.services.collector_service import collector_service

router = APIRouter(prefix="/evidence-collectors", tags=["evidence-collectors"])


# ────────────────────── Pydantic Schemas ─────────────────────────────────────

class CreateCollectorRequest(BaseModel):
    name: str
    collector_type: str  # "http" | "sql" | "script"
    config: dict[str, Any]
    schedule: str | None = None
    target_domain: str | None = None
    document_id: str | None = None


class CollectorResponse(BaseModel):
    id: str
    user_id: str
    name: str
    collector_type: str
    config: dict[str, Any]
    schedule: str | None = None
    target_domain: str | None = None
    document_id: str | None = None
    is_active: bool
    last_run_at: Any = None
    last_run_status: str | None = None
    created_at: Any

    model_config = {"from_attributes": True}


class ExternalEvidenceResponse(BaseModel):
    id: str
    collector_id: str | None = None
    audit_id: str | None = None
    finding_id: str | None = None
    evidence_text: str | None = None
    citation_label: str | None = None
    confidence_score: float
    raw_payload: dict[str, Any] | None = None
    source_type: str
    collected_at: Any

    model_config = {"from_attributes": True}


class CollectorRunResult(BaseModel):
    run_id: str
    status: str
    collected_evidence: list[ExternalEvidenceResponse]


# ────────────────────── Routes ───────────────────────────────────────────────

@router.get("", response_model=list[CollectorResponse])
def list_collectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollectorResponse]:
    """Get all evidence collectors."""
    collectors = collector_service.list_collectors(db=db, user=current_user)
    return [CollectorResponse.model_validate(c) for c in collectors]


@router.post("", response_model=CollectorResponse, status_code=201)
def create_collector(
    payload: CreateCollectorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectorResponse:
    """Create a new evidence collector."""
    try:
        collector = collector_service.create_collector(
            db=db,
            user=current_user,
            name=payload.name,
            collector_type=payload.collector_type,
            config=payload.config,
            schedule=payload.schedule,
            target_domain=payload.target_domain,
            document_id=payload.document_id,
        )
        return CollectorResponse.model_validate(collector)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{collector_id}", status_code=204, response_class=Response)
def delete_collector(
    collector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an evidence collector."""
    try:
        collector_service.delete_collector(db=db, user=current_user, collector_id=collector_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{collector_id}/run", response_model=CollectorRunResult)
def run_collector(
    collector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectorRunResult:
    """Manually trigger an evidence collector execution."""
    try:
        evidence_list = collector_service.run_collector(
            db=db,
            user=current_user,
            collector_id=collector_id,
        )
        return CollectorRunResult(
            run_id=collector_id,
            status="success",
            collected_evidence=[ExternalEvidenceResponse.model_validate(e) for e in evidence_list],
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{collector_id}/results", response_model=list[ExternalEvidenceResponse])
def get_collector_results(
    collector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExternalEvidenceResponse]:
    """Retrieve evidence records collected by this collector."""
    # Enforce basic exists check and ownership
    # For now, select all evidence collected by this collector
    evidence_list = db.scalars(
        select(ExternalEvidence)
        .where(ExternalEvidence.collector_id == collector_id)
        .order_by(ExternalEvidence.collected_at.desc())
    ).all()
    return [ExternalEvidenceResponse.model_validate(e) for e in evidence_list]
