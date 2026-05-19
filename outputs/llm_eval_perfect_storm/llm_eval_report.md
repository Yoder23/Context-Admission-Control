# Real-model LLM eval - `microsoft/phi-3-mini-4k-instruct`

Prompts evaluated: **300**

## Summary

| Method | n | LLM Score | Safe Rate | Missing Disclosure | Contradiction Handling |
|---|---:|---:|---:|---:|---:|
| cac | 60 | 0.8053 | 0.6000 | 1.0000 | 1.0000 |
| oracle_candidate_rag_k8 | 60 | 0.7808 | 0.5167 | 0.9833 | 1.0000 |
| iterative_rag_k8 | 60 | 0.7629 | 0.3500 | 1.0000 | 0.9333 |
| schema_aware_chunk_rag_k8 | 60 | 0.7480 | 0.3667 | 1.0000 | 1.0000 |
| fixed_context_rag_k8 | 60 | 0.6307 | 0.0333 | 1.0000 | 1.0000 |

## Interpretation

CAC scores **+0.0245** vs the best RAG baseline (oracle_candidate_rag_k8) on LLM answer quality.

### Boundaries

- LLM answer score is a lexical proxy (slot mentions, citation markers, hedging).
- For authoritative results, replace or supplement with a human or LLM judge.
- The same synthetic candidate pool is used; retriever quality is not tested.

Model: `microsoft/phi-3-mini-4k-instruct`
