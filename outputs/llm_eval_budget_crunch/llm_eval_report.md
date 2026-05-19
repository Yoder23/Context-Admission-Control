# Real-model LLM eval - `microsoft/phi-3-mini-4k-instruct`

Prompts evaluated: **300**

## Summary

| Method | n | LLM Score | Safe Rate | Missing Disclosure | Contradiction Handling |
|---|---:|---:|---:|---:|---:|
| cac | 60 | 0.8327 | 0.7000 | 1.0000 | 1.0000 |
| oracle_candidate_rag_k8 | 60 | 0.8032 | 0.5500 | 1.0000 | 0.9833 |
| schema_aware_chunk_rag_k8 | 60 | 0.7876 | 0.5000 | 1.0000 | 1.0000 |
| iterative_rag_k8 | 60 | 0.7498 | 0.3000 | 1.0000 | 0.9167 |
| fixed_context_rag_k8 | 60 | 0.6376 | 0.0333 | 1.0000 | 1.0000 |

## Interpretation

CAC scores **+0.0295** vs the best RAG baseline (oracle_candidate_rag_k8) on LLM answer quality.

### Boundaries

- LLM answer score is a lexical proxy (slot mentions, citation markers, hedging).
- For authoritative results, replace or supplement with a human or LLM judge.
- The same synthetic candidate pool is used; retriever quality is not tested.

Model: `microsoft/phi-3-mini-4k-instruct`
