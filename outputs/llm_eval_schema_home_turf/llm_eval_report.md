# Real-model LLM eval - `microsoft/phi-3-mini-4k-instruct`

Prompts evaluated: **400**

## Summary

| Method | n | LLM Score | Safe Rate | Missing Disclosure | Contradiction Handling |
|---|---:|---:|---:|---:|---:|
| cac | 80 | 0.8280 | 0.7625 | 1.0000 | 1.0000 |
| oracle_candidate_rag_k8 | 80 | 0.8109 | 0.5500 | 1.0000 | 1.0000 |
| schema_aware_chunk_rag_k8 | 80 | 0.7715 | 0.4250 | 1.0000 | 1.0000 |
| iterative_rag_k8 | 80 | 0.7193 | 0.1750 | 1.0000 | 0.9125 |
| fixed_context_rag_k8 | 80 | 0.6686 | 0.2125 | 0.9875 | 1.0000 |

## Interpretation

CAC scores **+0.0171** vs the best RAG baseline (oracle_candidate_rag_k8) on LLM answer quality.

### Boundaries

- LLM answer score is a lexical proxy (slot mentions, citation markers, hedging).
- For authoritative results, replace or supplement with a human or LLM judge.
- The same synthetic candidate pool is used; retriever quality is not tested.

Model: `microsoft/phi-3-mini-4k-instruct`
