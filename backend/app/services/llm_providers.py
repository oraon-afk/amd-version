from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from openai import OpenAI

from backend.app.core.config import (
    GEMINI_PROVIDER,
    OPENAI_COMPATIBLE_PROVIDERS,
    OPENROUTER_PROVIDER,
    settings,
)


@dataclass(frozen=True)
class LLMProviderAttempt:
    provider: str
    model: str
    api_key: str
    base_url: str
    stage: str


@dataclass(frozen=True)
class LLMGenerationResult:
    content: str
    usage: dict[str, int | None]


class LLMProviderHTTPError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, detail: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class ProviderRouter:
    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}

    def warm(self) -> bool:
        queue = self.retry_queue()
        if not queue:
            raise RuntimeError("No configured LLM provider is available.")
        self._provider_for(queue[0].provider).warm(queue[0])
        return True

    def retry_queue(self) -> list[LLMProviderAttempt]:
        limit = max(1, int(settings.llm_retry_attempts or 1))
        primary_provider = settings.llm_provider_normalized
        queue: list[LLMProviderAttempt] = []
        seen_attempts: set[tuple[str, str]] = set()

        def append_unique(attempt: LLMProviderAttempt | None) -> None:
            if attempt is None:
                return
            key = (attempt.provider, attempt.model)
            if key in seen_attempts:
                return
            seen_attempts.add(key)
            queue.append(attempt)

        primary_model = settings.provider_model(primary_provider)
        primary_attempt = self._attempt(
            provider=primary_provider,
            model=primary_model,
            stage="configured_model",
        )
        append_unique(primary_attempt)

        fallback_model = settings.provider_fallback_model(primary_provider)
        fallback_attempt = self._attempt(
            provider=primary_provider,
            model=fallback_model,
            stage="configured_fallback_model",
        )
        append_unique(fallback_attempt)

        secondary_provider = settings.secondary_llm_provider_normalized
        if secondary_provider:
            secondary_attempt = self._attempt(
                provider=secondary_provider,
                model=settings.provider_model(secondary_provider),
                stage="secondary_provider",
            )
            append_unique(secondary_attempt)
            secondary_fallback = self._attempt(
                provider=secondary_provider,
                model=settings.provider_fallback_model(secondary_provider),
                stage="secondary_provider_fallback_model",
            )
            append_unique(secondary_fallback)

        return queue[:limit]

    def generate(
        self,
        *,
        attempt: LLMProviderAttempt,
        system: str,
        user: str,
        max_tokens: int,
    ) -> LLMGenerationResult:
        return self._provider_for(attempt.provider).generate(
            attempt=attempt,
            system=system,
            user=user,
            max_tokens=max_tokens,
        )

    def validate_model_availability(self) -> LLMGenerationResult:
        queue = self.retry_queue()
        if not queue:
            raise RuntimeError("No configured LLM provider is available.")
        return self.generate(
            attempt=queue[0],
            system="Return a compact JSON object for this health check.",
            user='{"status":"ok"}',
            max_tokens=32,
        )

    def _attempt(self, *, provider: str | None, model: str | None, stage: str) -> LLMProviderAttempt | None:
        normalized = settings._normalize_provider(provider)
        api_key = settings.provider_api_key(normalized)
        base_url = settings.provider_base_url(normalized)
        clean_model = str(model or "").strip()
        if not normalized or not api_key or not base_url or not clean_model:
            return None
        return LLMProviderAttempt(
            provider=normalized,
            model=clean_model,
            api_key=api_key,
            base_url=base_url,
            stage=stage,
        )

    def _provider_for(self, provider: str) -> "BaseProvider":
        normalized = settings._normalize_provider(provider)
        if normalized not in self._providers:
            if normalized in OPENAI_COMPATIBLE_PROVIDERS:
                self._providers[normalized] = OpenAICompatibleProvider()
            elif normalized == GEMINI_PROVIDER:
                self._providers[normalized] = GeminiProvider()
            else:
                raise RuntimeError(f"Unsupported LLM provider: {provider}")
        return self._providers[normalized]


