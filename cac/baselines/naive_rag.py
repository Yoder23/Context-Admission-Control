from __future__ import annotations

from typing import List

from cac.core.schemas import TaskProfile, Candidate, EvidencePacket, AdmittedEvidence, Representation
from cac.core.packet import excerpt
from cac.core.slots import item_matches_slot, representation_satisfies_slot
from cac.core.valuation import metadata_distractor_signal


def fixed_context_rag(profile: TaskProfile, candidates: List[Candidate], k: int, method: str | None = None) -> EvidencePacket:
    chosen = candidates[:k]
    return _packet_from_chunks(profile, chosen, method or f"fixed_context_rag_k{k}")


def heuristic_rerank_rag(profile: TaskProfile, candidates: List[Candidate], k: int = 8) -> EvidencePacket:
    ranked = sorted(
        candidates,
        key=lambda c: (
            c.candidate_score * 1.1
            + c.item.authority * 0.8
            - min(0.6, c.item.freshness_days / 400.0)
            + (0.15 if c.item.source_type.value in {"contract", "billing", "support", "email"} else 0)
        ),
        reverse=True,
    )[:k]
    return _packet_from_chunks(profile, ranked, f"heuristic_rerank_rag_k{k}")


def metadata_aware_rag(profile: TaskProfile, candidates: List[Candidate], k: int = 8) -> EvidencePacket:
    """Slot-aware raw-chunk RAG baseline.

    This baseline gets access to the same task slot schema as CAC and uses it to
    rank raw chunks. It still admits full chunks only: no structured facts,
    summaries, exact-excerpt compression, missing-slot model, or representation
    selection. This tests whether CAC's advantage comes only from knowing the
    schema, versus from representation-aware evidence admission.
    """
    def score(c: Candidate) -> float:
        item = c.item
        matched = [slot for slot in profile.required_slots if item_matches_slot(item, slot)]
        slot_bonus = 0.65 * len(matched)
        exact_bonus = 0.0
        for slot in matched:
            if slot.exact_wording_required:
                # Full raw chunks preserve exact wording, but they pay full token cost.
                exact_bonus += 0.35
        authority_bonus = item.authority * 0.55
        freshness_penalty = min(0.35, item.freshness_days / 500.0)
        distractor_penalty = 0.75 if metadata_distractor_signal(item) else 0.0
        return c.candidate_score + slot_bonus + exact_bonus + authority_bonus - freshness_penalty - distractor_penalty

    ranked = sorted(candidates, key=score, reverse=True)[:k]
    return _packet_from_chunks(profile, ranked, f"metadata_aware_rag_k{k}")


def schema_aware_chunk_rag(profile: TaskProfile, candidates: List[Candidate], k: int = 8) -> EvidencePacket:
    """Schema-aware raw-chunk RAG baseline with missing-slot reporting.

    This is a stronger control than metadata_aware_rag:
    - It sees the same task evidence schema.
    - It ranks raw chunks by slot coverage, authority, freshness, and candidate score.
    - It admits raw full chunks only: no structured-fact compression, no summaries,
      no exact-excerpt-only representation, and no CAC cost-aware representation choice.
    - After admission, it reports missing slots based on schema matching, so CAC's
      missing-evidence advantage is not merely because RAG lacked a checklist.

    If CAC still wins, the advantage is representation-aware evidence admission,
    not just schema awareness.
    """
    ranked = sorted(candidates, key=lambda c: _schema_chunk_score(profile, c), reverse=True)[:k]
    return _packet_from_chunks(
        profile,
        ranked,
        f"schema_aware_chunk_rag_k{k}",
        schema_matches=True,
        report_missing_slots=True,
    )



def _polarity_signal(item) -> bool:
    hay = " ".join([item.title, item.text, " ".join(item.topics), " ".join(item.risk_tags)]).lower()
    return any(x in hay for x in [
        "healthy", "green", "on track", "low risk", "approve", "approved",
        "overdue", "p1", "escalation", "unresolved", "breach", "terminate",
        "cannot recommend", "blocked", "failed", "risk", "gap", "missing"
    ])

def _schema_chunk_score(profile: TaskProfile, c: Candidate) -> float:
    item = c.item
    matched = [slot for slot in profile.required_slots if item_matches_slot(item, slot)]
    exact_bonus = sum(0.45 for slot in matched if slot.exact_wording_required)
    coverage_bonus = 0.75 * len(matched)
    authority_bonus = 0.65 * item.authority
    freshness_penalty = min(0.35, item.freshness_days / 500.0)
    distractor_penalty = 0.90 if metadata_distractor_signal(item) else 0.0
    negative_or_positive_bonus = 0.18 if _polarity_signal(item) else 0.0
    return c.candidate_score + coverage_bonus + exact_bonus + authority_bonus + negative_or_positive_bonus - freshness_penalty - distractor_penalty


