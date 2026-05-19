# Real-model LLM eval - `microsoft/phi-3-mini-4k-instruct`

Prompts evaluated: **300**

## Summary

| Method | n | LLM Score | Safe Rate | Missing Disclosure | Contradiction Handling |
|---|---:|---:|---:|---:|---:|
| oracle_candidate_rag_k8 | 60 | 0.8030 | 0.6000 | 0.9833 | 1.0000 |
| cac | 60 | 0.7857 | 0.4833 | 0.9833 | 1.0000 |
| schema_aware_chunk_rag_k8 | 60 | 0.7827 | 0.4833 | 1.0000 | 1.0000 |
| iterative_rag_k8 | 60 | 0.7782 | 0.4167 | 1.0000 | 0.9833 |
| fixed_context_rag_k8 | 60 | 0.6513 | 0.0500 | 1.0000 | 0.9833 |

## Interpretation

Best RAG baseline (oracle_candidate_rag_k8) scores **+0.0173** above CAC on LLM answer quality.

### Boundaries

- LLM answer score is a lexical proxy (slot mentions, citation markers, hedging).
- For authoritative results, replace or supplement with a human or LLM judge.
- The same synthetic candidate pool is used; retriever quality is not tested.

Model: `microsoft/phi-3-mini-4k-instruct`