class BaseProvider:
    def warm(self, attempt: LLMProviderAttempt) -> bool:
        return bool(attempt.api_key and attempt.base_url and attempt.model)

    def generate(
        self,
        *,
        attempt: LLMProviderAttempt,
        system: str,
        user: str,
        max_tokens: int,
    ) -> LLMGenerationResult:
        raise NotImplementedError


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self) -> None:
        self._clients: dict[tuple[str, str], OpenAI] = {}

    def warm(self, attempt: LLMProviderAttempt) -> bool:
        self._client(attempt)
        return True

    def generate(
        self,
        *,
        attempt: LLMProviderAttempt,
        system: str,
        user: str,
        max_tokens: int,
    ) -> LLMGenerationResult:
        response = self._client(attempt).chat.completions.create(
            model=attempt.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        usage = response.usage
        return LLMGenerationResult(
            content=response.choices[0].message.content or "{}",
            usage={
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            },
        )

    def _client(self, attempt: LLMProviderAttempt) -> OpenAI:
        key = (attempt.provider, attempt.base_url)
        if key not in self._clients:
            default_headers: dict[str, str] = {}
            if attempt.provider == OPENROUTER_PROVIDER:
                if settings.openrouter_http_referer:
                    default_headers["HTTP-Referer"] = settings.openrouter_http_referer
                default_headers["X-Title"] = settings.openrouter_app_title or settings.app_name
            self._clients[key] = OpenAI(
                api_key=attempt.api_key,
                base_url=attempt.base_url,
                default_headers=default_headers or None,
                timeout=settings.llm_timeout_seconds,
                max_retries=0,
            )
        return self._clients[key]


class GeminiProvider(BaseProvider):
    def generate(
        self,
        *,
        attempt: LLMProviderAttempt,
        system: str,
        user: str,
        max_tokens: int,
    ) -> LLMGenerationResult:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system.strip()}\n\n{user.strip()}"}],
                },
            ],
            "generationConfig": self._generation_config(max_tokens=max_tokens),
        }
        request = Request(
            self._generate_url(attempt),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=settings.llm_timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMProviderHTTPError(
                f"Gemini HTTP {exc.code}: {detail[:500]}",
                status_code=exc.code,
                detail=detail,
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"Gemini request failed: {exc}") from exc

        response_payload = json.loads(raw)
        candidates = response_payload.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {raw[:500]}")
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict)).strip()
        if not text:
            raise RuntimeError(f"Gemini returned empty content: {raw[:500]}")
        usage = response_payload.get("usageMetadata") if isinstance(response_payload, dict) else None
        return LLMGenerationResult(
            content=text,
            usage={
                "prompt_tokens": _int_or_none((usage or {}).get("promptTokenCount")),
                "completion_tokens": _int_or_none((usage or {}).get("candidatesTokenCount")),
                "total_tokens": _int_or_none((usage or {}).get("totalTokenCount")),
            },
        )

    @staticmethod
    def _generation_config(*, max_tokens: int) -> dict[str, Any]:
        generation_config: dict[str, Any] = {
            "temperature": 0.1,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        }
        if settings.gemini_thinking_budget is not None:
            generation_config["thinkingConfig"] = {"thinkingBudget": settings.gemini_thinking_budget}
        return generation_config

    @staticmethod
    def _generate_url(attempt: LLMProviderAttempt) -> str:
        base_url = attempt.base_url.rstrip("/")
        if "{model}" in base_url:
            endpoint = base_url.format(model=attempt.model)
        elif base_url.endswith(":generateContent"):
            endpoint = base_url
        elif base_url.endswith("/models"):
            endpoint = f"{base_url}/{attempt.model}:generateContent"
        else:
            endpoint = f"{base_url.rstrip('/')}/models/{attempt.model}:generateContent"
        separator = "&" if "?" in endpoint else "?"
        return f"{endpoint}{separator}{urlencode({'key': attempt.api_key})}"


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
