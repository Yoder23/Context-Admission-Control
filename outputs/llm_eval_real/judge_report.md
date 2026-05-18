# LLM-as-judge eval — `microsoft/phi-3-mini-4k-instruct`

Source answers: `outputs\llm_eval_real\model_answers.jsonl`  
Answers judged: **100**

## Summary

| Method | n | Completeness | Hedging | Hallucination-free | Overall (1-5) | Safe Rate |
|---|---:|---:|---:|---:|---:|---:|
| cac | 20 | 4.80 | 4.95 | 5.00 | **4.85** | 100% |
| schema_aware_chunk_rag_k8 | 20 | 4.80 | 4.90 | 5.00 | **4.80** | 100% |
| oracle_candidate_rag_k8 | 20 | 4.75 | 4.75 | 5.00 | **4.75** | 100% |
| iterative_rag_k8 | 20 | 4.55 | 4.95 | 5.00 | **4.55** | 100% |
| fixed_context_rag_k8 | 20 | 4.40 | 4.85 | 5.00 | **4.45** | 100% |

## Interpretation

- **Safe** = judge_overall ≥ 4 (out of 5).
- Scores are from `microsoft/phi-3-mini-4k-instruct` judging its own outputs; treat as directional signal, not ground truth.
- For authoritative evaluation replace with a stronger judge (GPT-4, human review).

Model: `microsoft/phi-3-mini-4k-instruct`
