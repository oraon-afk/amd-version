from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

OPENROUTER_PROVIDER = "openrouter"
GROQ_PROVIDER = "groq"
GEMINI_PROVIDER = "gemini"
GEMINI_PROVIDER_ALIASES = frozenset({"google", "google-gemini"})
SUPPORTED_LLM_PROVIDERS = frozenset(
    {OPENROUTER_PROVIDER, GROQ_PROVIDER, GEMINI_PROVIDER, *GEMINI_PROVIDER_ALIASES},
)
OPENAI_COMPATIBLE_PROVIDERS = frozenset({OPENROUTER_PROVIDER, GROQ_PROVIDER})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI-Driven Audit & Compliance Assistant"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL"))

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 60
    jwt_refresh_token_days: int = 7
    password_hash_algorithm: str = "bcrypt"

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"
    s3_bucket: str = Field(default="audit-compliance-storage", validation_alias=AliasChoices("S3_BUCKET", "AWS_S3_BUCKET"))
    s3_rule_bucket: str | None = None
    s3_temp_upload_bucket: str | None = None
    s3_report_bucket: str | None = None
    s3_temp_upload_prefix: str = "temp-user-uploads/"
    s3_rule_prefix: str = "compliance-rules/"
    s3_report_prefix: str = "audit-reports/"
    temp_document_retention_hours: int = 24

    storage_root: str = "storage"
    storage_temp_dir: str = "temp"
    storage_rules_dir: str = "rules"
    storage_compliance_dir: str = "compliance"
    storage_policies_dir: str = "policies"
    cleanup_interval_seconds: int = 3600

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_rule_collection: str = "compliance_rules"
    qdrant_upload_collection: str = "audit_document_chunks"

    llm_provider: str = Field(validation_alias=AliasChoices("LLM_PROVIDER"))
    secondary_llm_provider: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SECONDARY_LLM_PROVIDER", "LLM_SECONDARY_PROVIDER", "FALLBACK_LLM_PROVIDER"),
    )

    openrouter_api_key: str | None = None
    openrouter_base_url: str | None = None
    openrouter_model: str | None = None
    openrouter_fallback_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_FALLBACK_MODEL", "LLM_FALLBACK_MODEL", "FALLBACK_LLM_MODEL"),
    )
    openrouter_http_referer: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_HTTP_REFERER", "OPENROUTER_SITE_URL"),
    )
    openrouter_app_title: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_APP_TITLE", "OPENROUTER_APP_NAME"),
    )
    llm_timeout_seconds: int = 45
    llm_retry_attempts: int = 3
    llm_retry_backoff_seconds: float = Field(
        default=1.0,
        validation_alias=AliasChoices("LLM_RETRY_BACKOFF_SECONDS", "LLM_BACKOFF_SECONDS"),
    )
    max_output_tokens: int = Field(
        default=900,
        validation_alias=AliasChoices("MAX_OUTPUT_TOKENS", "LLM_MAX_OUTPUT_TOKENS"),
    )
    max_context_chars: int = Field(
        default=7000,
        validation_alias=AliasChoices("MAX_CONTEXT_CHARS", "LLM_MAX_CONTEXT_CHARS"),
    )
    llm_max_rules: int = Field(
        default=3,
        validation_alias=AliasChoices("LLM_MAX_RULES", "MAX_LLM_RULES"),
    )
    llm_max_chunks: int = Field(
        default=5,
        validation_alias=AliasChoices("LLM_MAX_CHUNKS", "MAX_LLM_CHUNKS"),
    )

    groq_api_key: str | None = None
    groq_base_url: str | None = None
    groq_model: str | None = None
    groq_fallback_model: str | None = None

    gemini_api_key: str | None = None
    gemini_api_url: str | None = None
    gemini_model: str | None = None
    gemini_fallback_model: str | None = None
    gemini_thinking_budget: int | None = None

    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "OPENAI_EMBEDDING_MODEL"),
    )
    reranker_model: str = "BAAI/bge-reranker-base"
    chunk_size: int = Field(default=800, validation_alias=AliasChoices("CHUNK_SIZE", "CHUNK_MAX_TOKENS"))
    chunk_overlap: int = Field(
        default=120,
        validation_alias=AliasChoices("CHUNK_OVERLAP", "CHUNK_OVERLAP_TOKENS"),
    )
    top_k_vector: int = Field(default=25, validation_alias=AliasChoices("TOP_K_VECTOR", "VECTOR_TOP_K"))
    top_k_bm25: int = Field(default=25, validation_alias=AliasChoices("TOP_K_BM25", "BM25_TOP_K"))
    final_top_k: int = Field(default=8, validation_alias=AliasChoices("FINAL_TOP_K", "RERANK_TOP_K"))
    embedding_batch_size: int = Field(default=32, validation_alias=AliasChoices("EMBEDDING_BATCH_SIZE", "BATCH_SIZE"))
    semantic_similarity_threshold: float = Field(
        default=0.2,
        validation_alias=AliasChoices("SEMANTIC_SIMILARITY_THRESHOLD", "MIN_SEMANTIC_SCORE"),
    )
    min_confidence_threshold: float = Field(
        default=0.65,
        validation_alias=AliasChoices("MIN_CONFIDENCE_THRESHOLD", "MIN_CONTEXT_CONFIDENCE"),
    )
    enable_reranking: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_RERANKER", "ENABLE_RERANKING"),
    )
    enable_context_validation: bool = True
    enable_hybrid_retrieval: bool = True
    preload_models_on_startup: bool = True

    max_upload_mb: int = 25
    allowed_file_types: str = "application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    rule_categories: str = "HR,Security,Finance,Legal,Insurance,GDPR,Internal Policies"
    default_admin_emails: str = ""

    @property
    def upload_bucket(self) -> str:
        return self.s3_temp_upload_bucket or self.s3_bucket

    @property
    def rule_bucket(self) -> str:
        return self.s3_rule_bucket or self.s3_bucket

    @property
    def report_bucket(self) -> str:
        return self.s3_report_bucket or self.s3_bucket

    auto_create_tables: bool = True

    @property
    def qdrant_url_is_valid(self) -> bool:
        return bool(self.qdrant_url and self.qdrant_url.startswith(("http://", "https://")))

    @property
    def llm_provider_normalized(self) -> str:
        return self._normalize_provider(self.llm_provider)

    @property
    def secondary_llm_provider_normalized(self) -> str | None:
        provider = self._normalize_provider(self.secondary_llm_provider)
        if not provider or provider == self.llm_provider_normalized:
            return None
        return provider

    @property
    def llm_api_key(self) -> str | None:
        return self.provider_api_key(self.llm_provider_normalized)

    @property
    def llm_base_url(self) -> str | None:
        return self.provider_base_url(self.llm_provider_normalized)

    @property
    def llm_model(self) -> str | None:
        return self.provider_model(self.llm_provider_normalized)

    @property
    def llm_fallback_model(self) -> str | None:
        return self.provider_fallback_model(self.llm_provider_normalized)

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url and self.llm_model)

    def provider_api_key(self, provider: str | None) -> str | None:
        normalized = self._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return self.openrouter_api_key
        if normalized == GROQ_PROVIDER:
            return self.groq_api_key
        if normalized == GEMINI_PROVIDER:
            return self.gemini_api_key
        return None

    def provider_base_url(self, provider: str | None) -> str | None:
        normalized = self._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return self.openrouter_base_url
        if normalized == GROQ_PROVIDER:
            return self.groq_base_url
        if normalized == GEMINI_PROVIDER:
            return self.gemini_api_url
        return None

    def provider_model(self, provider: str | None) -> str | None:
        normalized = self._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return self.openrouter_model
        if normalized == GROQ_PROVIDER:
            return self.groq_model
        if normalized == GEMINI_PROVIDER:
            return self.gemini_model
        return None

    def provider_fallback_model(self, provider: str | None) -> str | None:
        normalized = self._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return self.openrouter_fallback_model
        if normalized == GROQ_PROVIDER:
            return self.groq_fallback_model
        if normalized == GEMINI_PROVIDER:
            return self.gemini_fallback_model
        return None

    def provider_configured(self, provider: str | None) -> bool:
        normalized = self._normalize_provider(provider)
        return bool(
            normalized
            and normalized in SUPPORTED_LLM_PROVIDERS
            and self.provider_api_key(normalized)
            and self.provider_base_url(normalized)
            and self.provider_model(normalized)
        )

    @staticmethod
    def provider_env_names(provider: str | None) -> tuple[str, str, str]:
        normalized = Settings._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_MODEL"
        if normalized == GROQ_PROVIDER:
            return "GROQ_API_KEY", "GROQ_BASE_URL", "GROQ_MODEL"
        if normalized == GEMINI_PROVIDER:
            return "GEMINI_API_KEY", "GEMINI_API_URL", "GEMINI_MODEL"
        return "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"

    def validate_startup_configuration(self) -> None:
        errors: list[str] = []

        def require(name: str, value: object) -> None:
            if value is None or not str(value).strip():
                errors.append(f"{name} is required")

        require("DATABASE_URL", self.database_url)
        require("QDRANT_URL", self.qdrant_url)
        if self.qdrant_url and not self.qdrant_url_is_valid:
            errors.append("QDRANT_URL must start with http:// or https://")
        require("QDRANT_API_KEY", self.qdrant_api_key)
        require("AWS_REGION", self.aws_region)
        require("AWS_ACCESS_KEY_ID", self.aws_access_key_id)
        require("AWS_SECRET_ACCESS_KEY", self.aws_secret_access_key)
        require("S3_RULE_BUCKET or S3_BUCKET", self.rule_bucket)
        require("S3_TEMP_UPLOAD_BUCKET or S3_BUCKET", self.upload_bucket)
        require("S3_REPORT_BUCKET or S3_BUCKET", self.report_bucket)

        provider = self.llm_provider_normalized
        if provider not in SUPPORTED_LLM_PROVIDERS:
            errors.append(f"LLM_PROVIDER is unsupported: {self.llm_provider}")
        else:
            key_name, base_url_name, model_name = self.provider_env_names(provider)
            require(key_name, self.provider_api_key(provider))
            require(base_url_name, self.provider_base_url(provider))
            require(model_name, self.provider_model(provider))

        secondary_provider = self.secondary_llm_provider_normalized
        if secondary_provider:
            if secondary_provider not in SUPPORTED_LLM_PROVIDERS:
                errors.append(f"SECONDARY_LLM_PROVIDER is unsupported: {self.secondary_llm_provider}")
            else:
                key_name, base_url_name, model_name = self.provider_env_names(secondary_provider)
                require(key_name, self.provider_api_key(secondary_provider))
                require(base_url_name, self.provider_base_url(secondary_provider))
                require(model_name, self.provider_model(secondary_provider))

        if errors:
            details = "; ".join(errors)
            raise RuntimeError(f"Startup configuration validation failed: {details}.")

    @property
    def diagnostics_summary(self) -> dict[str, str | bool | int]:
        return {
            "app_env": self.app_env,
            "debug": self.debug,
            "database_configured": bool(self.database_url),
            "qdrant_configured": bool(self.qdrant_url and self.qdrant_api_key),
            "qdrant_url_valid": self.qdrant_url_is_valid,
            "s3_rule_bucket_configured": bool(self.rule_bucket),
            "s3_temp_bucket_configured": bool(self.upload_bucket),
            "s3_report_bucket_configured": bool(self.report_bucket),
            "llm_provider": self.llm_provider_normalized,
            "llm_model": self.llm_model or "",
            "llm_fallback_model_configured": bool(self.llm_fallback_model),
            "secondary_llm_provider": self.secondary_llm_provider_normalized or "",
            "llm_configured": self.llm_configured,
            "openrouter_configured": bool(
                self.openrouter_api_key and self.openrouter_base_url and self.openrouter_model,
            ),
            "groq_configured": bool(self.groq_api_key and self.groq_base_url and self.groq_model),
            "gemini_configured": bool(self.gemini_api_key and self.gemini_api_url and self.gemini_model),
            "cors_origins_count": len(self.cors_origin_list),
            "jwt_configured": bool(self.jwt_secret_key and self.jwt_secret_key != "change-me"),
            "storage_root": self.storage_root,
            "temp_retention_hours": self.temp_document_retention_hours,
        }

    @property
    def cors_origin_list(self) -> list[str]:
        return self._parse_csv_list(self.cors_origins)

    @property
    def allowed_file_type_list(self) -> list[str]:
        return self._parse_csv_list(self.allowed_file_types)

    @property
    def rule_category_list(self) -> list[str]:
        return self._parse_csv_list(self.rule_categories)

    @property
    def default_admin_email_list(self) -> list[str]:
        return [item.lower() for item in self._parse_csv_list(self.default_admin_emails)]

    @field_validator("cors_origins", "allowed_file_types", "rule_categories", "default_admin_emails", mode="before")
    @classmethod
    def _normalize_csv(cls, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ",".join(str(item).strip() for item in value if str(item).strip())
        return str(value)

    @field_validator("debug", mode="before")
    @classmethod
    def _parse_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on", "debug", "development", "dev"}:
            return True
        if text in {"0", "false", "no", "off", "release", "production", "prod"}:
            return False
        return False

    @staticmethod
    def _parse_csv_list(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _normalize_provider(value: str | None) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in GEMINI_PROVIDER_ALIASES:
            return GEMINI_PROVIDER
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
