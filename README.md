# Context Admission Control (CAC) v1.4

Context Admission Control is a benchmarked context-control strategy for
evidence-sensitive enterprise decisions. The core idea is simple:

> RAG optimizes chunk relevance. CAC optimizes evidence sufficiency under budget.

This repository contains DecisionRiskBench v1.4, a synthetic benchmark artifact
for comparing CAC evidence packets against chunk-stuffing RAG baselines under
same-candidate-pool conditions.

## Supported Claim

Supported by the packaged synthetic benchmark:

> On DecisionRiskBench v1.4, CAC has the strongest aggregate decision-grade
> behavior, deterministic answer-readiness behavior, distractor control,
> exact-clause preservation, contradiction recall, and per-task decision-grade
> score among the included methods.

Not supported by this repository:

```text
RAG is dead in production.
CAC beats every conceivable RAG stack.
Human users prefer CAC.
Real LLM answers have been shown to improve from CAC packets.
This synthetic benchmark proves production performance.
This repository is production proof.
```

The right publication line is:

> Chunk relevance is not the same thing as evidence sufficiency under budget.

## What Is Included

- `cac/`: CAC packet-building, valuation, slot matching, and retrieval helpers.
- `cac/baselines/`: fixed, heuristic, metadata-aware, schema-aware, iterative,
  long-context, and oracle candidate RAG baselines.
- `benchmarks/decision_risk/`: DecisionRiskBench v1.4 generator, scorer, report
  writer, plot writer, prompt export, and external answer-evaluation harness.
- `benchmarks/decision_risk_human_rewrite/`: semi-synthetic surface rewrite
  suite that perturbs text and observable metadata.
- `benchmarks/decision_risk_stress/`: stress suite for contradiction misses,
  slot underfill, exact-representation failures, and distractor pressure.
- `outputs/`: packaged reference outputs for the v1.4 runs.

## Headline Reference Result

Packaged run:

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.run \
  --n 20 \
  --budgets 40,60,80,120,160,240,500 \
  --distractors 5,25,50 \
  --output-dir outputs/decision_risk_v1_4_n20
```

Shape:

```text
20 accounts x 4 tasks x 7 budgets x 3 distractor levels x 8 methods = 13,440 rows
```

Aggregate decision-grade results from the packaged output:

| Method | Avg Tokens | Decision Grade | Generated-Answer Proxy | Distractor Rate | Exact Clause | Contradiction Recall |
|---|---:|---:|---:|---:|---:|---:|
| cac | 60.1583 | 0.8101 | 0.8556 | 0.0464 | 0.9750 | 0.6280 |
| schema_aware_chunk_rag_k8 | 85.2643 | 0.6892 | 0.7366 | 0.2923 | 0.8923 | 0.2101 |
| iterative_rag_k8 | 69.6815 | 0.6876 | 0.7374 | 0.2344 | 0.8083 | 0.2458 |
| oracle_candidate_rag_k8 | 87.2554 | 0.6794 | 0.7455 | 0.2750 | 0.9524 | 0.1815 |
| metadata_aware_rag_k8 | 85.1798 | 0.6717 | 0.7106 | 0.2923 | 0.8869 | 0.2101 |
| heuristic_rerank_rag_k8 | 87.8994 | 0.6403 | 0.6892 | 0.3393 | 0.8652 | 0.1649 |
| long_context_rag_k24 | 126.6375 | 0.6046 | 0.6270 | 0.5209 | 0.7438 | 0.2458 |
| fixed_context_rag_k8 | 86.4607 | 0.5934 | 0.6310 | 0.4445 | 0.6997 | 0.2458 |

## Important Benchmark Boundary

DecisionRiskBench v1.4 tests context-control strategy, not retriever quality.
All compared methods use the same candidate pool. CAC can admit compact evidence
representations such as structured facts, summaries, and exact excerpts. RAG
baselines admit raw chunks.

That distinction is intentional: CAC is being evaluated as evidence admission
rather than chunk stuffing. It is also the largest methodological caveat, and
stronger future baselines should include compression-aware and answer-aware RAG.

## Deterministic Answer Proxy

The generated-answer metric is a deterministic answer-readiness proxy. It uses
benchmark labels during deterministic answer generation and scoring. It is not an LLM answer study and it is not a human preference study.

The next empirical milestone is:

```text
RAG chunks -> same LLM -> answer
CAC evidence packet -> same LLM -> answer
human or LLM judge -> score
```

This repository includes prompt export and answer scoring scaffolding for that
next step, but it does not include real model outputs.

## No-Gold-Admission Boundary

`SourceItem` carries benchmark gold fields for scoring and for the explicit
oracle baseline. Tests assert that CAC core and non-oracle RAG baselines do not
read these scorer-only fields:

```text
gold_slots
gold_negative
gold_positive
gold_exact_required
is_distractor
```

## Quickstart

Use Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
pytest -q
PYTHONPATH=. python tests/run_smoke_tests.py
PYTHONPATH=. python examples/acme_demo.py
```

On Windows PowerShell, use:

```powershell
$env:PYTHONPATH='.'
C:\Python310\python.exe -m pytest -q
```

## Reproduce The Main Suites

Main DecisionRiskBench suite:

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.run \
  --n 20 \
  --budgets 40,60,80,120,160,240,500 \
  --distractors 5,25,50 \
  --output-dir outputs/decision_risk_v1_4_n20
```

Semi-synthetic rewrite suite:

```bash
PYTHONPATH=. python -m benchmarks.decision_risk_human_rewrite.run \
  --n 8 \
  --budgets 40,60,80,120,160,240 \
  --distractors 25,50 \
  --metadata-noise 0.18 \
  --output-dir outputs/decision_risk_v1_4_rewrite
```

Failure-stress suite:

```bash
PYTHONPATH=. python -m benchmarks.decision_risk_stress.run \
  --n 8 \
  --budgets 40,60,80,120,160 \
  --distractors 50,100 \
  --metadata-noise 0.30 \
  --output-dir outputs/decision_risk_v1_4_stress
```

External LLM prompt export:

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.export_llm_eval_prompts \
  --n 5 \
  --budget 160 \
  --distractors 25 \
  --output outputs/llm_eval_v1_4/prompts.jsonl
```

After filling a JSONL file with model answers:

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.llm_eval \
  --answers outputs/llm_eval_v1_4/model_answers.jsonl \
  --output-dir outputs/llm_eval_v1_4_eval
```

## Release Notes

See `CHANGELOG.md` for release history and `RELEASE_CHECKLIST.md` for the
verification gates used before publishing.

## License

MIT. See `LICENSE`.
