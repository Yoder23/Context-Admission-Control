
from __future__ import annotations

from typing import List, Optional

from .schemas import (
    SourceItem, SourceType, Representation, TaskProfile, Candidate, CandidateValuation,
    AdmittedEvidence
)
from .slots import matched_slots
from .retrieval import keyword_overlap_score


def metadata_distractor_signal(item: SourceItem) -> bool:
    """Heuristic available from source-map metadata, not benchmark gold labels."""
    hay = " ".join([item.title, item.text, " ".join(item.topics), " ".join(item.risk_tags)]).lower()
    return (
        item.source_type == SourceType.SLACK and item.authority < 0.45
    ) or any(token in hay for token in [
        "distractor", "speculation", "generic_contract", "unrelated", "old positive",
        "stale_positive_signal", "commercially reasonable",
    ])


def freshness_score(freshness_days: int) -> float:
    return max(0.15, min(1.0, 1.0 / (1.0 + freshness_days / 120.0)))


def contradiction_potential(item: SourceItem) -> float:
    text = item.text.lower()
    topics = set(t.lower() for t in item.topics + item.risk_tags)
    signals = 0.0
    if any(x in text for x in ["healthy", "green", "low risk", "on track", "likely renew", "approve", "approved", "minor", "optimistic", "strategic"]):
        signals += 0.25
    if any(x in text for x in ["overdue", "escalation", "p1", "breach", "terminate", "late", "unhappy", "cannot recommend", "blocked", "gap", "missing", "lost export", "root cause", "dispute", "uncured", "downtime", "failed", "risk"]):
        signals += 0.45
    if {"crm", "support", "billing"} & topics:
        signals += 0.10
    return min(1.0, signals)


def task_criticality(item: SourceItem, profile: TaskProfile) -> float:
    critical = 0.0
    slot_count = len(matched_slots(item, profile))
    if slot_count:
        critical += min(0.55, 0.22 * slot_count)
    if profile.risk_profile == "commercial_contract" and item.source_type == SourceType.CONTRACT:
        critical += 0.20
    if "exact_wording_required" in item.risk_tags:
        critical += 0.28
    if any(tag in item.risk_tags for tag in ["payment_default", "renewal", "termination", "executive_commitment", "customer_unhappy", "approval", "authority", "commitment", "remediation", "breach", "control_gap", "mitigation", "root_cause"]):
        critical += 0.20
    return min(1.0, critical)


def representation_policy(item: SourceItem, profile: TaskProfile) -> tuple[Representation, str]:
    tags = set(item.risk_tags)
    if item.source_type == SourceType.SLACK and item.authority < 0.45:
        return Representation.IGNORE, "low-authority Slack speculation excluded unless corroborated"
    if ("exact_wording_required" in tags) or item.source_type == SourceType.CONTRACT and (
        "termination" in tags or "obligation" in tags or "payment_default" in tags or "cure" in tags or "breach" in tags
    ):
        return Representation.EXACT_EXCERPT, "contractual obligation or ambiguity requires exact wording"
    if item.source_type == SourceType.BILLING:
        return Representation.STRUCTURED_FACT, "billing is structured operational evidence"
    if item.source_type == SourceType.SUPPORT:
        return Representation.SUMMARY, "support evidence is best represented as a trend summary"
    if item.source_type == SourceType.CRM:
        return Representation.STRUCTURED_FACT, "CRM status is compact but must be checked against operational evidence"
    if item.source_type == SourceType.EMAIL and ("executive_commitment" in tags or "customer_unhappy" in tags or "approval" in tags or "authority" in tags or "commitment" in tags or "exact_wording_required" in tags):
        return Representation.EXACT_EXCERPT, "executive/customer commitment requires preserving language"
    if item.source_type in {SourceType.SECURITY, SourceType.INTERNAL_NOTE, SourceType.CALL_NOTE}:
        return Representation.SUMMARY, "secondary source admitted only as compact summary when slot-relevant"
    return Representation.SUMMARY, "default compact representation"


def build_admission_reason(item: SourceItem, slots: list[str], authority: float, fresh: float, contradiction: float, criticality: float) -> str:
    reasons: list[str] = []
    if slots:
        reasons.append(f"fills required slot(s): {', '.join(slots)}")
    if authority >= 0.85:
        reasons.append("high-authority source")
    if fresh >= 0.75:
        reasons.append("recent evidence")
    if contradiction >= 0.45:
        reasons.append("potentially contradicts or qualifies other evidence")
    if criticality >= 0.6:
        reasons.append("task-critical evidence")
    return "; ".join(reasons) or "marginal candidate evidence"


