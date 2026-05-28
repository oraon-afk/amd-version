from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import sleep, time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from json_repair import repair_json
from openai import OpenAI

from backend.app.core.config import PROJECT_ROOT, settings
from backend.app.core.logging import get_logger, log_pipeline_stage

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


class LLMHTTPError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, detail: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class LLMRequestMetadata:
    estimated_tokens: int
    max_tokens: int
    prompt_chars: int


class LLMService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if settings.llm_provider_normalized not in {"openrouter", "groq"}:
                raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
            if not settings.llm_configured:
                raise RuntimeError(
                    f"{settings.llm_provider_normalized} LLM settings are incomplete.",
                )

            default_headers = None
            if settings.llm_provider_normalized == "openrouter":
                default_headers = {
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": settings.app_name,
                }
            self._client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                default_headers=default_headers,
                timeout=settings.llm_timeout_seconds,
                max_retries=0,
            )
        return self._client

    def warm(self) -> bool:
        if settings.llm_provider_normalized in {"openrouter", "groq"}:
            _ = self.client
            return True
        if settings.llm_provider_normalized in {"gemini", "google", "google-gemini"}:
            if not settings.llm_configured:
                raise RuntimeError("Gemini LLM settings are incomplete.")
            return True
        raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

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
        effective_max_tokens = max(1, min(int(max_tokens or settings.max_output_tokens), 900))
        effective_model = self._effective_model_for_attempt(attempt)
        request_metadata = LLMRequestMetadata(
            estimated_tokens=estimate_tokens(system, user),
            max_tokens=effective_max_tokens,
            prompt_chars=len(system) + len(user),
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
            max_tokens=request_metadata.max_tokens,
            **(metadata or {}),
        )
        try:
            log_pipeline_stage(
                logger,
                "LLM_REQUEST",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                status="started",
                provider=settings.llm_provider_normalized,
                model=effective_model,
                attempt=attempt,
                prompt_chars=request_metadata.prompt_chars,
                estimated_tokens=request_metadata.estimated_tokens,
                max_tokens=request_metadata.max_tokens,
                **(metadata or {}),
            )
            content = self._generate_content(
                system=system,
                user=user,
                max_tokens=request_metadata.max_tokens,
                attempt=attempt,
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
            )
            payload = parse_json_response(
                content,
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
            )
            log_pipeline_stage(
                logger,
                "LLM_REQUEST",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                status="completed",
                provider=settings.llm_provider_normalized,
                model=effective_model,
                attempt=attempt,
                max_tokens=request_metadata.max_tokens,
            )
            return payload
        except Exception as exc:
            log_pipeline_stage(
                logger,
                "LLM_REQUEST",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                status="failed",
                provider=settings.llm_provider_normalized,
                model=effective_model,
                attempt=attempt,
                max_tokens=request_metadata.max_tokens,
                retryable=is_retryable_llm_error(exc),
                error=str(exc),
            )
            logger.warning(
                "llm.error provider=%s model=%s attempt=%s max_tokens=%s detail=%s",
                settings.llm_provider_normalized,
                effective_model,
                attempt,
                request_metadata.max_tokens,
                exc,
            )
            raise

    def _generate_content(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        attempt: int,
        audit_id: str | None,
        document_id: str | None,
        domain: str | None,
    ) -> str:
        if settings.llm_provider_normalized in {"openrouter", "groq"}:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "{}"

        if settings.llm_provider_normalized in {"gemini", "google", "google-gemini"}:
            return self._generate_gemini_content(
                system=system,
                user=user,
                max_tokens=max_tokens,
                attempt=attempt,
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
            )

        raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

    def _generate_gemini_content(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        attempt: int,
        audit_id: str | None,
        document_id: str | None,
        domain: str | None,
    ) -> str:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini.")
        model = self._gemini_model_for_attempt(attempt)
        if model != str(settings.gemini_model):
            log_pipeline_stage(
                logger,
                "LLM_MODEL_FALLBACK",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=time(),
                status="selected",
                from_model=settings.gemini_model,
                model=model,
                attempt=attempt,
            )

        url = self._gemini_generate_url(model=model)
        generation_config = self._gemini_generation_config(model=model, max_tokens=max_tokens)

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system.strip()}\n\n{user.strip()}"}],
                }
            ],
            "generationConfig": generation_config,
        }
        for request_attempt in range(1, 3):
            request = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=settings.llm_timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                break
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code == 503 and request_attempt == 1:
                    sleep_seconds = 5 * max(1, attempt)
                    log_pipeline_stage(
                        logger,
                        "LLM_REQUEST",
                        audit_id=audit_id,
                        document_id=document_id,
                        domain=domain,
                        started_at=time(),
                        status="retry_backoff",
                        provider=settings.llm_provider_normalized,
                        model=model,
                        attempt=attempt,
                        request_attempt=request_attempt,
                        http_status=503,
                        sleep_seconds=sleep_seconds,
                    )
                    sleep(sleep_seconds)
                    continue
                raise LLMHTTPError(
                    f"Gemini HTTP {exc.code}: {detail[:500]}",
                    status_code=exc.code,
                    detail=detail,
                ) from exc
            except URLError as exc:
                raise RuntimeError(f"Gemini request failed: {exc}") from exc
        else:
            raise RuntimeError("Gemini request failed without a response.")

        response_payload = json.loads(raw)
        candidates = response_payload.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {raw[:500]}")
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict)).strip()
        if not text:
            raise RuntimeError(f"Gemini returned empty content: {raw[:500]}")
        return text

    def _effective_model_for_attempt(self, attempt: int) -> str | None:
        if settings.llm_provider_normalized in {"gemini", "google", "google-gemini"}:
            return self._gemini_model_for_attempt(attempt)
        return settings.llm_model

    @staticmethod
    def _gemini_model_for_attempt(attempt: int) -> str:
        primary_model = str(settings.gemini_model or "").strip()
        fallback_model = str(settings.gemini_fallback_model or "").strip()
        if (
            attempt >= 3
            and primary_model == "gemini-2.5-flash-lite"
            and fallback_model
            and fallback_model != primary_model
        ):
            return fallback_model
        return primary_model

    @staticmethod
    def _gemini_generation_config(*, model: str, max_tokens: int) -> dict[str, Any]:
        generation_config: dict[str, Any] = {
            "temperature": 0.1,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        }
        if model.startswith("gemini-2.5"):
            generation_config["thinkingConfig"] = {"thinkingBudget": 0}
        return generation_config

    @staticmethod
    def _gemini_generate_url(*, model: str) -> str:
        base_url = str(settings.gemini_api_url or "").rstrip("/")
        if "{model}" in base_url:
            endpoint = base_url.format(model=model)
        elif base_url.endswith(":generateContent"):
            endpoint = base_url
        elif base_url.endswith("/models"):
            endpoint = f"{base_url}/{model}:generateContent"
        else:
            endpoint = f"{base_url.rstrip('/')}/models/{model}:generateContent"
        separator = "&" if "?" in endpoint else "?"
        return f"{endpoint}{separator}{urlencode({'key': settings.gemini_api_key})}"


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
) -> dict[str, Any]:
    started = time()
    cleaned = clean_json_response(content)
    raw_output_path: str | None = None
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
