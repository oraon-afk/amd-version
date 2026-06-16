from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import logging
from time import sleep
from typing import BinaryIO
from urllib.parse import urlparse

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_once

logger = get_logger(__name__)


def build_s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


@dataclass(frozen=True)
class S3ObjectRef:
    bucket: str
    key: str
    uri: str


class S3Storage:
    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import boto3

            client_kwargs = {
                "region_name": settings.aws_region,
                "aws_access_key_id": settings.aws_access_key_id,
                "aws_secret_access_key": settings.aws_secret_access_key,
            }
            if settings.minio_endpoint:
                client_kwargs["endpoint_url"] = settings.minio_endpoint

            self._client = boto3.client("s3", **client_kwargs)
        return self._client

    def check_connection(self) -> bool:
        buckets = [
            settings.rule_bucket,
            settings.upload_bucket,
            settings.report_bucket,
        ]
        configured_buckets = [bucket.strip() for bucket in buckets if bucket and bucket.strip()]
        if not configured_buckets:
            log_once(
                logger,
                logging.WARNING,
                "s3_connection_check_skipped_not_configured",
                "S3_CONNECTION_CHECK_SKIPPED reason=bucket_not_configured",
            )
            return False
        for bucket in configured_buckets:
            self.client.head_bucket(Bucket=bucket)
        return True

    def configured(self, bucket: str | None = None) -> bool:
        if bucket is not None:
            return bool(str(bucket).strip())
        return any(
            bool(str(value or "").strip())
            for value in (settings.rule_bucket, settings.upload_bucket, settings.report_bucket, settings.s3_bucket)
        )

    def warm(self) -> bool:
        if not self.configured():
            log_once(
                logger,
                logging.WARNING,
                "s3_warm_skipped_not_configured",
                "S3_WARM_SKIPPED reason=bucket_not_configured",
            )
            return False
        _ = self.client
        return True

    def upload_bytes(
        self,
        *,
        bucket: str,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
        expires_at: datetime | None = None,
    ) -> S3ObjectRef:
        bucket = self._require_bucket(bucket)
        key = self._require_key(key)
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata
        if expires_at:
            extra_args["Expires"] = expires_at
        self._retry(
            lambda: self.client.upload_fileobj(
                Fileobj=BytesIO(content),
                Bucket=bucket,
                Key=key,
                ExtraArgs=extra_args,
            ),
        )
        return S3ObjectRef(bucket=bucket, key=key, uri=build_s3_uri(bucket, key))

    def upload_fileobj(
        self,
        *,
        bucket: str,
        key: str,
        fileobj: BinaryIO,
        content_type: str,
    ) -> S3ObjectRef:
        bucket = self._require_bucket(bucket)
        key = self._require_key(key)
        self._retry(
            lambda: self.client.upload_fileobj(
                Fileobj=fileobj,
                Bucket=bucket,
                Key=key,
                ExtraArgs={"ContentType": content_type},
            ),
        )
        return S3ObjectRef(bucket=bucket, key=key, uri=build_s3_uri(bucket, key))

    def delete_object(self, *, bucket: str, key: str) -> None:
        bucket = self._require_bucket(bucket)
        key = self._require_key(key)
        self.client.delete_object(Bucket=bucket, Key=key)

    def read_bytes(self, *, bucket: str, key: str) -> bytes:
        bucket = self._require_bucket(bucket)
        key = self._require_key(key)
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def read_uri_bytes(self, uri: str) -> bytes:
        bucket, key = parse_s3_uri(uri)
        return self.read_bytes(bucket=bucket, key=key)

    def delete_uri(self, uri: str | None) -> bool:
        if not uri:
            return False
        try:
            bucket, key = parse_s3_uri(uri)
            self.delete_object(bucket=bucket, key=key)
            return True
        except Exception as exc:
            logger.warning("S3_DELETE_SKIPPED uri=%s error=%s", uri, exc)
            return False

    def prefix_summary(self, *, bucket: str, prefixes: list[str]) -> dict[str, dict[str, int]]:
        summary: dict[str, dict[str, int]] = {}
        normalized_prefixes = [prefix.strip("/") for prefix in prefixes if prefix and prefix.strip("/")]
        if not self.configured(bucket):
            log_once(
                logger,
                logging.WARNING,
                "s3_prefix_summary_skipped_not_configured",
                "S3_PREFIX_SUMMARY_SKIPPED reason=bucket_not_configured",
            )
            return {prefix: {"files": 0, "bytes": 0} for prefix in normalized_prefixes}
        bucket = bucket.strip()
        for normalized in normalized_prefixes:
            try:
                paginator = self.client.get_paginator("list_objects_v2")
                file_count = 0
                total_bytes = 0
                for page in paginator.paginate(Bucket=bucket, Prefix=f"{normalized}/"):
                    for item in page.get("Contents", []):
                        file_count += 1
                        total_bytes += int(item.get("Size") or 0)
                summary[normalized] = {"files": file_count, "bytes": total_bytes}
            except Exception as exc:
                log_once(
                    logger,
                    logging.WARNING,
                    f"s3_prefix_summary_failed:{bucket}:{normalized}",
                    "S3_PREFIX_SUMMARY_FAILED bucket=%s prefix=%s error=%s",
                    bucket,
                    normalized,
                    exc,
                )
                summary[normalized] = {"files": 0, "bytes": 0}
        return summary

    @staticmethod
    def _require_bucket(bucket: str | None) -> str:
        cleaned = str(bucket or "").strip()
        if not cleaned:
            raise ValueError("S3 bucket is not configured.")
        return cleaned

    @staticmethod
    def _require_key(key: str | None) -> str:
        cleaned = str(key or "").strip().lstrip("/")
        if not cleaned:
            raise ValueError("S3 object key is required.")
        return cleaned

    @staticmethod
    def _retry(operation, *, attempts: int = 3):
        last_exc = None
        for attempt in range(attempts):
            try:
                return operation()
            except Exception as exc:
                last_exc = exc
                if attempt == attempts - 1:
                    break
                sleep(0.4 * (attempt + 1))
        raise last_exc


s3_storage = S3Storage()
