from __future__ import annotations

"""Export same-candidate-pool answer prompts for external LLM evaluation.

This script does not call an LLM. It creates JSONL records that can be sent to any
answer model/judge later. It is included so v1.2 can move from deterministic
answer-readiness proxy to true same-model answer evaluation without changing the
benchmark generation or admitted contexts.
"""

import argparse, json
from pathlib import Path

from cac.core.retrieval import candidate_pool
from cac.core.builder import build_packet_from_candidates
from cac.baselines.naive_rag import (
    fixed_context_rag,
    schema_aware_chunk_rag,
    oracle_candidate_rag,
    iterative_rag,
)
from benchmarks.decision_risk.generate import generate_decision_dossiers
from benchmarks.decision_risk.profiles import TASKS, build_task_profile


def packet_context(packet) -> str:
    parts = []
    for ev in packet.admitted:
        slots = ",".join(ev.slot_matches) if ev.slot_matches else "unmapped"
        parts.append(
            f"SOURCE={ev.item.source_id}\nTYPE={ev.item.source_type.value}\nREP={ev.representation.value}\nSLOTS={slots}\nTEXT={ev.item.text}"
        )
    if packet.missing_slots:
        parts.append("MISSING_SLOTS=" + ",".join(packet.missing_slots))
    if packet.conflicts:
        parts.append("CONFLICTS=" + json.dumps(packet.conflicts))
    return "\n\n".join(parts)


def make_prompt(task_type: str, entity: str, context: str) -> str:
    return f"""You are evaluating an evidence-sensitive enterprise decision.

Task type: {task_type}
Entity: {entity}

Use only the provided evidence. If required evidence is missing, say so explicitly.
Preserve exact wording when legal/security/commitment language matters.
Surface contradictions and cite source IDs.

Evidence context:
{context}

Write a concise decision answer with:
1. Decision
2. Supporting evidence with source IDs
3. Contradictions
4. Missing evidence / uncertainty
5. Recommended next action
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--budget", type=int, default=160)
    ap.add_argument("--distractors", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path, default=Path("outputs/llm_eval_prompts.jsonl"))
    args = ap.parse_args()

    methods = {
        "cac": lambda profile, candidates: build_packet_from_candidates(profile, candidates, method="cac"),
        "fixed_context_rag_k8": lambda profile, candidates: fixed_context_rag(profile, candidates, 8, "fixed_context_rag_k8"),
        "schema_aware_chunk_rag_k8": lambda profile, candidates: schema_aware_chunk_rag(profile, candidates, 8),
        "oracle_candidate_rag_k8": lambda profile, candidates: oracle_candidate_rag(profile, candidates, 8),
        "iterative_rag_k8": lambda profile, candidates: iterative_rag(profile, candidates, 8),
    }

    dossiers = generate_decision_dossiers(args.n, args.distractors, args.seed, list(TASKS))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for dossier in dossiers:
            task_type = next(t for t in TASKS if dossier.account_id.startswith(t[:3]))
            profile = build_task_profile(task_type, dossier.entity, args.budget)
            candidates = candidate_pool(profile, dossier.sources, max_candidates=32)
            for method, fn in methods.items():
                packet = fn(profile, candidates)
                rec = {
                    "account_id": dossier.account_id,
                    "task_type": task_type,
                    "method": method,
                    "budget": args.budget,
                    "distractors": args.distractors,
                    "prompt": make_prompt(task_type, dossier.entity, packet_context(packet)),
                    "gold_present_slots": dossier.present_gold_slots,
                    "gold_missing_slots": dossier.missing_gold_slots,
                    "has_contradiction": dossier.has_contradiction,
                }
                f.write(json.dumps(rec) + "\n")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
