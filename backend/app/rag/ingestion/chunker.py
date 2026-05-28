from __future__ import annotations

from hashlib import sha1

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:  # pragma: no cover - dependency is declared, fallback keeps startup diagnosable.
    RecursiveCharacterTextSplitter = None

from backend.app.core.config import settings
from backend.app.rag.ingestion.metadata_extractor import infer_section_title, make_citation_label


def chunk_pages(
    *,
    pages: list[dict],
    document_id: str,
    filename: str,
    source_type: str,
    extra_metadata: dict | None = None,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[dict]:
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap
    if overlap >= chunk_size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    chunks: list[dict] = []
    metadata = extra_metadata or {}

    for page in pages:
        page_number = int(page["page_number"])
        text = str(page["text"]).strip()
        if not text:
            continue

        section_title = infer_section_title(text)
        split_texts = _recursive_split(text, chunk_size=chunk_size, overlap=overlap)
        for chunk_index, chunk_text in enumerate(split_texts):
            if not chunk_text:
                continue

            text_hash = sha1(chunk_text.encode("utf-8")).hexdigest()[:12]
            chunk_id = f"{document_id}:p{page_number}:c{chunk_index}:{text_hash}"
            chunks.append(
                {
                    **metadata,
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "filename": filename,
                    "source_type": source_type,
                    "page_number": page_number,
                    "section": section_title,
                    "section_title": section_title,
                    "chunk_index": chunk_index,
                    "text_hash": text_hash,
                    "text": chunk_text,
                    "citation_label": make_citation_label(
                        filename=filename,
                        page_number=page_number,
                        section_title=section_title,
                    ),
                },
            )

    return chunks


def _recursive_split(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    if RecursiveCharacterTextSplitter is not None:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
        )
        return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]

    words = text.split()
    step = chunk_size - overlap
    chunks = []
    for start in range(0, len(words), step):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(words):
            break
    return chunks
