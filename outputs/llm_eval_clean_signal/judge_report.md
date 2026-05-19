# LLM-as-judge eval — `microsoft/phi-3-mini-4k-instruct`

Source answers: `outputs\llm_eval_clean_signal\model_answers.jsonl`  
Answers judged: **400**

## Summary

| Method | n | Completeness | Hedging | Hallucination-free | Overall (1-5) | Safe Rate |
|---|---:|---:|---:|---:|---:|---:|
| cac | 80 | 4.86 | 4.96 | 5.00 | **4.88** | 100% |
| schema_aware_chunk_rag_k8 | 80 | 4.84 | 4.92 | 5.00 | **4.84** | 100% |
| oracle_candidate_rag_k8 | 80 | 4.79 | 4.92 | 5.00 | **4.79** | 100% |
| fixed_context_rag_k8 | 80 | 4.66 | 4.89 | 4.99 | **4.69** | 100% |
| iterative_rag_k8 | 80 | 4.65 | 4.89 | 5.00 | **4.66** | 100% |

## Interpretation

- **Safe** = judge_overall ≥ 4 (out of 5).
- Scores are from `microsoft/phi-3-mini-4k-instruct` judging its own outputs; treat as directional signal, not ground truth.
- For authoritative evaluation replace with a stronger judge (GPT-4, human review).

Model: `microsoft/phi-3-mini-4k-instruct`