strong_reranked_rag = heuristic_rerank_rag


def _packet_from_chunks(profile: TaskProfile, chosen: List[Candidate], method: str, schema_matches: bool = False, report_missing_slots: bool = False) -> EvidencePacket:
    budgeted: list[Candidate] = []
    used = 0
    over_budget_tokens = 0
    for c in chosen:
        cost = c.item.token_cost
        if used + cost <= profile.token_budget:
            budgeted.append(c)
            used += cost
        elif not budgeted:
            # Fixed-context systems often include one over-budget chunk rather than returning nothing.
            # We track this explicitly so benchmark reports can account for it.
            budgeted.append(c)
            used += cost
            over_budget_tokens = max(0, used - profile.token_budget)
            break
    admitted = [
        AdmittedEvidence(
            item=c.item,
            representation=Representation.FULL_SOURCE_SPAN,
            slot_matches=[slot.name for slot in profile.required_slots if item_matches_slot(c.item, slot)] if schema_matches else [],
            token_cost=c.item.token_cost,
        )
        for c in budgeted
    ]
    packet = EvidencePacket(
        answer_target=profile.answer_target,
        entity=profile.entity,
        method=method,
        budget_used={
            "context_tokens": sum(ev.token_cost for ev in admitted),
            "candidate_sources_scanned": len(chosen),
            "sources_admitted": len(admitted),
            "over_budget_tokens": over_budget_tokens,
            "over_budget": over_budget_tokens > 0,
        },
        admitted=admitted,
    )
    for ev in admitted:
        packet.exact_evidence.append({
            "source": ev.item.source_id,
            "source_type": ev.item.source_type.value,
            "text": excerpt(ev.item.text),
            "fills_slots": ev.slot_matches,
        })
    text = " ".join(ev.item.text.lower() for ev in admitted)
    if any(x in text for x in ["healthy", "green", "on track"]) and any(x in text for x in ["overdue", "p1", "escalation", "cannot recommend", "breach", "terminate"]):
        packet.conflicts.append({"issue": "Possible contradiction in admitted chunks", "higher_authority_signal": "not resolved by fixed-context RAG"})
    if report_missing_slots:
        filled = set()
        for ev in admitted:
            for slot_name in ev.slot_matches:
                if representation_satisfies_slot(profile, slot_name, ev.representation):
                    filled.add(slot_name)
        packet.filled_slots = sorted(filled)
        packet.missing_slots = [slot.name for slot in profile.required_slots if slot.name not in filled]
        packet.uncertainties = [f"Required evidence slot not filled: {slot.name}. {slot.description}" for slot in profile.required_slots if slot.name not in filled]
    return packet


def oracle_candidate_rag(profile: TaskProfile, candidates: List[Candidate], k: int = 8) -> EvidencePacket:
    """Oracle-ish raw-chunk baseline using benchmark gold labels for candidate ordering."""
    ranked = sorted(candidates, key=lambda c: (
        2.5 * bool(c.item.gold_slots) + 0.7 * len(c.item.gold_slots) + 0.8 * c.item.authority
        + 0.4 * bool(c.item.gold_exact_required) + 0.3 * bool(c.item.gold_positive or c.item.gold_negative)
        - 1.2 * bool(c.item.is_distractor) - min(0.4, c.item.freshness_days / 500.0)
    ), reverse=True)[:k]
    return _packet_from_chunks(profile, ranked, f"oracle_candidate_rag_k{k}", schema_matches=True, report_missing_slots=True)


def long_context_rag(profile: TaskProfile, candidates: List[Candidate], k: int = 24) -> EvidencePacket:
    return _packet_from_chunks(profile, candidates[:k], f"long_context_rag_k{k}")


def iterative_rag(profile: TaskProfile, candidates: List[Candidate], k: int = 8) -> EvidencePacket:
    first = candidates[:max(2, k // 2)]
    selected = list(first)
    filled = set()
    for c in selected:
        for slot in profile.required_slots:
            if item_matches_slot(c.item, slot):
                filled.add(slot.name)
    for slot in profile.required_slots:
        if slot.name in filled:
            continue
        matches = [c for c in candidates if c not in selected and item_matches_slot(c.item, slot)]
        if matches:
            matches.sort(key=lambda c: (c.item.authority, -c.item.freshness_days, c.candidate_score), reverse=True)
            selected.append(matches[0])
        if len(selected) >= k:
            break
    return _packet_from_chunks(profile, selected[:k], f"iterative_rag_k{k}", schema_matches=True, report_missing_slots=True)
