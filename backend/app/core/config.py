from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

OPENROUTER_PROVIDER = "openrouter"
GROQ_PROVIDER = "groq"
GEMINI_PROVIDER = "gemini"
OLLAMA_PROVIDER = "ollama"
GEMINI_PROVIDER_ALIASES = frozenset({"google", "google-gemini"})
SUPPORTED_LLM_PROVIDERS = frozenset(
    {OPENROUTER_PROVIDER, GROQ_PROVIDER, GEMINI_PROVIDER, OLLAMA_PROVIDER, *GEMINI_PROVIDER_ALIASES},
)
OPENAI_COMPATIBLE_PROVIDERS = frozenset({OPENROUTER_PROVIDER, GROQ_PROVIDER, OLLAMA_PROVIDER})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI Audit & Compliance Assistant"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = False
    deployment_mode: str = "cloud"  # "cloud" | "hybrid" | "onprem"
    ollama_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    enable_caching: bool = True
    ollama_model: str | None = None
    minio_endpoint: str | None = None
    local_qdrant_url: str | None = None
    local_embedding_model: str | None = None
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL"),
    )
    database_connect_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("DATABASE_CONNECT_RETRIES", "DB_CONNECT_RETRIES"),
    )
    database_retry_backoff_seconds: float = Field(
        default=0.5,
        validation_alias=AliasChoices("DATABASE_RETRY_BACKOFF_SECONDS", "DB_RETRY_BACKOFF_SECONDS"),
    )
    database_pool_recycle_seconds: int = Field(
        default=1800,
        validation_alias=AliasChoices("DATABASE_POOL_RECYCLE_SECONDS", "DB_POOL_RECYCLE_SECONDS"),
    )

    jwt_secret_key: str | None = Field(default=None, validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"))
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 60
    jwt_refresh_token_days: int = 7
    password_hash_algorithm: str = "bcrypt"

    aws_access_key_id: str | None = Field(default=None, validation_alias=AliasChoices("AWS_ACCESS_KEY_ID", "S3_ACCESS_KEY"))
    aws_secret_access_key: str | None = Field(default=None, validation_alias=AliasChoices("AWS_SECRET_ACCESS_KEY", "S3_SECRET_KEY"))
    aws_region: str = Field(default="us-east-1", validation_alias=AliasChoices("AWS_REGION", "S3_REGION"))
    s3_bucket: str = Field(default="", validation_alias=AliasChoices("S3_BUCKET", "AWS_S3_BUCKET"))
    s3_rule_bucket: str | None = Field(default=None, validation_alias=AliasChoices("S3_RULE_BUCKET"))
    s3_temp_upload_bucket: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_TEMP_UPLOAD_BUCKET", "S3_TEMP_BUCKET"),
    )
    s3_report_bucket: str | None = Field(default=None, validation_alias=AliasChoices("S3_REPORT_BUCKET"))
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
    qdrant_rule_collection: str = Field(
        default="compliance_rules",
        validation_alias=AliasChoices("QDRANT_RULE_COLLECTION", "QDRANT_COLLECTION"),
    )
    qdrant_upload_collection: str = Field(default="audit_document_chunks", validation_alias=AliasChoices("QDRANT_UPLOAD_COLLECTION"))

    primary_llm_provider: str = Field(default=OPENROUTER_PROVIDER, validation_alias=AliasChoices("PRIMARY_LLM_PROVIDER", "LLM_PROVIDER"))
    primary_llm_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PRIMARY_MODEL", "PRIMARY_LLM_MODEL", "LLM_MODEL"),
    )
    secondary_llm_provider: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SECONDARY_LLM_PROVIDER", "LLM_SECONDARY_PROVIDER", "FALLBACK_LLM_PROVIDER"),
    )
    secondary_llm_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SECONDARY_MODEL", "SECONDARY_LLM_MODEL", "LLM_SECONDARY_MODEL", "FALLBACK_LLM_MODEL"),
    )
    tertiary_llm_provider: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TERTIARY_LLM_PROVIDER", "FINAL_LLM_PROVIDER"),
    )
    tertiary_llm_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TERTIARY_LLM_MODEL", "FINAL_LLM_MODEL"),
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
    llm_retry_attempts: int = Field(
        default=3,
        validation_alias=AliasChoices("MAX_LLM_RETRIES", "LLM_RETRY_ATTEMPTS"),
    )
    llm_retry_backoff_seconds: float = Field(
        default=1.0,
        validation_alias=AliasChoices("LLM_RETRY_BACKOFF_SECONDS", "LLM_BACKOFF_SECONDS"),
    )
    json_repair_enabled: bool = Field(default=True, validation_alias=AliasChoices("JSON_REPAIR_ENABLED"))
    llm_max_completion_tokens: int = Field(
        default=700,
        validation_alias=AliasChoices("LLM_MAX_COMPLETION_TOKENS", "MAX_LLM_COMPLETION_TOKENS"),
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
        default="",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "OPENAI_EMBEDDING_MODEL"),
    )
    reranker_model: str = Field(default="", validation_alias=AliasChoices("RERANKER_MODEL"))
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
    max_bulk_documents: int = Field(default=2000, validation_alias=AliasChoices("MAX_BULK_DOCUMENTS"))
    bulk_upload_max_retries: int = Field(default=2, validation_alias=AliasChoices("BULK_UPLOAD_MAX_RETRIES"))
    bulk_read_chunk_size_bytes: int = Field(
        default=1024 * 1024,
        validation_alias=AliasChoices("BULK_READ_CHUNK_SIZE_BYTES"),
    )
    qdrant_timeout_seconds: int = Field(default=30, validation_alias=AliasChoices("QDRANT_TIMEOUT_SECONDS"))
    qdrant_retry_attempts: int = Field(default=3, validation_alias=AliasChoices("QDRANT_RETRY_ATTEMPTS"))
    qdrant_retry_backoff_seconds: float = Field(
        default=0.4,
        validation_alias=AliasChoices("QDRANT_RETRY_BACKOFF_SECONDS"),
    )
    digital_twin_cache_ttl_seconds: int = Field(default=300, validation_alias=AliasChoices("DIGITAL_TWIN_CACHE_TTL_SECONDS"))
    allowed_file_types: str = "application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    rule_categories: str = "HR,Security,Finance,Legal,Insurance,GDPR,Internal Policies,Banking,Healthcare,HR-Policy"
    default_admin_emails: str = ""

    @property
    def upload_bucket(self) -> str:
        return self._clean_optional(self.s3_temp_upload_bucket) or self._clean_optional(self.s3_bucket) or ""

    @property
    def rule_bucket(self) -> str:
        return self._clean_optional(self.s3_rule_bucket) or self._clean_optional(self.s3_bucket) or ""

    @property
    def report_bucket(self) -> str:
        return self._clean_optional(self.s3_report_bucket) or self._clean_optional(self.s3_bucket) or ""

    auto_create_tables: bool = True

    @property
    def qdrant_url_is_valid(self) -> bool:
        return bool(self.qdrant_url and self.qdrant_url.strip().startswith(("http://", "https://")))

    @property
    def llm_provider_normalized(self) -> str:
        return self.primary_llm_provider_normalized

    @property
    def primary_llm_provider_normalized(self) -> str:
        return self._normalize_provider(self.primary_llm_provider)

    @property
    def secondary_llm_provider_normalized(self) -> str | None:
        provider = self._normalize_provider(self.secondary_llm_provider)
        if not provider:
            return None
        return provider

    @property
    def tertiary_llm_provider_normalized(self) -> str | None:
        provider = self._normalize_provider(self.tertiary_llm_provider)
        if not provider:
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
        return self.primary_llm_model or self.provider_model(self.llm_provider_normalized)

    @property
    def llm_fallback_model(self) -> str | None:
        return self.provider_fallback_model(self.llm_provider_normalized)

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url and self.llm_model)

    @property
    def max_llm_retries(self) -> int:
        return self.llm_retry_attempts

    def provider_api_key(self, provider: str | None) -> str | None:
        normalized = self._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return self.openrouter_api_key
        if normalized == GROQ_PROVIDER:
            return self.groq_api_key
        if normalized == GEMINI_PROVIDER:
            return self.gemini_api_key
        if normalized == OLLAMA_PROVIDER:
            return "ollama-local-key"
        return None

    def provider_base_url(self, provider: str | None) -> str | None:
        normalized = self._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return self.openrouter_base_url
        if normalized == GROQ_PROVIDER:
            return self.groq_base_url
        if normalized == GEMINI_PROVIDER:
            return self.gemini_api_url
        if normalized == OLLAMA_PROVIDER:
            return self.ollama_url or "http://localhost:11434"
        return None

    def provider_model(self, provider: str | None) -> str | None:
        normalized = self._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return self.openrouter_model
        if normalized == GROQ_PROVIDER:
            return self.groq_model
        if normalized == GEMINI_PROVIDER:
            return self.gemini_model
        if normalized == OLLAMA_PROVIDER:
            return self.ollama_model or "llama2"
        return None

    def provider_fallback_model(self, provider: str | None) -> str | None:
        normalized = self._normalize_provider(provider)
        if normalized == OPENROUTER_PROVIDER:
            return self.openrouter_fallback_model
        if normalized == GROQ_PROVIDER:
            return self.groq_fallback_model
        if normalized == GEMINI_PROVIDER:
            return self.gemini_fallback_model
        if normalized == OLLAMA_PROVIDER:
            return self.ollama_model or "llama2"
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
        if normalized == OLLAMA_PROVIDER:
            return "OLLAMA_API_KEY", "OLLAMA_URL", "OLLAMA_MODEL"
        return "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"

    def validate_startup_configuration(self) -> None:
        _ = self.configuration_warnings

    @property
    def configuration_warnings(self) -> list[str]:
        warnings: list[str] = []

        def require(name: str, value: object) -> None:
            if value is None or not str(value).strip():
                warnings.append(f"{name} is not configured")

        require("DATABASE_URL", self.database_url)
        require("JWT_SECRET_KEY", self.jwt_secret_key)
        if self.jwt_secret_key and self.jwt_secret_key.strip() == "change-me":
            warnings.append("JWT_SECRET_KEY must be changed from the placeholder value")
        require("QDRANT_URL", self.qdrant_url)
        if self.qdrant_url and not self.qdrant_url_is_valid:
            warnings.append("QDRANT_URL must start with http:// or https://")
        require("QDRANT_API_KEY", self.qdrant_api_key)
        require("AWS_REGION", self.aws_region)
        require("AWS_ACCESS_KEY_ID", self.aws_access_key_id)
        require("AWS_SECRET_ACCESS_KEY", self.aws_secret_access_key)
        require("S3_RULE_BUCKET or S3_BUCKET", self.rule_bucket)
        require("S3_TEMP_BUCKET or S3_TEMP_UPLOAD_BUCKET or S3_BUCKET", self.upload_bucket)
        require("S3_REPORT_BUCKET or S3_BUCKET", self.report_bucket)

        provider = self.primary_llm_provider_normalized
        if provider not in SUPPORTED_LLM_PROVIDERS:
            warnings.append(f"PRIMARY_LLM_PROVIDER is unsupported: {self.primary_llm_provider}")
        else:
            key_name, base_url_name, model_name = self.provider_env_names(provider)
            require(key_name, self.provider_api_key(provider))
            require(base_url_name, self.provider_base_url(provider))
            require("PRIMARY_MODEL or PRIMARY_LLM_MODEL or " + model_name, self.llm_model)

        secondary_provider = self.secondary_llm_provider_normalized
        if secondary_provider:
            if secondary_provider not in SUPPORTED_LLM_PROVIDERS:
                warnings.append(f"SECONDARY_LLM_PROVIDER is unsupported: {self.secondary_llm_provider}")
            else:
                key_name, base_url_name, model_name = self.provider_env_names(secondary_provider)
                require(key_name, self.provider_api_key(secondary_provider))
                require(base_url_name, self.provider_base_url(secondary_provider))
                require("SECONDARY_MODEL or SECONDARY_LLM_MODEL or " + model_name, self.secondary_llm_model or self.provider_model(secondary_provider))

        tertiary_provider = self.tertiary_llm_provider_normalized
        if tertiary_provider:
            if tertiary_provider not in SUPPORTED_LLM_PROVIDERS:
                warnings.append(f"TERTIARY_LLM_PROVIDER is unsupported: {self.tertiary_llm_provider}")
            else:
                key_name, base_url_name, model_name = self.provider_env_names(tertiary_provider)
                require(key_name, self.provider_api_key(tertiary_provider))
                require(base_url_name, self.provider_base_url(tertiary_provider))
                require("TERTIARY_LLM_MODEL or " + model_name, self.tertiary_llm_model or self.provider_model(tertiary_provider))

        return warnings

    @property
    def diagnostics_summary(self) -> dict[str, str | bool | int]:
        return {
            "app_env": self.app_env,
            "debug": self.debug,
            "database_configured": bool(self.database_url),
            "database_connect_retries": self.database_connect_retries,
            "database_pool_recycle_seconds": self.database_pool_recycle_seconds,
            "qdrant_configured": bool(self.qdrant_url and self.qdrant_api_key),
            "qdrant_url_valid": self.qdrant_url_is_valid,
            "s3_rule_bucket_configured": bool(self.rule_bucket),
            "s3_temp_bucket_configured": bool(self.upload_bucket),
            "s3_report_bucket_configured": bool(self.report_bucket),
            "llm_provider": self.llm_provider_normalized,
            "llm_model": self.llm_model or "",
            "llm_fallback_model_configured": bool(self.llm_fallback_model),
            "secondary_llm_provider": self.secondary_llm_provider_normalized or "",
            "secondary_llm_model_configured": bool(self.secondary_llm_model),
            "tertiary_llm_provider": self.tertiary_llm_provider_normalized or "",
            "tertiary_llm_model_configured": bool(self.tertiary_llm_model),
            "max_llm_retries": self.max_llm_retries,
            "json_repair_enabled": self.json_repair_enabled,
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
            "digital_twin_cache_ttl_seconds": self.digital_twin_cache_ttl_seconds,
            "configuration_warnings_count": len(self.configuration_warnings),
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

    @field_validator(
        "qdrant_url",
        "qdrant_api_key",
        "database_url",
        "jwt_secret_key",
        "qdrant_rule_collection",
        "qdrant_upload_collection",
        "s3_bucket",
        "s3_rule_bucket",
        "s3_temp_upload_bucket",
        "s3_report_bucket",
        "s3_temp_upload_prefix",
        "s3_rule_prefix",
        "s3_report_prefix",
        "aws_region",
        "openrouter_base_url",
        "openrouter_model",
        "openrouter_fallback_model",
        "gemini_api_url",
        "gemini_model",
        "gemini_fallback_model",
        "groq_base_url",
        "groq_model",
        "groq_fallback_model",
        "primary_llm_model",
        "secondary_llm_model",
        "tertiary_llm_model",
        "ollama_url",
        "ollama_model",
        "minio_endpoint",
        "local_qdrant_url",
        "local_embedding_model",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value

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
    def _clean_optional(value: str | None) -> str | None:
        cleaned = str(value or "").strip()
        return cleaned or None

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
