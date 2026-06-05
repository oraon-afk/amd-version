from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import sleep, time
from typing import Any
from uuid import uuid4

from json_repair import repair_json

from backend.app.core.config import PROJECT_ROOT, settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.services.llm_providers import LLMGenerationResult, ProviderRouter

logger = get_logger(__name__)

_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
_FENCED_JSON_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_REQUIRED_RESPONSE_KEYS = frozenset({"summary", "findings", "compliance_score"})


class LLMResponseValidationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        missing_keys: list[str] | None = None,
        invalid_keys: list[str] | None = None,
        present_keys: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.missing_keys = missing_keys or []
        self.invalid_keys = invalid_keys or []
        self.present_keys = present_keys or []


@dataclass(frozen=True)
class LLMRequestMetadata:
    estimated_tokens: int
    max_tokens: int
    prompt_chars: int
    system_chars: int
    user_chars: int


class LLMService:
    def __init__(self) -> None:
        self._provider_router = ProviderRouter()

    def warm(self) -> bool:
        queue = self._provider_router.retry_queue()
        if not queue:
            raise RuntimeError("No configured LLM provider is available.")
        selected = queue[0]
        logger.info("LLM Provider: %s", _provider_display_name(selected.provider))
        logger.info("Model: %s", selected.model)
        logger.info("Status: Active")
        logger.info(
            "LLM retry queue: %s",
            [
                {"provider": item.provider, "model": item.model, "stage": item.stage}
                for item in queue
            ],
        )
        return self._provider_router.warm()

    def validate_model_availability(self) -> LLMGenerationResult:
        return self._provider_router.validate_model_availability()

    def generate_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
        attempt: int = 1,
        audit_id: str | None = None,
        document_id: str | None = None,
        domain: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time()
        effective_max_tokens = max(
            1,
            min(int(max_tokens or settings.max_output_tokens), int(settings.llm_max_completion_tokens or 1)),
        )
        retry_queue = self._provider_router.retry_queue()
        if not retry_queue:
            raise RuntimeError("No configured LLM provider is available.")
        request_metadata = LLMRequestMetadata(
            estimated_tokens=estimate_tokens(system, user),
            max_tokens=effective_max_tokens,
            prompt_chars=len(system) + len(user),
            system_chars=len(system),
            user_chars=len(user),
        )
        log_pipeline_stage(
            logger,
            "TOKEN_ESTIMATE",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="completed",
            estimated_tokens=request_metadata.estimated_tokens,
            prompt_chars=request_metadata.prompt_chars,
            system_chars=request_metadata.system_chars,
            user_chars=request_metadata.user_chars,
            max_tokens=request_metadata.max_tokens,
            **(metadata or {}),
        )
        last_exc: Exception | None = None
        for provider_attempt_index, provider_attempt in enumerate(retry_queue, start=1):
            if provider_attempt_index > 1:
                log_pipeline_stage(
                    logger,
                    "FAILOVER_TRIGGERED",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=time(),
                    status="selected",
                    provider=provider_attempt.provider,
                    model=provider_attempt.model,
                    fallback_stage=provider_attempt.stage,
                    provider_attempt=provider_attempt_index,
                    analysis_attempt=attempt,
                    **(metadata or {}),
                )
                log_pipeline_stage(
                    logger,
                    "LLM_FALLBACK",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=time(),
                    status="selected",
                    provider=provider_attempt.provider,
                    model=provider_attempt.model,
                    fallback_stage=provider_attempt.stage,
                    provider_attempt=provider_attempt_index,
                    analysis_attempt=attempt,
                    **(metadata or {}),
                )
                log_pipeline_stage(
                    logger,
                    "FALLBACK_MODEL_USED",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=time(),
                    status="selected",
                    provider=provider_attempt.provider,
                    model=provider_attempt.model,
                    fallback_stage=provider_attempt.stage,
                    provider_attempt=provider_attempt_index,
                    analysis_attempt=attempt,
                    **(metadata or {}),
                )
            else:
                log_pipeline_stage(
                    logger,
                    "PRIMARY_MODEL_USED",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=time(),
                    status="selected",
                    provider=provider_attempt.provider,
                    model=provider_attempt.model,
                    fallback_stage=provider_attempt.stage,
                    provider_attempt=provider_attempt_index,
                    analysis_attempt=attempt,
                    **(metadata or {}),
                )
            log_pipeline_stage(
                logger,
                "LLM_REQUEST",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                status="started",
                provider=provider_attempt.provider,
                model=provider_attempt.model,
                attempt=attempt,
                provider_attempt=provider_attempt_index,
                fallback_stage=provider_attempt.stage,
                prompt_chars=request_metadata.prompt_chars,
                system_chars=request_metadata.system_chars,
                user_chars=request_metadata.user_chars,
                estimated_tokens=request_metadata.estimated_tokens,
                max_tokens=request_metadata.max_tokens,
                **(metadata or {}),
            )
            try:
                generation = self._provider_router.generate(
                    attempt=provider_attempt,
                    system=system,
                    user=user,
                    max_tokens=request_metadata.max_tokens,
                )
                allow_repair = settings.json_repair_enabled and provider_attempt_index == len(retry_queue)
                payload = parse_json_response(
                    generation.content,
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    repair_enabled=allow_repair,
                )
                log_pipeline_stage(
                    logger,
                    "LLM_REQUEST",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=started,
                    status="completed",
                    provider=provider_attempt.provider,
                    model=provider_attempt.model,
                    attempt=attempt,
                    provider_attempt=provider_attempt_index,
                    fallback_stage=provider_attempt.stage,
                    max_tokens=request_metadata.max_tokens,
                    json_repair_enabled=allow_repair,
                    prompt_tokens=generation.usage.get("prompt_tokens"),
                    completion_tokens=generation.usage.get("completion_tokens"),
                    total_tokens=generation.usage.get("total_tokens"),
                )
                return payload
            except Exception as exc:
                last_exc = exc
                retryable = is_retryable_llm_error(exc)
                has_next = provider_attempt_index < len(retry_queue)
                log_pipeline_stage(
                    logger,
                    "LLM_REQUEST",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=started,
                    status="failed",
                    provider=provider_attempt.provider,
                    model=provider_attempt.model,
                    attempt=attempt,
                    provider_attempt=provider_attempt_index,
                    fallback_stage=provider_attempt.stage,
                    max_tokens=request_metadata.max_tokens,
                    retryable=retryable,
                    error=str(exc),
                )
                logger.warning(
                    "llm.error provider=%s model=%s attempt=%s provider_attempt=%s max_tokens=%s retryable=%s detail=%s",
                    provider_attempt.provider,
                    provider_attempt.model,
                    attempt,
                    provider_attempt_index,
                    request_metadata.max_tokens,
                    retryable,
                    exc,
                )
                if has_next and retryable:
                    next_attempt = retry_queue[provider_attempt_index]
                    sleep_seconds = self._backoff_seconds(provider_attempt_index)
                    log_pipeline_stage(
                        logger,
                        "LLM_RETRY_QUEUE",
                        audit_id=audit_id,
                        document_id=document_id,
                        domain=domain,
                        started_at=time(),
                        status="scheduled",
                        from_provider=provider_attempt.provider,
                        from_model=provider_attempt.model,
                        next_provider=next_attempt.provider,
                        next_model=next_attempt.model,
                        next_stage=next_attempt.stage,
                        attempt=attempt,
                        provider_attempt=provider_attempt_index,
                        sleep_seconds=sleep_seconds,
                        error=str(exc),
                    )
                    sleep(sleep_seconds)
                    continue
                raise

        raise last_exc or RuntimeError("LLM request failed without an exception.")

    @staticmethod
    def _backoff_seconds(provider_attempt_index: int) -> float:
        base = max(0.1, float(settings.llm_retry_backoff_seconds or 1.0))
        return round(min(30.0, base * (2 ** max(provider_attempt_index - 1, 0))), 2)


