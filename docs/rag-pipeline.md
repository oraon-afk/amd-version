# RAG Pipeline

## Compliance Rule Ingestion

```text
PDF/text rule document
  -> parse
  -> clean text
  -> semantic chunking
  -> metadata extraction
  -> embedding
  -> Qdrant compliance_rules collection
  -> BM25 rule index
```

## Uploaded Document Processing

```text
User PDF/text upload
  -> temporary S3 object
  -> parse
  -> clean text
  -> semantic chunking
  -> embedding
  -> Qdrant audit_document_chunks collection
  -> expires_at metadata
```

## Hybrid Retrieval

```text
Compliance query
  -> vector search
  +  BM25 search
  -> result merge
  -> reranking
  -> metadata filtering
  -> context validation
  -> top relevant chunks
```

## Required Retrieval Techniques

- Semantic chunking
- Vector retrieval
- BM25 keyword retrieval
- Hybrid result merging
- Reranking
- Metadata filtering
- Citation tracking
- Confidence scoring
- Context validation

## Practical Defaults

```text
chunk size:      600 to 1,000 tokens
chunk overlap:   80 to 150 tokens
vector top k:    20 to 30
BM25 top k:      20 to 30
rerank top k:     5 to 8
```

## Grounding Rules

Generated findings must include:

- Matched rule citation
- Uploaded document evidence citation when available
- Explanation grounded in retrieved context
- Confidence score
- Risk level
- Recommendation

If retrieved context is weak, the system should mark the finding as low-confidence instead of inventing unsupported conclusions.

