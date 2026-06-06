from __future__ import annotations

from datetime import datetime
import json
from time import time
from typing import Any, TypedDict

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from backend.app.agents.compliance_agent import ComplianceAnalysis, FindingDraft, compliance_agent
from backend.app.agents.document_agent import ProcessedDocument, document_agent
from backend.app.agents.evidence_agent import evidence_agent
from backend.app.agents.report_agent import report_agent
from backend.app.agents.retrieval_agent import RetrievalOutput, retrieval_agent
from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.db.models.audit import (
    AuditReport,
    AuditResult,
    AuditRun,
    ComplianceScoreDiagnostic,
    EvidenceLink,
    Finding,
    ReportRecord,
)
from backend.app.db.models.document import UploadedDocument
from backend.app.db.transactions import commit_or_rollback
from backend.app.services.audit_log_service import audit_log_service
from backend.app.storage.s3_client import s3_storage

logger = get_logger(__name__)


class AuditWorkflowState(TypedDict):
    document: dict[str, Any]
    processed: ProcessedDocument | None
    retrieval: RetrievalOutput | None
    retrieved_rules: list[Any]
    analysis: ComplianceAnalysis | None
    findings: list[FindingDraft]
    persisted_findings: list[Finding]
    report: dict[str, Any]
    status: str


