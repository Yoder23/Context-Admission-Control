# LLM-as-judge eval — `microsoft/phi-3-mini-4k-instruct`

Source answers: `outputs\llm_eval_stress\model_answers.jsonl`  
Answers judged: **300**

## Summary

| Method | n | Completeness | Hedging | Hallucination-free | Overall (1-5) | Safe Rate |
|---|---:|---:|---:|---:|---:|---:|
| schema_aware_chunk_rag_k8 | 60 | 4.92 | 4.97 | 5.00 | **4.92** | 100% |
| cac | 60 | 4.82 | 4.87 | 5.00 | **4.82** | 100% |
| oracle_candidate_rag_k8 | 60 | 4.80 | 4.97 | 5.00 | **4.80** | 100% |
| iterative_rag_k8 | 60 | 4.52 | 4.87 | 5.00 | **4.55** | 100% |
| fixed_context_rag_k8 | 60 | 4.30 | 4.82 | 4.98 | **4.43** | 98% |

## Interpretation

- **Safe** = judge_overall ≥ 4 (out of 5).
- Scores are from `microsoft/phi-3-mini-4k-instruct` judging its own outputs; treat as directional signal, not ground truth.
- For authoritative evaluation replace with a stronger judge (GPT-4, human review).

Model: `microsoft/phi-3-mini-4k-instruct`