def _provider_display_name(provider: str) -> str:
    return {
        "openrouter": "OpenRouter",
        "groq": "Groq",
        "gemini": "Gemini",
    }.get(provider, provider)


def estimate_tokens(*parts: str) -> int:
    text = " ".join(" ".join(str(part or "").split()) for part in parts).strip()
    if not text:
        return 0
    word_count = len(text.split())
    return max(word_count, math.ceil(len(text) / 4))


def parse_json_response(
    content: str,
    *,
    audit_id: str | None = None,
    document_id: str | None = None,
    domain: str | None = None,
    repair_enabled: bool | None = None,
) -> dict[str, Any]:
    started = time()
    cleaned = clean_json_response(content)
    allow_repair = settings.json_repair_enabled if repair_enabled is None else repair_enabled
    raw_output_path: str | None = None
    try:
        fast_payload = json.loads(cleaned)
    except json.JSONDecodeError:
        fast_payload = None
    else:
        if isinstance(fast_payload, dict):
            validate_json_payload(
                fast_payload,
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                output_chars=len(content or ""),
                cleaned_chars=len(cleaned),
                repaired_chars=len(cleaned),
                raw_content=content,
                cleaned_content=cleaned,
                repaired_content=cleaned,
            )
            log_pipeline_stage(
                logger,
                "JSON_PARSE",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                status="completed",
                keys=sorted(fast_payload.keys()),
                output_chars=len(content or ""),
                cleaned_chars=len(cleaned),
                repaired_chars=len(cleaned),
                repair_applied=False,
            )
            return fast_payload
    if not allow_repair:
        raw_output_path = save_failed_llm_output(
            content=content,
            cleaned_content=cleaned,
            repaired_content=None,
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            error="json_repair_disabled",
        )
        log_pipeline_stage(
            logger,
            "LLM_JSON_PARSE_FAILED",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="failed",
            error="json_repair_disabled",
            raw_output_path=raw_output_path,
            output_chars=len(content or ""),
            cleaned_chars=len(cleaned),
        )
        raise LLMResponseValidationError(
            "LLM JSON output could not be parsed.",
            invalid_keys=["json"],
            present_keys=[],
        )
    try:
        repaired = repair_json(cleaned)
    except Exception as exc:
        raw_output_path = save_failed_llm_output(
            content=content,
            cleaned_content=cleaned,
            repaired_content=None,
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            error=str(exc),
        )
        log_pipeline_stage(
            logger,
            "LLM_JSON_PARSE_FAILED",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="failed",
            error=str(exc),
            repair_error=True,
            raw_output_path=raw_output_path,
            output_chars=len(content or ""),
            cleaned_chars=len(cleaned),
        )
        raise
    if not isinstance(repaired, str):
        repaired = json.dumps(repaired, ensure_ascii=True)
    repaired = repaired.strip()
    if repaired != cleaned:
        raw_output_path = save_failed_llm_output(
            content=content,
            cleaned_content=cleaned,
            repaired_content=repaired,
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            error="json_repair_applied",
        )
        log_pipeline_stage(
            logger,
            "LLM_JSON_REPAIR_SUCCESS",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="completed",
            raw_output_path=raw_output_path,
            output_chars=len(content or ""),
            cleaned_chars=len(cleaned),
            repaired_chars=len(repaired),
        )
    try:
        payload = json.loads(repaired)
    except json.JSONDecodeError as exc:
        if raw_output_path is None:
            raw_output_path = save_failed_llm_output(
                content=content,
                cleaned_content=cleaned,
                repaired_content=repaired,
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                error=str(exc),
            )
        log_pipeline_stage(
            logger,
            "LLM_JSON_PARSE_FAILED",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="failed",
            error=str(exc),
            raw_output_path=raw_output_path,
            output_chars=len(content or ""),
            cleaned_chars=len(cleaned),
            repaired_chars=len(repaired),
        )
        raise
    if not isinstance(payload, dict):
        if raw_output_path is None:
            raw_output_path = save_failed_llm_output(
                content=content,
                cleaned_content=cleaned,
                repaired_content=repaired,
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                error="llm_json_not_object",
            )
        log_pipeline_stage(
            logger,
            "LLM_JSON_PARSE_FAILED",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="failed",
            error="llm_json_not_object",
            output_chars=len(content or ""),
            cleaned_chars=len(cleaned),
            repaired_chars=len(repaired),
        )
        raise LLMResponseValidationError("LLM JSON output must be an object.")
    validate_json_payload(
        payload,
        audit_id=audit_id,
        document_id=document_id,
        domain=domain,
        started_at=started,
        output_chars=len(content or ""),
        cleaned_chars=len(cleaned),
        repaired_chars=len(repaired),
        raw_output_path=raw_output_path,
        raw_content=content,
        cleaned_content=cleaned,
        repaired_content=repaired,
    )
    log_pipeline_stage(
        logger,
        "JSON_PARSE",
        audit_id=audit_id,
        document_id=document_id,
        domain=domain,
        started_at=started,
        status="completed",
        keys=sorted(payload.keys()),
        output_chars=len(content or ""),
        cleaned_chars=len(cleaned),
        repaired_chars=len(repaired),
    )
    return payload