class AuditWorkflow:
    def run(self, *, db: Session, audit_id: str) -> AuditRun:
        audit = db.scalar(select(AuditRun).where(AuditRun.id == audit_id))
        if audit is None:
            raise ValueError(f"Audit not found: {audit_id}")

        document = db.scalar(select(UploadedDocument).where(UploadedDocument.id == audit.document_id))
        if document is None:
            raise ValueError(f"Document not found: {audit.document_id}")

        try:
            if self._run_langgraph(db=db, audit=audit, document=document):
                db.refresh(audit)
                return audit
            return self._run_linear(db=db, audit=audit, document=document)
        except Exception as exc:
            db.rollback()
            self._mark_failed(db=db, audit_id=audit.id, document_id=document.id, error=str(exc))
            logger.exception("Audit workflow failed for audit %s", audit.id)
            refreshed = db.get(AuditRun, audit.id)
            if refreshed is None:
                raise
            return refreshed

    def _run_langgraph(self, *, db: Session, audit: AuditRun, document: UploadedDocument) -> bool:
        try:
            from langgraph.graph import END, StateGraph
        except Exception:
            logger.warning("LangGraph is not installed; falling back to linear audit workflow.")
            return False

        def extraction_node(state: AuditWorkflowState) -> AuditWorkflowState:
            processed = self._process_document(db=db, audit=audit, document=document)
            return self._merge_state(state, processed=processed, status="embedding")

        def retrieval_node(state: AuditWorkflowState) -> AuditWorkflowState:
            processed = self._require_processed(state)
            retrieval = self._retrieve_rules(db=db, audit=audit, document=document, processed=processed)
            return self._merge_state(
                state,
                retrieval=retrieval,
                retrieved_rules=retrieval.results,
                status="retrieving_rules",
            )

        def compliance_node(state: AuditWorkflowState) -> AuditWorkflowState:
            processed = self._require_processed(state)
            retrieval = self._require_retrieval(state)
            analysis = self._analyze_compliance(
                db=db,
                audit=audit,
                document=document,
                processed=processed,
                retrieval=retrieval,
            )
            return self._merge_state(
                state,
                analysis=analysis,
                findings=analysis.findings,
                status="analyzing",
            )

        def report_node(state: AuditWorkflowState) -> AuditWorkflowState:
            retrieval = self._require_retrieval(state)
            analysis = self._require_analysis(state)
            self._assert_analysis_finalizable(analysis=analysis)
            self._set_status(db=db, audit=audit, document=document, status="generating_report")
            persisted_findings = self._persist_findings(
                db=db,
                audit=audit,
                document=document,
                drafts=analysis.findings,
            )
            report_payload = self._persist_report(
                db=db,
                audit=audit,
                retrieval=retrieval,
                analysis=analysis,
                drafts=analysis.findings,
            )
            self._complete_audit(
                db=db,
                audit=audit,
                document=document,
                persisted_findings=persisted_findings,
            )
            return self._merge_state(
                state,
                persisted_findings=persisted_findings,
                report=report_payload,
                status="completed",
            )

        graph = StateGraph(AuditWorkflowState)
        graph.add_node("extraction", extraction_node)
        graph.add_node("retrieval", retrieval_node)
        graph.add_node("compliance", compliance_node)
        graph.add_node("report", report_node)
        graph.set_entry_point("extraction")
        graph.add_edge("extraction", "retrieval")
        graph.add_edge("retrieval", "compliance")
        graph.add_edge("compliance", "report")
        graph.add_edge("report", END)
        graph.compile().invoke(self._initial_state(document=document))
        return True

    def _run_linear(self, *, db: Session, audit: AuditRun, document: UploadedDocument) -> AuditRun:
        state = self._initial_state(document=document)
        processed = self._process_document(db=db, audit=audit, document=document)
        state = self._merge_state(state, processed=processed, status="embedding")
        retrieval = self._retrieve_rules(db=db, audit=audit, document=document, processed=processed)
        state = self._merge_state(state, retrieval=retrieval, retrieved_rules=retrieval.results)
        analysis = self._analyze_compliance(
            db=db,
            audit=audit,
            document=document,
            processed=processed,
            retrieval=retrieval,
        )
        state = self._merge_state(state, analysis=analysis, findings=analysis.findings)
        self._assert_analysis_finalizable(analysis=analysis)
        self._set_status(db=db, audit=audit, document=document, status="generating_report")
        persisted_findings = self._persist_findings(
            db=db,
            audit=audit,
            document=document,
            drafts=analysis.findings,
        )
        report_payload = self._persist_report(
            db=db,
            audit=audit,
            retrieval=retrieval,
            analysis=analysis,
            drafts=analysis.findings,
        )
        self._merge_state(state, persisted_findings=persisted_findings, report=report_payload)
        self._complete_audit(
            db=db,
            audit=audit,
            document=document,
            persisted_findings=persisted_findings,
        )
        db.refresh(audit)
        return audit

    def _process_document(
        self,
        *,
        db: Session,
        audit: AuditRun,
        document: UploadedDocument,
    ) -> ProcessedDocument:
        audit.started_at = audit.started_at or datetime.utcnow()
        self._set_status(db=db, audit=audit, document=document, status="extracting")
        return document_agent.process_upload(db=db, document=document, audit_id=audit.id)

    def _retrieve_rules(
        self,
        *,
        db: Session,
        audit: AuditRun,
        document: UploadedDocument,
        processed: ProcessedDocument,
    ) -> RetrievalOutput:
        self._set_status(db=db, audit=audit, document=document, status="retrieving_rules")
        retrieval = retrieval_agent.retrieve_rules(
            document_text=processed.full_text,
            domain=document.domain,
            rule_set_id=audit.rule_set_id,
            audit_id=audit.id,
            document_id=document.id,
        )
        if settings.enable_reranking:
            self._set_status(db=db, audit=audit, document=document, status="reranking")
        return retrieval

    def _analyze_compliance(
        self,
        *,
        db: Session,
        audit: AuditRun,
        document: UploadedDocument,
        processed: ProcessedDocument,
        retrieval: RetrievalOutput,
    ) -> ComplianceAnalysis:
        self._set_status(db=db, audit=audit, document=document, status="analyzing")
        return compliance_agent.evaluate_analysis(
            document_text=processed.full_text,
            document_chunks=processed.chunks,
            rule_results=retrieval.results,
            audit_id=audit.id,
            document_id=document.id,
            domain=document.domain,
        )

    def _persist_findings(
        self,
        *,
        db: Session,
        audit: AuditRun,
        document: UploadedDocument,
        drafts: list[FindingDraft],
    ) -> list[Finding]:
        started = time()
        persisted_findings = []
        for draft in drafts:
            finding = Finding(
                audit_id=audit.id,
                document_id=document.id,
                violated_rule=draft.violated_rule,
                finding_type=draft.finding_type,
                severity=draft.severity,
                risk_level=draft.risk_level,
                confidence_score=draft.confidence_score,
                confidence=draft.confidence_score,
                evidence_text=draft.evidence_text,
                citation_source=draft.citation_source,
                explanation=draft.explanation,
                recommendation=draft.recommendation,
            )
            db.add(finding)
            db.flush()
            persisted_findings.append(finding)

            finding_exists = db.scalar(select(Finding.id).where(Finding.id == finding.id)) is not None
            log_pipeline_stage(
                logger,
                "AUDIT_PERSISTENCE_DIAGNOSTIC",
                audit_id=audit.id,
                document_id=document.id,
                domain=document.domain,
                started_at=started,
                status="finding_flushed",
                AUDIT_ID=audit.id,
                FINDING_ID=finding.id,
                FINDING_PERSISTED=inspect(finding).persistent,
                FINDING_EXISTS_IN_DB=finding_exists,
                EVIDENCE_INSERT_START=False,
            )

        for draft, finding in zip(drafts, persisted_findings, strict=True):
            finding_exists = db.scalar(select(Finding.id).where(Finding.id == finding.id)) is not None
            log_pipeline_stage(
                logger,
                "AUDIT_PERSISTENCE_DIAGNOSTIC",
                audit_id=audit.id,
                document_id=document.id,
                domain=document.domain,
                started_at=started,
                status="evidence_insert_start",
                AUDIT_ID=audit.id,
                FINDING_ID=finding.id,
                FINDING_PERSISTED=inspect(finding).persistent,
                FINDING_EXISTS_IN_DB=finding_exists,
                EVIDENCE_INSERT_START=True,
            )
            if not finding_exists:
                raise RuntimeError(f"Finding was not persisted before evidence insert: {finding.id}")

            for evidence in evidence_agent.trace(finding=draft):
                db.add(
                    EvidenceLink(
                        finding_id=finding.id,
                        source_type=evidence.source_type,
                        qdrant_point_id=evidence.qdrant_point_id,
                        document_id=evidence.document_id or document.id,
                        page_number=evidence.page_number,
                        section_title=evidence.section_title,
                        citation_text=evidence.citation_text,
                        citation_label=evidence.citation_label,
                        confidence_score=evidence.confidence_score,
                ),
            )
        db.flush()
        log_pipeline_stage(
            logger,
            "REPORT_PERSIST",
            audit_id=audit.id,
            document_id=document.id,
            domain=document.domain,
            started_at=started,
            status="findings_flushed",
            table="findings",
            row_count=len(persisted_findings),
        )
        return persisted_findings

    def _persist_report(
        self,
        *,
        db: Session,
        audit: AuditRun,
        retrieval: RetrievalOutput,
        analysis: ComplianceAnalysis,
        drafts: list[FindingDraft],
    ) -> dict[str, Any]:
        started = time()
        try:
            report = report_agent.generate(
                findings=drafts,
                context_ready=retrieval.has_enough_context,
                rule_count=len(retrieval.results),
                analysis=analysis,
            )
        except Exception as exc:
            log_pipeline_stage(
                logger,
                "REPORT_GENERATION",
                audit_id=audit.id,
                document_id=audit.document_id,
                domain=self._document_domain(db=db, document_id=audit.document_id),
                started_at=started,
                status="failed",
                error=str(exc),
            )
            raise
        report_uri = None
        markdown_uri = None
        payload = dict(report.payload)
        score_diagnostics = self._score_diagnostics(
            retrieval=retrieval,
            analysis=analysis,
            drafts=drafts,
            payload=payload,
        )
        payload["score_diagnostics"] = score_diagnostics

        s3_started = time()
        try:
            base_key = f"{settings.s3_report_prefix.strip('/')}/{audit.user_id}/{audit.id}"
            markdown_upload = s3_storage.upload_bytes(
                bucket=settings.report_bucket,
                key=f"{base_key}/audit-report.md",
                content=self._markdown_report(payload).encode("utf-8"),
                content_type="text/markdown",
                metadata={"audit-id": audit.id, "document-id": audit.document_id},
            )
            markdown_uri = markdown_upload.uri
            payload["markdown_s3_uri"] = markdown_uri
            uploaded = s3_storage.upload_bytes(
                bucket=settings.report_bucket,
                key=f"{base_key}/audit-report.json",
                content=json.dumps(payload, indent=2, default=str).encode("utf-8"),
                content_type="application/json",
                metadata={"audit-id": audit.id, "document-id": audit.document_id},
            )
            report_uri = uploaded.uri
            log_pipeline_stage(
                logger,
                "S3_UPLOAD",
                audit_id=audit.id,
                document_id=audit.document_id,
                domain=self._document_domain(db=db, document_id=audit.document_id),
                started_at=s3_started,
                status="completed",
                json_uri=report_uri,
                markdown_uri=markdown_uri,
            )
        except Exception as exc:
            log_pipeline_stage(
                logger,
                "S3_UPLOAD",
                audit_id=audit.id,
                document_id=audit.document_id,
                domain=self._document_domain(db=db, document_id=audit.document_id),
                started_at=s3_started,
                status="failed",
                error=str(exc),
            )
            logger.warning("S3 report upload failed for audit %s", audit.id, exc_info=True)

        db_started = time()
        audit_result = AuditResult(
            document_id=audit.document_id,
            overall_risk=self._overall_risk_from_drafts(drafts),
            confidence_score=self._average_confidence_from_drafts(drafts),
            summary=report.summary,
        )
        db.add(audit_result)
        db.flush()
        audit_report = AuditReport(
            audit_id=audit.id,
            summary=report.summary,
            report_payload=payload,
            report_json_s3_uri=report_uri,
        )
        db.add(audit_report)
        db.flush()
        db.add(
            ComplianceScoreDiagnostic(
                audit_id=audit.id,
                report_id=audit_report.id,
                rules_evaluated=score_diagnostics["rules_evaluated"],
                rules_matched=score_diagnostics["rules_matched"],
                rules_failed=score_diagnostics["rules_failed"],
                match_confidence=score_diagnostics["match_confidence"],
                score_reasoning=score_diagnostics["score_reasoning"],
                diagnostics_payload=score_diagnostics,
            ),
        )
        db.add(
            ReportRecord(
                id=audit_report.id,
                audit_result_id=audit_result.id,
                report_path=report_uri,
                generated_at=audit_report.created_at,
                audit_id=audit.id,
                summary=report.summary,
                report_payload=payload,
                report_json_s3_uri=report_uri,
                created_at=audit_report.created_at,
            ),
        )
        commit_or_rollback(db)
        log_pipeline_stage(
            logger,
            "REPORT_PERSIST",
            audit_id=audit.id,
            document_id=audit.document_id,
            domain=self._document_domain(db=db, document_id=audit.document_id),
            started_at=db_started,
            status="completed",
            transaction_order="findings,audit_results,audit_reports,reports,commit",
            finding_count=len(drafts),
            audit_result_id=audit_result.id,
            report_id=audit_report.id,
            report_json_s3_uri=report_uri,
            raw_score=payload.get("compliance_score"),
            api_score=payload.get("compliance_score"),
            diagnostics_score=score_diagnostics.get("compliance_score"),
        )
        log_pipeline_stage(
            logger,
            "REPORT_GENERATION",
            audit_id=audit.id,
            document_id=audit.document_id,
            domain=self._document_domain(db=db, document_id=audit.document_id),
            started_at=started,
            status="completed",
            finding_count=len(drafts),
            compliance_score=payload.get("compliance_score"),
        )
        log_pipeline_stage(
            logger,
            "DB_WRITE",
            audit_id=audit.id,
            document_id=audit.document_id,
            domain=self._document_domain(db=db, document_id=audit.document_id),
            started_at=db_started,
            status="completed",
            table="audit_results,audit_reports,reports",
            audit_result_id=audit_result.id,
            report_id=audit_report.id,
        )
        return payload

    def _complete_audit(
        self,
        *,
        db: Session,
        audit: AuditRun,
        document: UploadedDocument,
        persisted_findings: list[Finding],
    ) -> None:
        started = time()
        audit.status = "completed"
        document.upload_status = "completed"
        document.status = "completed"
        document.processing_stage = "completed"
        audit.completed_at = datetime.utcnow()
        audit.confidence_score = self._average_confidence(persisted_findings)
        audit.overall_risk = self._overall_risk(persisted_findings)
        commit_or_rollback(db)
        log_pipeline_stage(
            logger,
            "DB_WRITE",
            audit_id=audit.id,
            document_id=document.id,
            domain=document.domain,
            started_at=started,
            status="completed",
            table="audit_runs,uploaded_documents",
        )
        audit_log_service.log(
            db=db,
            action="audit.completed",
            user=None,
            entity_type="audit_run",
            entity_id=audit.id,
            metadata={
                "document_id": document.id,
                "finding_count": len(persisted_findings),
                "overall_risk": audit.overall_risk,
            },
        )

    def _mark_failed(self, *, db: Session, audit_id: str, document_id: str, error: str) -> None:
        started = time()
        audit = db.get(AuditRun, audit_id)
        document = db.get(UploadedDocument, document_id)
        if audit is not None:
            audit.status = "failed"
            audit.error_message = error
            audit.completed_at = datetime.utcnow()
        if document is not None:
            document.upload_status = "failed"
            document.status = "failed"
            document.processing_stage = "failed"
        commit_or_rollback(db)
        log_pipeline_stage(
            logger,
            "DB_WRITE",
            audit_id=audit_id,
            document_id=document_id,
            domain=document.domain if document is not None else None,
            started_at=started,
            status="failed",
            table="audit_runs,uploaded_documents",
            error=error,
        )
        audit_log_service.log(
            db=db,
            action="audit.failed",
            user=None,
            entity_type="audit_run",
            entity_id=audit_id,
            metadata={"document_id": document_id, "error": error},
        )

    def _set_status(
        self,
        *,
        db: Session,
        audit: AuditRun,
        document: UploadedDocument,
        status: str,
    ) -> None:
        started = time()
        audit.status = status
        document.upload_status = status
        document.status = status
        document.processing_stage = status
        commit_or_rollback(db)
        log_pipeline_stage(
            logger,
            "DB_WRITE",
            audit_id=audit.id,
            document_id=document.id,
            domain=document.domain,
            started_at=started,
            status=status,
            table="audit_runs,uploaded_documents",
        )

    def _set_status_by_id(
        self,
        *,
        db: Session,
        audit_id: str,
        document_id: str,
        status: str,
    ) -> None:
        audit = db.get(AuditRun, audit_id)
        document = db.get(UploadedDocument, document_id)
        if audit is None or document is None:
            raise ValueError("Audit or document disappeared during workflow status update.")
        self._set_status(db=db, audit=audit, document=document, status=status)

    @staticmethod
    def _initial_state(*, document: UploadedDocument) -> AuditWorkflowState:
        return {
            "document": {
                "id": document.id,
                "domain": document.domain,
                "filename": document.filename,
            },
            "processed": None,
            "retrieval": None,
            "retrieved_rules": [],
            "analysis": None,
            "findings": [],
            "persisted_findings": [],
            "report": {},
            "status": "uploaded",
        }

    @staticmethod
    def _merge_state(state: AuditWorkflowState, **updates: Any) -> AuditWorkflowState:
        merged: AuditWorkflowState = {
            "document": state.get("document", {}),
            "processed": state.get("processed"),
            "retrieval": state.get("retrieval"),
            "retrieved_rules": state.get("retrieved_rules", []),
            "analysis": state.get("analysis"),
            "findings": state.get("findings", []),
            "persisted_findings": state.get("persisted_findings", []),
            "report": state.get("report", {}),
            "status": state.get("status", ""),
        }
        merged.update(updates)
        return merged

    @staticmethod
    def _require_processed(state: AuditWorkflowState) -> ProcessedDocument:
        processed = state.get("processed")
        if processed is None:
            raise RuntimeError("Workflow state is missing 'processed' after extraction.")
        return processed

    @staticmethod
    def _require_retrieval(state: AuditWorkflowState) -> RetrievalOutput:
        retrieval = state.get("retrieval")
        if retrieval is None:
            raise RuntimeError("Workflow state is missing 'retrieval' after rule retrieval.")
        return retrieval

    @staticmethod
    def _require_analysis(state: AuditWorkflowState) -> ComplianceAnalysis:
        analysis = state.get("analysis")
        if analysis is None:
            raise RuntimeError("Workflow state is missing 'analysis' after compliance analysis.")
        return analysis

    @staticmethod
    def _assert_analysis_finalizable(*, analysis: ComplianceAnalysis) -> None:
        raw_payload = analysis.raw_payload if isinstance(analysis.raw_payload, dict) else {}
        metadata = raw_payload.get("metadata") if isinstance(raw_payload.get("metadata"), dict) else {}
        llm_status = str(raw_payload.get("status") or metadata.get("llm_status") or "").strip().lower()
        has_llm_error = bool(metadata.get("llm_error"))
        if not analysis.findings and (
            llm_status in {"fallback_generated", "llm_failed", "failed"} or has_llm_error
        ):
            raise RuntimeError(
                "LLM failed with zero findings; report finalization was blocked to avoid a masked compliant report."
            )

    @staticmethod
    def _average_confidence(findings: list[Finding]) -> float:
        if not findings:
            return 1.0
        return round(sum(finding.confidence_score for finding in findings) / len(findings), 4)

    @staticmethod
    def _average_confidence_from_drafts(findings: list[FindingDraft]) -> float:
        if not findings:
            return 1.0
        return round(sum(finding.confidence_score for finding in findings) / len(findings), 4)

    @staticmethod
    def _overall_risk(findings: list[Finding]) -> str:
        risks = {finding.risk_level for finding in findings}
        if "HIGH" in risks:
            return "HIGH"
        if "MEDIUM" in risks:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _overall_risk_from_drafts(findings: list[FindingDraft]) -> str:
        risks = {finding.risk_level for finding in findings}
        if "HIGH" in risks:
            return "HIGH"
        if "MEDIUM" in risks:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _markdown_report(payload: dict[str, Any]) -> str:
        lines = [
            "# AI Audit Report",
            "",
            f"Compliance score: {payload.get('compliance_score', 'n/a')}",
            f"Total violations: {payload.get('total_violations', payload.get('finding_count', 0))}",
            "",
            "## Summary",
            str(payload.get("summary") or ""),
            "",
            "## Findings",
        ]
        findings = payload.get("findings")
        if not isinstance(findings, list) or not findings:
            lines.append("No evidence-backed findings were generated.")
        else:
            for index, finding in enumerate(findings, start=1):
                if not isinstance(finding, dict):
                    continue
                lines.extend(
                    [
                        "",
                        f"### {index}. {finding.get('violated_rule', 'Finding')}",
                        f"- Severity: {finding.get('severity', 'n/a')}",
                        f"- Confidence: {finding.get('confidence_score', 'n/a')}",
                        f"- Citation: {finding.get('citation', 'n/a')}",
                        f"- Evidence: {finding.get('evidence', 'n/a')}",
                        f"- Recommendation: {finding.get('recommendation', 'n/a')}",
                    ],
                )
        return "\n".join(lines)

    @staticmethod
    def _score_diagnostics(
        *,
        retrieval: RetrievalOutput,
        analysis: ComplianceAnalysis,
        drafts: list[FindingDraft],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        scores = [float(result.score or 0.0) for result in retrieval.results]
        threshold = float(settings.semantic_similarity_threshold or 0.0)
        rules_evaluated = len(retrieval.results)
        rules_matched = sum(1 for score in scores if score >= threshold)
        rules_failed = len(drafts)
        match_confidence = round(sum(scores) / len(scores), 4) if scores else None
        compliance_score = payload.get("compliance_score", analysis.compliance_score)
        if not retrieval.results:
            reasoning = "Score is low because no compliance rules were retrieved for the selected domain/rule set."
        elif rules_failed:
            reasoning = (
                f"Score reflects {rules_failed} failed rule(s) from {rules_evaluated} evaluated rule candidate(s)."
            )
        else:
            reasoning = (
                f"Score reflects {rules_matched} matched rule candidate(s) and no persisted findings."
            )
        return {
            "rules_evaluated": rules_evaluated,
            "rules_matched": rules_matched,
            "rules_failed": rules_failed,
            "match_confidence": match_confidence,
            "compliance_score": compliance_score,
            "score_reasoning": reasoning,
            "context_ready": retrieval.has_enough_context,
            "retrieval_query_chars": len(retrieval.query or ""),
            "rule_matches": [
                {
                    "chunk_id": result.chunk_id,
                    "point_id": result.point_id,
                    "score": round(float(result.score or 0.0), 4),
                    "domain": (result.payload or {}).get("domain"),
                    "citation": (result.payload or {}).get("citation_label") or (result.payload or {}).get("source"),
                }
                for result in retrieval.results
            ],
            "failed_rules": [
                {
                    "violated_rule": draft.violated_rule,
                    "severity": draft.severity,
                    "confidence_score": draft.confidence_score,
                    "match_confidence": round(float(draft.rule_result.score or 0.0), 4),
                    "overlap_score": round(float(draft.overlap_score or 0.0), 4),
                    "reason": draft.explanation,
                }
                for draft in drafts
            ],
        }

    @staticmethod
    def _document_domain(*, db: Session, document_id: str) -> str | None:
        document = db.get(UploadedDocument, document_id)
        return document.domain if document is not None else None


audit_workflow = AuditWorkflow()
