
from __future__ import annotations

from typing import List

from .schemas import TaskProfile, Candidate, AdmittedEvidence, EvidencePacket, SourceType
from .slots import item_matches_slot
from .valuation import value_candidates
from .packet import assemble_packet, update_packet_status


def contradiction_seeking_candidates(profile: TaskProfile, candidates: List[Candidate], admitted: List[AdmittedEvidence]) -> List[Candidate]:
    """
    Bidirectional conflict-pair seeking.

    If CAC has admitted subjective optimism, seek high-authority operational negatives.
    If CAC has admitted operational negatives, seek subjective CRM status if available.
    This makes contradiction handling an explicit evidence-pair behavior rather
    than a side-effect of chunk stuffing.
    """
    admitted_text = " ".join(ev.item.text.lower() for ev in admitted)
    has_positive = any(x in admitted_text for x in ["healthy", "green", "on track", "low risk", "likely renew", "approve", "approved", "minor", "optimistic", "strategic"])
    has_negative = any(x in admitted_text for x in ["overdue", "p1", "escalation", "late", "unresolved", "breach", "terminate", "cannot recommend", "blocked", "gap", "missing", "lost export", "root cause", "dispute", "uncured", "downtime", "failed", "risk"])
    if not has_positive and not has_negative:
        return []

    admitted_ids = {ev.item.source_id for ev in admitted}
    negative_terms = {"overdue", "p1", "escalation", "late", "unresolved", "breach", "terminate", "cannot recommend", "blocked", "gap", "missing", "lost export", "root cause", "dispute", "uncured", "downtime", "failed", "risk"}
    positive_terms = {"healthy", "green", "on track", "low risk", "likely renew", "approve", "approved", "minor", "optimistic", "strategic"}
    high_value_negative_types = {SourceType.BILLING, SourceType.SUPPORT, SourceType.CONTRACT, SourceType.EMAIL, SourceType.SECURITY, SourceType.INTERNAL_NOTE}
    out: list[Candidate] = []

    for c in candidates:
        item = c.item
        if item.source_id in admitted_ids:
            continue
        searchable = " ".join([item.text, item.title, " ".join(item.topics), " ".join(item.risk_tags)]).lower()

        if has_positive and not has_negative and item.source_type in high_value_negative_types:
            if any(t in searchable for t in negative_terms):
                out.append(c)

        if has_negative and not has_positive and item.source_type in {SourceType.CRM, SourceType.EMAIL, SourceType.INTERNAL_NOTE}:
            if any(t in searchable for t in positive_terms):
                out.append(c)

        if has_positive and has_negative:
            # Already paired; no additional contradiction-seeking candidates needed.
            continue

    return out


def expansion_loop(profile: TaskProfile, candidates: List[Candidate], packet: EvidencePacket, admitted: List[AdmittedEvidence]) -> EvidencePacket:
    remaining = profile.token_budget - packet.budget_used["context_tokens"]
    if remaining <= 20:
        return packet
    admitted_ids = {ev.item.source_id for ev in admitted}
    missing_candidates: list[Candidate] = []
    missing = set(packet.missing_slots)
    for c in candidates:
        if c.item.source_id in admitted_ids:
            continue
        if any(slot.name in missing and item_matches_slot(c.item, slot) for slot in profile.required_slots):
            missing_candidates.append(c)
    expansion_candidates = unique_candidates(missing_candidates + contradiction_seeking_candidates(profile, candidates, admitted))
    if not expansion_candidates:
        return packet
    expansion_profile = TaskProfile(
        task=profile.task + " targeted expansion for missing evidence slots and contradiction checks",
        entity=profile.entity,
        answer_target=profile.answer_target,
        token_budget=remaining,
        risk_profile=profile.risk_profile,
        required_slots=profile.required_slots,
        slot_mode=profile.slot_mode,
    )
    vals = value_candidates(expansion_profile, expansion_candidates, already_admitted=admitted)
    ep, new_admitted = assemble_packet(expansion_profile, vals, method=packet.method)
    packet.structured_facts.extend(ep.structured_facts)
    packet.summaries.extend(ep.summaries)
    packet.exact_evidence.extend(ep.exact_evidence)
    packet.excluded_evidence.extend(ep.excluded_evidence)
    packet.audit_trace.extend([{**a, "pass": "targeted_expansion"} for a in ep.audit_trace])
    packet.admitted.extend(new_admitted)
    packet.budget_used["context_tokens"] += ep.budget_used["context_tokens"]
    packet.budget_used["sources_admitted"] += ep.budget_used["sources_admitted"]
    update_packet_status(profile, packet)
    return packet


def unique_candidates(candidates: List[Candidate]) -> List[Candidate]:
    seen = set()
    out = []
    for c in candidates:
        if c.item.source_id in seen:
            continue
        seen.add(c.item.source_id)
        out.append(c)
    return out
