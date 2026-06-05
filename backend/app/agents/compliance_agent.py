from __future__ import annotations

from dataclasses import dataclass
from time import sleep, time
from typing import Any

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.rag.prompts.compliance_analysis import SYSTEM_PROMPT, build_compliance_prompt
from backend.app.rag.retrieval.bm25_retriever import tokenize
from backend.app.rag.retrieval.types import RetrievalResult
from backend.app.rag.scoring.confidence import finding_confidence
from backend.app.services.llm_service import is_retryable_llm_error, llm_service

_KNOWN_SEVERITIES: frozenset[str] = frozenset({"LOW", "MEDIUM", "HIGH"})
_KNOWN_FINDING_TYPES: frozenset[str] = frozenset(
    {"missing_clause", "contradiction", "weak_clause", "risk"},
)
_NEGATION_TERMS: frozenset[str] = frozenset(
    {"not", "never", "no", "without", "optional", "may", "unless", "except"},
)
_OBLIGATION_TERMS: frozenset[str] = frozenset(
    {"must", "shall", "required", "requires", "mandatory", "ensure", "maintain"},
)

logger = get_logger(__name__)


class ComplianceAnalysisFailed(RuntimeError):
    pass


@dataclass
class FindingDraft:
    violated_rule: str
    finding_type: str
    severity: str
    risk_level: str
    confidence_score: float
    explanation: str
    recommendation: str
    rule_result: RetrievalResult
    evidence_text: str
    citation_source: str
    matched_uploaded_text: str
    matched_rule_text: str
    overlap_score: float
    matched_document_chunk: dict | None = None


@dataclass
class ComplianceAnalysis:
    compliance_score: float
    summary: str
    findings: list[FindingDraft]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class AnalysisAttemptProfile:
    rule_candidate_limit: int
    chunk_limit: int
    max_tokens: int
    max_context_chars: int
    text_char_limit: int


