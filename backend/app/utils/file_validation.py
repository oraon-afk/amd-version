from pathlib import Path

from fastapi import HTTPException, status

from backend.app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".text", ".docx"}


def validate_upload_file(*, filename: str, content_type: str, content: bytes) -> None:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOCX, and text files are supported.",
        )

    extension_content_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".text": "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    allowed_for_extension = extension_content_types.get(extension)
    configured_types = {item.strip().lower() for item in settings.allowed_file_type_list}
    normalized_content_type = content_type.split(";", 1)[0].strip().lower()
    extension_aliases = {extension, extension.lstrip(".")}
    if (
        normalized_content_type not in configured_types
        and (allowed_for_extension or "").lower() not in configured_types
        and not (extension_aliases & configured_types)
        and content_type not in {"application/octet-stream", "binary/octet-stream"}
        and allowed_for_extension is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {content_type}",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload size of {settings.max_upload_mb} MB.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
