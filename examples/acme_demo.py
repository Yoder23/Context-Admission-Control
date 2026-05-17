from __future__ import annotations

import json
from benchmarks.decision_risk.generate import generate_decision_dossiers
from benchmarks.decision_risk.profiles import build_task_profile
from benchmarks.decision_risk.score import score_packet_generic
from cac.core.builder import build_packet_from_candidates
from cac.core.retrieval import candidate_pool
from cac.core.reporting import packet_brief
from cac.baselines.naive_rag import fixed_context_rag, schema_aware_chunk_rag, oracle_candidate_rag


def main() -> None:
    dossier = generate_decision_dossiers(
        n=1,
        distractors=10,
        seed=7,
        task_types=["renewal_risk"],
        missing_rate=0.0,
        metadata_noise=0.05,
    )[0]
    profile = build_task_profile("renewal_risk", dossier.entity, budget=160)
    candidates = candidate_pool(profile, dossier.sources, max_candidates=32)
    packets = [
        build_packet_from_candidates(profile, candidates, method="cac"),
        schema_aware_chunk_rag(profile, candidates, k=8),
        oracle_candidate_rag(profile, candidates, k=8),
        fixed_context_rag(profile, candidates, k=8, method="fixed_context_rag_k8"),
    ]

    print(f"Dossier: {dossier.account_id} / {dossier.entity}")
    print(f"Candidates: {len(candidates)}")
    for packet in packets:
        print("\n===", packet.method, "===")
        print(json.dumps(packet_brief(packet), indent=2))
        print(json.dumps(score_packet_generic(dossier, packet), indent=2))
        if packet.audit_trace:
            print("Audit sample:")
            print(json.dumps(packet.audit_trace[:4], indent=2))


if __name__ == "__main__":
    main()