class ComplianceAgent:
    def evaluate(
        self,
        *,
        document_text: str,
        document_chunks: list[dict],
        rule_results: list[RetrievalResult],
        audit_id: str | None = None,
        document_id: str | None = None,
        domain: str | None = None,
    ) -> list[FindingDraft]:
        return self.evaluate_analysis(
            document_text=document_text,
            document_chunks=document_chunks,
            rule_results=rule_results,
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
        ).findings

    def evaluate_analysis(
        self,
        *,
        document_text: str,
        document_chunks: list[dict],
        rule_results: list[RetrievalResult],
        audit_id: str | None = None,
        document_id: str | None = None,
        domain: str | None = None,
    ) -> ComplianceAnalysis:
        started = time()
        if not rule_results:
            payload = {
                "compliance_score": 0.0,
                "summary": "No compliance rules were retrieved for this audit.",
                "findings": [],
                "metadata": {
                    "domain": domain or "",
                    "retrieved_rules": 0,
                    "analyzed_chunks": 0,
                    "llm_status": "skipped",
                },
            }
            log_pipeline_stage(
                logger,
                "AGENT_ANALYSIS",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                status="skipped",
                reason="no_retrieved_rules",
            )
            return ComplianceAnalysis(
                compliance_score=0.0,
                summary=str(payload["summary"]),
                findings=[],
                raw_payload=payload,
            )

        raw_payload: dict[str, Any] | None = None
        selected_chunks: list[dict[str, Any]] = []
        selected_rules: list[RetrievalResult] = []
        last_exc: Exception | None = None
        completed_attempt = 0
        profiles = self._analysis_attempt_profiles()

        for attempt, profile in enumerate(profiles, start=1):
            selected_rules = self._select_rule_results(
                rule_results=rule_results,
                domain=domain,
                candidate_limit=profile.rule_candidate_limit,
            )
            selected_chunks = self._select_document_chunks(
                document_text=document_text,
                document_chunks=document_chunks,
                rule_results=selected_rules,
                max_chunks=profile.chunk_limit,
                text_char_limit=profile.text_char_limit,
            )
            rule_context = self._build_rule_context(
                rule_results=selected_rules,
                document_chunks=document_chunks,
                max_rules=settings.llm_max_rules,
                text_char_limit=profile.text_char_limit,
            )
            prompt = self._build_prompt_with_budget(
                domain=domain,
                document_chunks=selected_chunks,
                rule_context=rule_context,
                max_context_chars=profile.max_context_chars,
            )
            try:
                raw_payload = llm_service.generate_json(
                    system=SYSTEM_PROMPT,
                    user=prompt,
                    max_tokens=profile.max_tokens,
                    attempt=attempt,
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    metadata={
                        "rule_candidate_limit": profile.rule_candidate_limit,
                        "selected_rules": len(selected_rules),
                        "selected_chunks": len(selected_chunks),
                        "max_context_chars": profile.max_context_chars,
                    },
                )
                completed_attempt = attempt
                break
            except Exception as exc:
                last_exc = exc
                retryable = is_retryable_llm_error(exc)
                log_pipeline_stage(
                    logger,
                    "LLM_RETRY",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=started,
                    status="scheduled" if attempt < len(profiles) else "exhausted",
                    attempt=attempt,
                    retryable=retryable,
                    next_max_tokens=profiles[attempt].max_tokens if attempt < len(profiles) else None,
                    next_rule_candidate_limit=profiles[attempt].rule_candidate_limit
                    if attempt < len(profiles)
                    else None,
                    error=str(exc),
                )
                if attempt < len(profiles):
                    sleep(min(1.5, 0.4 * attempt))

        if raw_payload is None:
            completed_attempt = len(profiles)
            log_pipeline_stage(
                logger,
                "LLM_FINALIZATION",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                status="failed",
                attempts=completed_attempt,
                findings_count=0,
                error=str(last_exc or ""),
            )
            raise ComplianceAnalysisFailed(
                "LLM analysis failed after retries; no findings were generated and report finalization was stopped. "
                f"Last error: {last_exc or 'unknown'}"
            ) from last_exc

        findings = self._findings_from_payload(
            payload=raw_payload,
            document_chunks=document_chunks,
            rule_results=selected_rules or rule_results,
        )
        compliance_score = self._coerce_score(
            raw_payload.get("compliance_score"),
            default=max(0.0, 1.0 - (len(findings) / max(len(selected_rules or rule_results), 1))),
        )
        summary = str(raw_payload.get("summary") or self._default_summary(findings))
        metadata = self._normalize_metadata(
            payload=raw_payload,
            domain=domain,
            retrieved_rules=len(selected_rules or rule_results),
            analyzed_chunks=len(selected_chunks),
            attempts=completed_attempt,
        )
        normalized_payload = {
            "compliance_score": compliance_score,
            "summary": summary,
            "findings": self._structured_findings(findings),
            "metadata": metadata,
        }
        if raw_payload.get("status"):
            normalized_payload["status"] = str(raw_payload.get("status"))
        log_pipeline_stage(
            logger,
            "AGENT_ANALYSIS",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="completed",
            rule_count=len(selected_rules or rule_results),
            chunk_count=len(selected_chunks),
            finding_count=len(findings),
            compliance_score=compliance_score,
            llm_status=normalized_payload.get("status", "generated"),
            attempts=completed_attempt,
        )
        return ComplianceAnalysis(
            compliance_score=compliance_score,
            summary=summary,
            findings=findings,
            raw_payload=normalized_payload,
        )

    def _build_rule_context(
        self,
        *,
        rule_results: list[RetrievalResult],
        document_chunks: list[dict],
        max_rules: int,
        text_char_limit: int,
    ) -> list[dict[str, Any]]:
        context = []
        for result in rule_results[: max(1, max_rules)]:
            diagnostics = self._rule_diagnostics(rule_text=result.text, document_chunks=document_chunks)
            payload = result.payload or {}
            context.append(
                {
                    "chunk_id": result.chunk_id,
                    "point_id": result.point_id,
                    "score": round(float(result.score or 0.0), 4),
                    "citation": payload.get("citation_label") or payload.get("source") or result.chunk_id,
                    "domain": payload.get("domain"),
                    "section": payload.get("section_title") or payload.get("section"),
                    "source": payload.get("source"),
                    "text": self._trim_context_text(result.text, text_char_limit),
                    **diagnostics,
                },
            )
        return context

    def _rule_diagnostics(self, *, rule_text: str, document_chunks: list[dict]) -> dict[str, Any]:
        rule_terms = self._important_terms(rule_text)
        document_terms: set[str] = set()
        for chunk in document_chunks:
            document_terms.update(tokenize(str(chunk.get("text", ""))))
        overlap_score = len(rule_terms & document_terms) / max(len(rule_terms), 1)
        missing_terms = sorted(rule_terms - document_terms)[:20]

        rule_tokens = set(tokenize(rule_text))
        document_tokens = document_terms
        contradiction_signals = []
        if rule_tokens & _OBLIGATION_TERMS and document_tokens & _NEGATION_TERMS:
            contradiction_signals.append("rule_obligation_with_document_negation_or_optional_language")

        return {
            "coverage_score": round(overlap_score, 4),
            "missing_terms": missing_terms,
            "contradiction_signals": contradiction_signals,
        }

    def _select_document_chunks(
        self,
        *,
        document_text: str,
        document_chunks: list[dict],
        rule_results: list[RetrievalResult],
        max_chunks: int,
        text_char_limit: int,
    ) -> list[dict[str, Any]]:
        if not document_chunks:
            return [
                {
                    "chunk_id": "full_document_excerpt",
                    "section": "Full document excerpt",
                    "page_number": 1,
                    "text": self._trim_context_text(document_text, text_char_limit),
                },
            ]

        rule_terms: set[str] = set()
        for result in rule_results[: max(1, settings.llm_max_rules)]:
            rule_terms.update(self._important_terms(result.text))

        ranked = sorted(
            enumerate(document_chunks),
            key=lambda indexed_chunk: (
                len(rule_terms & set(tokenize(str(indexed_chunk[1].get("text", ""))))),
                -indexed_chunk[0],
            ),
            reverse=True,
        )
        selected: list[dict] = []
        seen_texts: set[str] = set()
        for _, chunk in ranked:
            key = self._normalized_context_key(str(chunk.get("text", "")))
            if key and key in seen_texts:
                continue
            if key:
                seen_texts.add(key)
            selected.append(chunk)
            if len(selected) >= max(1, max_chunks):
                break
        return [
            {
                "chunk_id": chunk.get("chunk_id"),
                "section": chunk.get("section_title") or chunk.get("section"),
                "page_number": chunk.get("page_number"),
                "citation_label": chunk.get("citation_label"),
                "text": self._trim_context_text(str(chunk.get("text", "")), text_char_limit),
            }
            for chunk in selected
        ]

    def _select_rule_results(
        self,
        *,
        rule_results: list[RetrievalResult],
        domain: str | None,
        candidate_limit: int,
    ) -> list[RetrievalResult]:
        selected: list[RetrievalResult] = []
        seen: set[str] = set()
        domain_lower = str(domain or "").strip().lower()
        ranked = sorted(
            rule_results[: max(candidate_limit, settings.llm_max_rules)],
            key=lambda result: self._rule_priority_score(result=result, domain=domain_lower),
            reverse=True,
        )
        for result in ranked:
            key = self._normalized_context_key(result.text)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            selected.append(result)
            if len(selected) >= max(1, settings.llm_max_rules):
                break
        return selected or rule_results[: max(1, min(settings.llm_max_rules, len(rule_results)))]

    @staticmethod
    def _build_prompt_with_budget(
        *,
        domain: str | None,
        document_chunks: list[dict[str, Any]],
        rule_context: list[dict[str, Any]],
        max_context_chars: int,
    ) -> str:
        budget = max(1400, min(int(max_context_chars or settings.max_context_chars), 3000))
        prompt_limit = 3760
        prompt = ""
        for _ in range(5):
            prompt = build_compliance_prompt(
                domain=domain,
                document_chunks=document_chunks,
                rule_context=rule_context,
                max_context_chars=budget,
            )
            if len(prompt) <= prompt_limit:
                return prompt
            budget = max(1400, int(budget * 0.72))
        return prompt

    @staticmethod
    def _rule_priority_score(*, result: RetrievalResult, domain: str) -> float:
        payload = result.payload or {}
        score = float(result.score or 0.0)
        result_domain = str(payload.get("domain") or "").strip().lower()
        if domain and result_domain == domain:
            score += 0.08
        if str(payload.get("source_type") or "").lower() == "compliance_rule":
            score += 0.02
        return score

    @staticmethod
    def _analysis_attempt_profiles() -> list[AnalysisAttemptProfile]:
        max_context = max(1400, min(settings.max_context_chars, 3000))
        max_tokens = max(1, min(settings.max_output_tokens, 700))
        profiles = [
            AnalysisAttemptProfile(
                rule_candidate_limit=5,
                chunk_limit=min(settings.llm_max_chunks, 5),
                max_tokens=max_tokens,
                max_context_chars=max_context,
                text_char_limit=900,
            ),
            AnalysisAttemptProfile(
                rule_candidate_limit=3,
                chunk_limit=min(settings.llm_max_chunks, 4),
                max_tokens=min(max_tokens, 650),
                max_context_chars=min(max_context, 2400),
                text_char_limit=700,
            ),
            AnalysisAttemptProfile(
                rule_candidate_limit=2,
                chunk_limit=min(settings.llm_max_chunks, 3),
                max_tokens=min(max_tokens, 600),
                max_context_chars=min(max_context, 1800),
                text_char_limit=550,
            ),
        ]
        return profiles[: max(1, min(settings.llm_retry_attempts, len(profiles)))]

    def _findings_from_payload(
        self,
        *,
        payload: dict[str, Any],
        document_chunks: list[dict],
        rule_results: list[RetrievalResult],
    ) -> list[FindingDraft]:
        raw_findings = payload.get("findings")
        if not isinstance(raw_findings, list):
            return []

        findings: list[FindingDraft] = []
        for item in raw_findings:
            if not isinstance(item, dict):
                continue
            violated_rule = str(item.get("violated_rule") or item.get("matched_rule_text") or "").strip()
            if not violated_rule:
                continue
            rule_result = self._match_rule(item=item, rule_results=rule_results)
            matched_chunk = self._match_chunk(item=item, document_chunks=document_chunks)
            rule_terms = self._important_terms(rule_result.text)
            chunk_text = str((matched_chunk or {}).get("text") or "")
            coverage_terms = set(tokenize(chunk_text)) if chunk_text else set()
            overlap = len(rule_terms & coverage_terms) / max(len(rule_terms), 1)

            severity = self._normalize_severity(item.get("severity"))
            finding_type = self._normalize_finding_type(item.get("finding_type"))
            llm_confidence = self._coerce_score(item.get("confidence_score"), default=0.0)
            heuristic_confidence = finding_confidence(
                retrieval_score=min(max(rule_result.score, 0.0), 1.0),
                evidence_score=1.0 if item.get("evidence") or item.get("matched_uploaded_text") else 0.65,
                overlap_score=1.0 - overlap,
            )
            confidence = round(max(llm_confidence, heuristic_confidence), 4)
            evidence_text = str(
                item.get("evidence")
                or item.get("matched_uploaded_text")
                or chunk_text
                or "The cited compliance rule is not sufficiently represented in the uploaded document."
            )[:2000]
            matched_uploaded_text = str(item.get("matched_uploaded_text") or chunk_text or evidence_text)[:2000]
            matched_rule_text = str(item.get("matched_rule_text") or rule_result.text)[:2000]
            citation = str(
                item.get("citation")
                or rule_result.payload.get("citation_label")
                or rule_result.payload.get("source")
                or rule_result.chunk_id
            )
            findings.append(
                FindingDraft(
                    violated_rule=violated_rule[:1000],
                    finding_type=finding_type,
                    severity=severity,
                    risk_level=severity,
                    confidence_score=confidence,
                    explanation=str(item.get("summary") or item.get("explanation") or evidence_text)[:2000],
                    recommendation=str(
                        item.get("recommendation")
                        or "Review the cited rule and update the relevant clause in the document."
                    )[:2000],
                    rule_result=rule_result,
                    evidence_text=evidence_text,
                    citation_source=citation,
                    matched_uploaded_text=matched_uploaded_text,
                    matched_rule_text=matched_rule_text,
                    overlap_score=overlap,
                    matched_document_chunk=matched_chunk,
                ),
            )
        return findings

    @staticmethod
    def _match_rule(*, item: dict[str, Any], rule_results: list[RetrievalResult]) -> RetrievalResult:
        citation = str(item.get("citation") or "").lower()
        matched_rule_text = str(item.get("matched_rule_text") or item.get("violated_rule") or "")
        matched_terms = set(tokenize(matched_rule_text))

        def score(result: RetrievalResult) -> float:
            payload = result.payload or {}
            payload_citation = str(payload.get("citation_label") or payload.get("source") or "").lower()
            citation_hit = 1.0 if citation and citation in payload_citation else 0.0
            term_overlap = len(matched_terms & set(tokenize(result.text))) / max(len(matched_terms), 1)
            return citation_hit + term_overlap + (0.05 * float(result.score or 0.0))

        return max(rule_results, key=score)

    @staticmethod
    def _match_chunk(*, item: dict[str, Any], document_chunks: list[dict]) -> dict | None:
        evidence = str(item.get("matched_uploaded_text") or item.get("evidence") or "")
        evidence_terms = set(tokenize(evidence))
        if not document_chunks:
            return None
        if not evidence_terms:
            return document_chunks[0]
        return max(
            document_chunks,
            key=lambda chunk: len(evidence_terms & set(tokenize(str(chunk.get("text", ""))))),
        )

    @staticmethod
    def _important_terms(text: str) -> set[str]:
        stop_words = {
            "the",
            "and",
            "or",
            "of",
            "to",
            "in",
            "for",
            "a",
            "an",
            "is",
            "are",
            "be",
            "by",
            "with",
            "as",
            "on",
            "this",
            "that",
            "shall",
            "must",
            "should",
        }
        return {token for token in tokenize(text) if len(token) > 3 and token not in stop_words}

    @staticmethod
    def _normalize_severity(value: object) -> str:
        normalized = str(value or "").strip().upper()
        return normalized if normalized in _KNOWN_SEVERITIES else "MEDIUM"

    @staticmethod
    def _normalize_finding_type(value: object) -> str:
        normalized = str(value or "").strip().lower()
        return normalized if normalized in _KNOWN_FINDING_TYPES else "missing_clause"

    @staticmethod
    def _coerce_score(value: object, *, default: float) -> float:
        if isinstance(value, bool):
            score = default
        elif isinstance(value, str):
            stripped = value.strip()
            try:
                parsed = float(stripped.removesuffix("%"))
            except ValueError:
                score = default
            else:
                score = parsed / 100 if stripped.endswith("%") or parsed > 1 else parsed
        else:
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                score = default
            else:
                score = parsed / 100 if parsed > 1 else parsed
        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def _default_summary(findings: list[FindingDraft]) -> str:
        if findings:
            return f"Audit identified {len(findings)} potential compliance finding(s)."
        return "Audit completed without evidence-backed violations in the retrieved rule context."

    @staticmethod
    def _structured_findings(findings: list[FindingDraft]) -> list[dict[str, Any]]:
        return [
            {
                "violated_rule": finding.violated_rule,
                "severity": finding.severity.lower(),
                "confidence_score": finding.confidence_score,
                "evidence": finding.evidence_text,
                "recommendation": finding.recommendation,
                "citation": finding.citation_source,
                "matched_section": finding.rule_result.payload.get("section_title")
                or finding.rule_result.payload.get("section")
                or finding.citation_source,
            }
            for finding in findings
        ]

    @staticmethod
    def _normalize_metadata(
        *,
        payload: dict[str, Any],
        domain: str | None,
        retrieved_rules: int,
        analyzed_chunks: int,
        attempts: int,
    ) -> dict[str, Any]:
        raw_metadata = payload.get("metadata")
        metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
        metadata.update(
            {
                "domain": str(metadata.get("domain") or domain or ""),
                "retrieved_rules": int(metadata.get("retrieved_rules") or retrieved_rules),
                "analyzed_chunks": int(metadata.get("analyzed_chunks") or analyzed_chunks),
                "retry_attempts": attempts,
                "llm_status": str(payload.get("status") or metadata.get("llm_status") or "generated"),
            },
        )
        return metadata

    @staticmethod
    def _normalized_context_key(text: str) -> str:
        tokens = tokenize(str(text or "").lower())
        if not tokens:
            return ""
        return " ".join(tokens[:120])

    @staticmethod
    def _trim_context_text(text: str, limit: int) -> str:
        normalized = " ".join(str(text or "").split()).strip()
        if len(normalized) <= limit:
            return normalized
        clipped = normalized[:limit].rstrip()
        sentence_end = max(clipped.rfind("."), clipped.rfind(";"))
        if sentence_end >= max(120, int(limit * 0.5)):
            return clipped[: sentence_end + 1].strip()
        return clipped


compliance_agent = ComplianceAgent()
