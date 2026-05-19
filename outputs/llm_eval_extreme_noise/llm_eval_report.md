# Real-model LLM eval - `microsoft/phi-3-mini-4k-instruct`

Prompts evaluated: **400**

## Summary

| Method | n | LLM Score | Safe Rate | Missing Disclosure | Contradiction Handling |
|---|---:|---:|---:|---:|---:|
| cac | 80 | 0.8067 | 0.5750 | 1.0000 | 1.0000 |
| oracle_candidate_rag_k8 | 80 | 0.7560 | 0.3625 | 1.0000 | 1.0000 |
| schema_aware_chunk_rag_k8 | 80 | 0.7522 | 0.3375 | 1.0000 | 1.0000 |
| iterative_rag_k8 | 80 | 0.7483 | 0.3000 | 1.0000 | 0.9000 |
| fixed_context_rag_k8 | 80 | 0.6452 | 0.0000 | 1.0000 | 0.9625 |

## Interpretation

CAC scores **+0.0507** vs the best RAG baseline (oracle_candidate_rag_k8) on LLM answer quality.

### Boundaries

- LLM answer score is a lexical proxy (slot mentions, citation markers, hedging).
- For authoritative results, replace or supplement with a human or LLM judge.
- The same synthetic candidate pool is used; retriever quality is not tested.

Model: `microsoft/phi-3-mini-4k-instruct`
