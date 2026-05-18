# Real-model LLM eval — `microsoft/phi-3-mini-4k-instruct`

Prompts evaluated: **300**

## Summary

| Method | n | LLM Score | Safe Rate | Missing Disclosure | Contradiction Handling |
|---|---:|---:|---:|---:|---:|
| cac | 60 | 0.8242 | 0.6333 | 1.0000 | 1.0000 |
| oracle_candidate_rag_k8 | 60 | 0.7975 | 0.4833 | 1.0000 | 1.0000 |
| schema_aware_chunk_rag_k8 | 60 | 0.7406 | 0.2667 | 1.0000 | 1.0000 |
| iterative_rag_k8 | 60 | 0.7334 | 0.2167 | 1.0000 | 0.9167 |
| fixed_context_rag_k8 | 60 | 0.6513 | 0.0000 | 1.0000 | 0.9833 |

## Interpretation

CAC scores **+0.0267** vs the best RAG baseline (oracle_candidate_rag_k8) on LLM answer quality.

### Boundaries

- LLM answer score is a lexical proxy (slot mentions, citation markers, hedging).
- For authoritative results, replace or supplement with a human or LLM judge.
- The same synthetic candidate pool is used; retriever quality is not tested.

Model: `microsoft/phi-3-mini-4k-instruct`
