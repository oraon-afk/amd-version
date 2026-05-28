from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.config import settings
from backend.app.rag.retrieval.context_validator import context_validator
from backend.app.rag.retrieval.hybrid_retriever import HybridRetriever, hybrid_retriever
from backend.app.rag.retrieval.types import RetrievalResult

# Boilerplate / metadata tokens commonly found in document headers that
# add noise to the compliance query without carrying policy content.
_HEADER_NOISE: frozenset[str] = frozenset(
    {
        "version",
        "confidential",
        "copyright",
        "rights",
        "reserved",
        "table",
        "contents",
        "section",
        "page",
        "draft",
        "revision",
        "document",
        "title",
        "author",
        "date",
        "approved",
        "classification",
    }
)


@dataclass
class RetrievalOutput:
    query: str
    results: list[RetrievalResult]
    has_enough_context: bool


class RetrievalAgent:
    def __init__(self, retriever: HybridRetriever = hybrid_retriever) -> None:
        self.retriever = retriever

    def retrieve_rules(
        self,
        *,
        document_text: str,
        domain: str | None = None,
        rule_set_id: str | None = None,
        audit_id: str | None = None,
        document_id: str | None = None,
    ) -> RetrievalOutput:
        query = self._build_compliance_query(document_text)

        # Build filters only for keys that have an actual value so an empty
        # string does not silently drop a filter condition.
        filters: dict[str, str] = {}
        if rule_set_id:
            filters["rule_set_id"] = rule_set_id
        if domain:
            filters["domain"] = domain
        filters["source_type"] = "compliance_rule"

        results = self.retriever.search(
            collection_name=settings.qdrant_rule_collection,
            query=query,
            filters=filters if filters else None,
            final_top_k=settings.final_top_k,
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
        )
        if not results and domain:
            relaxed_filters = {key: value for key, value in filters.items() if key != "domain"}
            results = self.retriever.search(
                collection_name=settings.qdrant_rule_collection,
                query=query,
                filters=relaxed_filters,
                final_top_k=settings.final_top_k,
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
            )
        if not results and filters.get("source_type"):
            relaxed_filters = {
                key: value for key, value in filters.items() if key not in {"domain", "source_type"}
            }
            results = self.retriever.search(
                collection_name=settings.qdrant_rule_collection,
                query=query,
                filters=relaxed_filters or None,
                final_top_k=settings.final_top_k,
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
            )
        return RetrievalOutput(
            query=query,
            results=results,
            has_enough_context=context_validator.has_enough_context(results),
        )

    @staticmethod
    def _build_compliance_query(document_text: str) -> str:
        """
        Select the 350 most content-bearing words from the document rather
        than blindly taking the first 350 words, which are often dominated by
        boilerplate headers and metadata that mislead the vector search.

        Strategy:
        1. Split the full text into words.
        2. Skip any word that is a known header-noise token (case-insensitive).
        3. Skip very short words (≤ 2 chars) and purely numeric tokens.
        4. Collect up to 350 words in document order and join them.

        If the filtered set is too small (fewer than 50 words), fall back to
        the raw first-350-word approach so we never return an empty query.
        """
        words = document_text.split()
        filtered: list[str] = []
        for word in words:
            clean = word.strip(".,;:()[]\"'").lower()
            if len(clean) <= 2:
                continue
            if clean.isnumeric():
                continue
            if clean in _HEADER_NOISE:
                continue
            filtered.append(word)
            if len(filtered) >= 350:
                break

        if len(filtered) < 50:
            # Fallback: document may be short or purely numeric — use raw head.
            return " ".join(words[:350])

        return " ".join(filtered)


retrieval_agent = RetrievalAgent()
