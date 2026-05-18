# Real-model LLM eval — `microsoft/phi-3-mini-4k-instruct`

Prompts evaluated: **100**

## Summary

| Method | n | LLM Score | Safe Rate | Missing Disclosure | Contradiction Handling |
|---|---:|---:|---:|---:|---:|
| cac | 20 | 0.8157 | 0.6500 | 1.0000 | 1.0000 |
| oracle_candidate_rag_k8 | 20 | 0.8088 | 0.6000 | 1.0000 | 1.0000 |
| schema_aware_chunk_rag_k8 | 20 | 0.7832 | 0.4000 | 1.0000 | 1.0000 |
| iterative_rag_k8 | 20 | 0.7282 | 0.1500 | 1.0000 | 0.9000 |
| fixed_context_rag_k8 | 20 | 0.6608 | 0.2000 | 0.9500 | 1.0000 |

## Interpretation

CAC scores **+0.0069** vs the best RAG baseline (oracle_candidate_rag_k8) on LLM answer quality.

### Boundaries

- LLM answer score is a lexical proxy (slot mentions, citation markers, hedging).
- For authoritative results, replace or supplement with a human or LLM judge.
- The same synthetic candidate pool is used; retriever quality is not tested.

Model: `microsoft/phi-3-mini-4k-instruct`