def value_candidates(profile: TaskProfile, candidates: List[Candidate], already_admitted: Optional[List[AdmittedEvidence]] = None) -> List[CandidateValuation]:
    already_admitted = already_admitted or []
    admitted_topics = set(t for ev in already_admitted for t in ev.item.topics)
    vals: list[CandidateValuation] = []
    for cand in candidates:
        item = cand.item
        slots = matched_slots(item, profile)
        relevance = cand.candidate_score
        authority = item.authority
        fresh = freshness_score(item.freshness_days)
        novelty = 1.0 - min(0.85, len(set(item.topics) & admitted_topics) * 0.18)
        contradiction = contradiction_potential(item)
        criticality = task_criticality(item, profile)
        redundancy = 1.0 - novelty
        token_cost_penalty = min(1.0, item.token_cost / max(1, profile.token_budget))
        slot_fill_bonus = 0.40 if slots else 0.0
        representation, representation_reason = representation_policy(item, profile)
        if any(slot.name in slots and slot.exact_wording_required for slot in profile.required_slots):
            representation = Representation.EXACT_EXCERPT
            representation_reason = "matched exact-wording evidence slot; preserve source language"

        # v1.2: exact wording and conflict-pair evidence are no longer soft
        # afterthoughts. They get explicit valuation pressure so CAC reserves
        # attention for wording-sensitive and contradiction-sensitive evidence
        # rather than discovering them only if budget remains.
        exact_slot_bonus = 0.0
        for slot in profile.required_slots:
            if slot.name in slots and slot.exact_wording_required and representation in {Representation.EXACT_EXCERPT, Representation.FULL_SOURCE_SPAN}:
                exact_slot_bonus += 0.85

        text_for_pair = " ".join([item.text, item.title, " ".join(item.topics), " ".join(item.risk_tags)]).lower()
        positive_pair_signal = any(x in text_for_pair for x in ["healthy", "green", "on track", "low risk", "likely renew", "approve", "approved", "minor", "optimistic", "strategic", "business justification"])
        negative_pair_signal = any(x in text_for_pair for x in ["overdue", "p1", "escalation", "late", "unresolved", "breach", "terminate", "cannot recommend", "blocked", "gap", "missing", "lost export", "root cause", "dispute", "uncured", "downtime", "failed", "risk"])
        conflict_pair_bonus = 0.0
        if item.source_type in {SourceType.CRM, SourceType.BILLING, SourceType.SUPPORT, SourceType.CONTRACT, SourceType.EMAIL, SourceType.SECURITY, SourceType.INTERNAL_NOTE} and not metadata_distractor_signal(item) and item.authority >= 0.50:
            if positive_pair_signal or negative_pair_signal:
                conflict_pair_bonus = 0.30
            if profile.answer_target in {"renewal_risk", "contract_termination"} and (positive_pair_signal or negative_pair_signal):
                conflict_pair_bonus += 0.20

        admission_score = (
            1.05 * relevance + 1.20 * authority + 0.70 * fresh + 0.70 * novelty
            + 0.85 * contradiction + 1.25 * criticality + slot_fill_bonus
            + exact_slot_bonus + conflict_pair_bonus
            - 0.85 * redundancy - 0.62 * token_cost_penalty
        )
        if representation == Representation.IGNORE:
            admission_score -= 2.5
        # CAC is slot-oriented: non-slot candidates need trusted conflict-pair value to be admitted.
        trusted_conflict_source = item.source_type in {SourceType.CRM, SourceType.BILLING, SourceType.SUPPORT, SourceType.CONTRACT, SourceType.EMAIL} and not metadata_distractor_signal(item) and item.authority >= 0.55
        if not slots and (contradiction < 0.45 or not trusted_conflict_source):
            admission_score -= 1.25
        vals.append(CandidateValuation(
            item=item,
            relevance=round(relevance, 4), authority=round(authority, 4), freshness=round(fresh, 4),
            novelty=round(novelty, 4), contradiction_potential=round(contradiction, 4),
            task_criticality=round(criticality, 4), redundancy=round(redundancy, 4),
            token_cost_penalty=round(token_cost_penalty, 4), slot_fill_bonus=round(slot_fill_bonus, 4),
            admission_score=round(admission_score, 4), representation=representation,
            admission_reason=build_admission_reason(item, slots, authority, fresh, contradiction, criticality),
            representation_reason=representation_reason, slot_matches=slots,
        ))
    vals.sort(key=lambda v: v.admission_score, reverse=True)
    return vals


def admission_cost(item: SourceItem, representation: Representation) -> int:
    if representation == Representation.IGNORE:
        return 0
    if representation == Representation.METADATA_ONLY:
        return 10
    if representation == Representation.STRUCTURED_FACT:
        # v1.3 compact evidence packets: structured facts are normalized key/value
        # evidence, not prose chunks. This makes the benchmark test evidence
        # admission rather than accidental verbosity.
        return min(30, max(10, len(str(item.structured).split()) + 5))
    if representation == Representation.SUMMARY:
        return min(45, max(16, item.token_cost // 7))
    if representation == Representation.EXACT_EXCERPT:
        # Exact evidence is the operative span, not the whole chunk.
        return min(item.token_cost, 22)
    if representation == Representation.FULL_SOURCE_SPAN:
        return item.token_cost
    return item.token_cost