def clean_json_response(content: str) -> str:
    text = str(content or "").strip()
    text = text.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
    text = _FENCED_JSON_RE.sub("", text).strip()
    if text.lower().startswith("json "):
        text = text[5:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    elif start >= 0:
        text = text[start:]
    text = _TRAILING_COMMA_RE.sub(r"\1", text)
    return text.strip()


def validate_json_payload(
    payload: dict[str, Any],
    *,
    audit_id: str | None,
    document_id: str | None,
    domain: str | None,
    started_at: float,
    output_chars: int,
    cleaned_chars: int,
    repaired_chars: int,
    raw_output_path: str | None = None,
    raw_content: str = "",
    cleaned_content: str = "",
    repaired_content: str = "",
) -> None:
    missing = sorted(key for key in _REQUIRED_RESPONSE_KEYS if key not in payload)
    invalid: list[str] = []
    if "summary" in payload and not str(payload.get("summary") or "").strip():
        invalid.append("summary")
    if "findings" in payload and not isinstance(payload.get("findings"), list):
        invalid.append("findings")
    if "compliance_score" in payload:
        try:
            score = float(payload.get("compliance_score"))
        except (TypeError, ValueError):
            invalid.append("compliance_score")
        else:
            if not math.isfinite(score):
                invalid.append("compliance_score")

    if missing or invalid:
        if raw_output_path is None:
            raw_output_path = save_failed_llm_output(
                content=raw_content,
                cleaned_content=cleaned_content,
                repaired_content=repaired_content or json.dumps(payload, ensure_ascii=True),
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                error="llm_json_validation_failed",
            )
        log_pipeline_stage(
            logger,
            "LLM_JSON_PARSE_FAILED",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started_at,
            status="failed",
            error="llm_json_validation_failed",
            missing_keys=missing,
            invalid_keys=invalid,
            keys=sorted(payload.keys()),
            raw_output_path=raw_output_path,
            output_chars=output_chars,
            cleaned_chars=cleaned_chars,
            repaired_chars=repaired_chars,
        )
        detail = []
        if missing:
            detail.append(f"missing_keys={','.join(missing)}")
        if invalid:
            detail.append(f"invalid_keys={','.join(invalid)}")
        raise LLMResponseValidationError(
            f"LLM JSON output failed validation ({'; '.join(detail)}).",
            missing_keys=missing,
            invalid_keys=invalid,
            present_keys=sorted(payload.keys()),
        )


def save_failed_llm_output(
    *,
    content: str,
    cleaned_content: str,
    repaired_content: str | None,
    audit_id: str | None,
    document_id: str | None,
    domain: str | None,
    error: str,
) -> str | None:
    started = time()
    try:
        root = Path(settings.storage_root)
        if not root.is_absolute():
            root = PROJECT_ROOT / root
        debug_dir = root / "debug" / "failed_llm"
        debug_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        audit_part = _safe_filename_part(audit_id or "no-audit")
        path = debug_dir / f"{stamp}_{audit_part}_{uuid4().hex}.json"
        payload = {
            "audit_id": audit_id,
            "document_id": document_id,
            "domain": domain,
            "error": error,
            "raw_output": str(content or ""),
            "cleaned_output": cleaned_content,
            "repaired_output": repaired_content,
        }
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("LLM_RAW_OUTPUT_SAVE_FAILED error=%s", exc)
        return None

    log_pipeline_stage(
        logger,
        "LLM_RAW_OUTPUT_SAVED",
        audit_id=audit_id,
        document_id=document_id,
        domain=domain,
        started_at=started,
        status="completed",
        path=str(path),
        raw_chars=len(content or ""),
        cleaned_chars=len(cleaned_content or ""),
        repaired_chars=len(repaired_content or "") if repaired_content is not None else None,
    )
    return str(path)


def _safe_filename_part(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip())
    return safe[:80] or "llm-output"


def is_retryable_llm_error(exc: Exception | None) -> bool:
    if isinstance(exc, (json.JSONDecodeError, LLMResponseValidationError)):
        return True
    status_code = _status_code_from_exception(exc)
    if status_code in {402, 429, 500, 502, 503, 504}:
        return True
    detail = str(exc or "").lower()
    retryable_markers = (
        "402",
        "429",
        "500",
        "503",
        "insufficient credits",
        "rate limit",
        "high demand",
        "model unavailable",
        "overloaded",
        "timeout",
        "timed out",
        "temporarily unavailable",
        "server error",
    )
    return any(marker in detail for marker in retryable_markers)


def _status_code_from_exception(exc: Exception | None) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


llm_service = LLMService()
