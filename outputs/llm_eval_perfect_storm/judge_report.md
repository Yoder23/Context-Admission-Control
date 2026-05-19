# LLM-as-judge eval — `microsoft/phi-3-mini-4k-instruct`

Source answers: `outputs\llm_eval_perfect_storm\model_answers.jsonl`  
Answers judged: **300**

## Summary

| Method | n | Completeness | Hedging | Hallucination-free | Overall (1-5) | Safe Rate |
|---|---:|---:|---:|---:|---:|---:|
| cac | 60 | 4.72 | 4.95 | 5.00 | **4.72** | 100% |
| oracle_candidate_rag_k8 | 60 | 4.57 | 4.92 | 4.98 | **4.58** | 100% |
| schema_aware_chunk_rag_k8 | 60 | 4.38 | 4.83 | 4.90 | **4.52** | 100% |
| iterative_rag_k8 | 60 | 4.27 | 4.80 | 4.97 | **4.43** | 98% |
| fixed_context_rag_k8 | 60 | 4.23 | 4.90 | 5.00 | **4.32** | 100% |

## Interpretation

- **Safe** = judge_overall ≥ 4 (out of 5).
- Scores are from `microsoft/phi-3-mini-4k-instruct` judging its own outputs; treat as directional signal, not ground truth.
- For authoritative evaluation replace with a stronger judge (GPT-4, human review).

Model: `microsoft/phi-3-mini-4k-instruct`
