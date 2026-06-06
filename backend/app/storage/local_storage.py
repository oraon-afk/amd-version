from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from backend.app.core.config import settings


@dataclass(frozen=True)
class LocalStoredObject:
    key: str
    uri: str
    path: Path
    size_bytes: int


class LocalStorage:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.storage_root)

    def save_temp_file(
        self,
        *,
        user_id: str,
        document_id: str,
        filename: str,
        content: bytes,
    ) -> LocalStoredObject:
        return self._save(
            area=settings.storage_temp_dir,
            owner_id=user_id,
            document_id=document_id,
            filename=filename,
            content=content,
        )

    def save_rule_file(
        self,
        *,
        user_id: str,
        document_id: str,
        filename: str,
        content: bytes,
        document_type: str,
    ) -> LocalStoredObject:
        area = self._area_for_rule_type(document_type)
        return self._save(
            area=area,
            owner_id=user_id,
            document_id=document_id,
            filename=filename,
            content=content,
        )

    def read_uri_bytes(self, uri: str) -> bytes:
        if not uri.startswith("local://"):
            raise ValueError(f"Unsupported local storage URI: {uri}")
        return self.resolve_uri(uri).read_bytes()

    def delete_uri(self, uri: str | None) -> bool:
        if not uri or not uri.startswith("local://"):
            return False
        path = self.resolve_uri(uri)
        if not path.exists():
            return False
        if path.is_dir():
            rmtree(path)
        else:
            path.unlink()
            self._remove_empty_parents(path.parent)
        return True

    def delete_temp_uri(self, uri: str | None) -> bool:
        if not uri or not uri.startswith("local://"):
            return False
        path = self.resolve_uri(uri)
        temp_root = self._safe_root() / settings.storage_temp_dir
        if not self._is_relative_to(path, temp_root):
            return False
        return self.delete_uri(uri)

    def resolve_uri(self, uri: str) -> Path:
        relative = uri.removeprefix("local://").replace("\\", "/").lstrip("/")
        path = (self._safe_root() / relative).resolve()
        if not self._is_relative_to(path, self._safe_root()):
            raise ValueError("Resolved storage path escapes storage root.")
        return path

    def storage_summary(self) -> dict[str, dict[str, int]]:
        root = self._safe_root()
        summary: dict[str, dict[str, int]] = {}
        for area in (
            settings.storage_temp_dir,
            settings.storage_rules_dir,
            settings.storage_compliance_dir,
            settings.storage_policies_dir,
        ):
            area_path = root / area
            file_count = 0
            total_bytes = 0
            if area_path.exists():
                for path in area_path.rglob("*"):
                    if path.is_file():
                        file_count += 1
                        total_bytes += path.stat().st_size
            summary[area] = {"files": file_count, "bytes": total_bytes}
        return summary

    def _save(
        self,
        *,
        area: str,
        owner_id: str,
        document_id: str,
        filename: str,
        content: bytes,
    ) -> LocalStoredObject:
        safe_name = self._safe_filename(filename)
        relative = Path(area) / owner_id / document_id / safe_name
        path = (self._safe_root() / relative).resolve()
        if not self._is_relative_to(path, self._safe_root()):
            raise ValueError("Storage path escapes storage root.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        key = relative.as_posix()
        return LocalStoredObject(key=key, uri=f"local://{key}", path=path, size_bytes=len(content))

    def _safe_root(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root.resolve()

    def _remove_empty_parents(self, path: Path) -> None:
        root = self._safe_root()
        while path != root and self._is_relative_to(path, root):
            try:
                path.rmdir()
            except OSError:
                break
            path = path.parent

    @staticmethod
    def _safe_filename(filename: str) -> str:
        clean = Path(filename).name.strip().replace("\\", "_").replace("/", "_")
        return clean or f"document-{uuid4()}"

    @staticmethod
    def _area_for_rule_type(document_type: str) -> str:
        normalized = document_type.strip().lower().replace("_", "-")
        if normalized in {"compliance", "compliance-rule", "compliance-rules"}:
            return settings.storage_compliance_dir
        if normalized in {"policy", "policies", "internal-policy", "internal-policies"}:
            return settings.storage_policies_dir
        return settings.storage_rules_dir

    @staticmethod
    def _is_relative_to(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False


local_storage = LocalStorage()
