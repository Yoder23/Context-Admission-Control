# LLM-as-judge eval — `microsoft/phi-3-mini-4k-instruct`

Source answers: `outputs\llm_eval_extreme_noise\model_answers.jsonl`  
Answers judged: **400**

## Summary

| Method | n | Completeness | Hedging | Hallucination-free | Overall (1-5) | Safe Rate |
|---|---:|---:|---:|---:|---:|---:|
| cac | 80 | 4.76 | 4.94 | 5.00 | **4.76** | 100% |
| schema_aware_chunk_rag_k8 | 80 | 4.62 | 4.94 | 5.00 | **4.64** | 100% |
| oracle_candidate_rag_k8 | 80 | 4.59 | 4.90 | 5.00 | **4.60** | 100% |
| iterative_rag_k8 | 80 | 4.45 | 4.91 | 4.99 | **4.54** | 100% |
| fixed_context_rag_k8 | 80 | 4.22 | 4.76 | 4.96 | **4.40** | 95% |

## Interpretation

- **Safe** = judge_overall ≥ 4 (out of 5).
- Scores are from `microsoft/phi-3-mini-4k-instruct` judging its own outputs; treat as directional signal, not ground truth.
- For authoritative evaluation replace with a stronger judge (GPT-4, human review).

Model: `microsoft/phi-3-mini-4k-instruct`
