"""
Feature 3: Agentic Evidence Collection – Service.

Executes evidence collectors (HTTP, SQL, Script), extracts evidence
via simple JSONPath mapping, and stores the results as ExternalEvidence.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
import subprocess
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.db.models.collector import EvidenceCollector, ExternalEvidence
from backend.app.db.models.user import User
from backend.app.db.transactions import commit_or_rollback

logger = get_logger(__name__)


def extract_value_by_path(data: Any, path: str) -> Any:
    """Extract nested value from JSON payload using simple dot/bracket notation."""
    if not path:
        return None
    # Standardize path: remove $. and brackets
    cleaned = path.strip().replace("$.", "")
    cleaned = cleaned.replace("[", ".").replace("]", "")
    parts = cleaned.split(".")
    
    curr = data
    for part in parts:
        if not part:
            continue
        if isinstance(curr, dict):
            curr = curr.get(part)
        elif isinstance(curr, list):
            try:
                idx = int(part)
                curr = curr[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return curr


class CollectorService:
    """Service to manage and execute agentic evidence collectors."""

    def create_collector(
        self,
        *,
        db: Session,
        user: User,
        name: str,
        collector_type: str,
        config: dict[str, Any],
        schedule: str | None = None,
        target_domain: str | None = None,
        document_id: str | None = None,
    ) -> EvidenceCollector:
        """Create a new evidence collector configuration."""
        valid_types = {"http", "sql", "script"}
        if collector_type not in valid_types:
            raise ValueError(f"Invalid collector type. Must be one of {valid_types}")

        collector = EvidenceCollector(
            user_id=user.id,
            name=name,
            collector_type=collector_type,
            config=config,
            schedule=schedule,
            target_domain=target_domain,
            document_id=document_id,
            is_active=True,
        )
        db.add(collector)
        commit_or_rollback(db)
        db.refresh(collector)
        logger.info("Created collector %s of type %s for user %s", collector.id, collector_type, user.id)
        return collector

    def list_collectors(self, *, db: Session, user: User) -> list[EvidenceCollector]:
        """List all active collectors for a user, or all if user is admin."""
        if (user.role or "").upper() == "ADMIN":
            return list(db.scalars(select(EvidenceCollector)).all())
        return list(
            db.scalars(
                select(EvidenceCollector).where(EvidenceCollector.user_id == user.id)
            ).all()
        )

    def delete_collector(self, *, db: Session, user: User, collector_id: str) -> None:
        """Delete an evidence collector."""
        collector = db.scalar(select(EvidenceCollector).where(EvidenceCollector.id == collector_id))
        if collector is None:
            raise ValueError("Collector not found.")

        if (user.role or "").upper() != "ADMIN" and collector.user_id != user.id:
            raise PermissionError("Access denied.")

        db.delete(collector)
        commit_or_rollback(db)
        logger.info("Deleted collector %s", collector_id)

    def run_collector(
        self,
        *,
        db: Session,
        user: User,
        collector_id: str,
    ) -> list[ExternalEvidence]:
        """Execute a collector synchronously, save and return retrieved evidence."""
        collector = db.scalar(select(EvidenceCollector).where(EvidenceCollector.id == collector_id))
        if collector is None:
            raise ValueError("Collector not found.")

        if (user.role or "").upper() != "ADMIN" and collector.user_id != user.id:
            raise PermissionError("Access denied.")

        collector.last_run_at = datetime.utcnow()
        results: list[ExternalEvidence] = []
        try:
            if collector.collector_type == "http":
                results = self._execute_http(collector)
            elif collector.collector_type == "sql":
                results = self._execute_sql(collector)
            elif collector.collector_type == "script":
                results = self._execute_script(collector)
            else:
                raise ValueError(f"Unknown collector type: {collector.collector_type}")

            collector.last_run_status = "success"
            
            # Save external evidence to database
            for evidence in results:
                evidence.collector_id = collector.id
                db.add(evidence)
            
            commit_or_rollback(db)
            logger.info("Collector %s ran successfully. Evidence count: %d", collector.id, len(results))
        except Exception as exc:
            db.rollback()
            collector.last_run_status = "failed"
            commit_or_rollback(db)
            logger.error("Collector %s execution failed: %s", collector.id, exc, exc_info=True)
            raise RuntimeError(f"Collector run failed: {exc}") from exc

        return results

    # ────────────────────────── Executors ────────────────────────────────────

    def _execute_http(self, collector: EvidenceCollector) -> list[ExternalEvidence]:
        """Execute an HTTP/REST collector."""
        import httpx

        config = collector.config
        url = config.get("url")
        method = config.get("method", "GET").upper()
        headers = dict(config.get("headers", {}))
        response_mapping = config.get("response_mapping", {})

        if not url:
            raise ValueError("URL is missing from HTTP collector config.")

        # Resolve environment variables in headers (e.g. ${VAR_NAME})
        for k, v in headers.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_var = v[2:-1]
                headers[k] = os.getenv(env_var, "")

        with httpx.Client(timeout=15.0) as client:
            if method == "GET":
                response = client.get(url, headers=headers)
            elif method == "POST":
                response = client.post(url, headers=headers, json=config.get("body"))
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code >= 400:
            raise RuntimeError(f"HTTP Server returned code {response.status_code}: {response.text}")

        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        # Apply response mappings
        evidence_text_path = response_mapping.get("evidence_text", "$.evidence_text")
        citation_label_path = response_mapping.get("citation_label", "$.citation_label")
        
        evidence_text = extract_value_by_path(data, evidence_text_path)
        citation_label = extract_value_by_path(data, citation_label_path)

        # Fallbacks if mappings didn't find anything
        if not evidence_text:
            evidence_text = str(data)[:2000]
        if not citation_label:
            citation_label = f"HTTP Evidence from {url}"

        evidence = ExternalEvidence(
            evidence_text=str(evidence_text),
            citation_label=str(citation_label),
            confidence_score=0.9,
            raw_payload=data,
            source_type="external_collector",
        )
        return [evidence]

    def _execute_sql(self, collector: EvidenceCollector) -> list[ExternalEvidence]:
        """Execute a SQL database query collector."""
        from sqlalchemy import create_engine

        config = collector.config
        db_url = config.get("db_url")
        query = config.get("query")
        response_mapping = config.get("response_mapping", {})

        if not db_url or not query:
            raise ValueError("db_url and query are required for SQL collector config.")

        # Resolve env var for db_url
        if db_url.startswith("${") and db_url.endswith("}"):
            db_url = os.getenv(db_url[2:-1], db_url)

        local_engine = create_engine(db_url)
        with local_engine.connect() as conn:
            result = conn.execute(text(query))
            rows = [dict(row._mapping) for row in result.all()]

        if not rows:
            return []

        evidences: list[ExternalEvidence] = []
        for i, row in enumerate(rows):
            evidence_text_path = response_mapping.get("evidence_text", "evidence_text")
            citation_label_path = response_mapping.get("citation_label", "citation_label")

            # Extract fields directly from row dict or path
            evidence_text = row.get(evidence_text_path) or extract_value_by_path(row, evidence_text_path)
            citation_label = row.get(citation_label_path) or extract_value_by_path(row, citation_label_path)

            if not evidence_text:
                evidence_text = json.dumps(row)
            if not citation_label:
                citation_label = f"SQL Evidence (row {i})"

            evidence = ExternalEvidence(
                evidence_text=str(evidence_text),
                citation_label=str(citation_label),
                confidence_score=0.85,
                raw_payload=row,
                source_type="external_collector",
            )
            evidences.append(evidence)

        return evidences

    def _execute_script(self, collector: EvidenceCollector) -> list[ExternalEvidence]:
        """Execute a custom Python script collector safely."""
        config = collector.config
        script_path = config.get("script_path")
        if not script_path or not os.path.exists(script_path):
            raise ValueError(f"Script path not found or invalid: {script_path}")

        # Execute script in sandbox/subprocess
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Script exit code {result.returncode}: {result.stderr}")

        try:
            data = json.loads(result.stdout)
        except Exception:
            data = {"stdout": result.stdout}

        response_mapping = config.get("response_mapping", {})
        evidence_text = extract_value_by_path(data, response_mapping.get("evidence_text", "evidence_text"))
        citation_label = extract_value_by_path(data, response_mapping.get("citation_label", "citation_label"))

        if not evidence_text:
            evidence_text = result.stdout[:2000]
        if not citation_label:
            citation_label = f"Script Evidence from {script_path}"

        evidence = ExternalEvidence(
            evidence_text=str(evidence_text),
            citation_label=str(citation_label),
            confidence_score=0.8,
            raw_payload=data,
            source_type="external_collector",
        )
        return [evidence]


collector_service = CollectorService()
