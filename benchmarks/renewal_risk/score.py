from __future__ import annotations
from typing import Dict, Any
from cac.core.schemas import AccountDossier, EvidencePacket, EXACT_REPRESENTATIONS
from cac.core.slots import CANONICAL_SLOT_NAMES

EXACT_SLOT = "contract_renewal_or_termination_terms"


def score_packet(dossier: AccountDossier, packet: EvidencePacket) -> Dict[str, Any]:
    """Score an evidence packet against benchmark gold labels.

    The benchmark exposes two scores:
    - evidence_score: weighted diagnostic score for component performance.
    - decision_grade_score: stricter gated score for evidence-sensitive decisions.

    The decision-grade score treats certain failures as disqualifying caps rather
    than small additive penalties. This reflects the benchmark's central premise:
    evidence-sensitive workflows are conjunctive; one missing required element can
    invalidate the decision.
    """
    present = set(dossier.present_gold_slots)
    missing = set(dossier.missing_gold_slots)
    filled: set[str] = set()
    exact_preserved = False
    admitted_positive = False
    admitted_negative = False
    unsupported = 0
    distractor_count = 0
    distractor_tokens = 0
    irrelevant_context_tokens = 0
    low_authority_positive_admitted = False
    high_authority_negative_admitted = False

    for ev in packet.admitted:
        item = ev.item
        if item.gold_positive:
            admitted_positive = True
            if item.authority < 0.65:
                low_authority_positive_admitted = True
        if item.gold_negative:
            admitted_negative = True
            if item.authority >= 0.85:
                high_authority_negative_admitted = True
        if item.is_distractor:
            distractor_count += 1
            distractor_tokens += ev.token_cost
        if not item.gold_slots:
            unsupported += 1
            irrelevant_context_tokens += ev.token_cost
        for slot in item.gold_slots:
            if slot == EXACT_SLOT:
                if ev.representation in EXACT_REPRESENTATIONS:
                    filled.add(slot)
                    exact_preserved = True
            else:
                filled.add(slot)

    slot_fill_rate = len(filled & present) / max(1, len(present))
    exact_clause_preservation = 1.0 if EXACT_SLOT not in present or exact_preserved else 0.0
    contradiction_recall = (
        1.0
        if not dossier.has_contradiction
        else (1.0 if (admitted_positive and admitted_negative and packet.conflicts) else 0.0)
    )

    if missing:
        reported = set(packet.missing_slots)
        uncertainty_text = " ".join(packet.uncertainties).lower()
        reported |= {
            slot for slot in missing
            if slot.replace("_", " ") in uncertainty_text or slot in uncertainty_text
        }
        insufficient_evidence_calibration = len(reported & missing) / len(missing)
    else:
        insufficient_evidence_calibration = 1.0

    spurious_missing = [slot for slot in packet.missing_slots if slot not in missing and slot not in present]
    spurious_uncertainty_rate = min(1.0, len(spurious_missing) / max(1, len(packet.missing_slots)))

    admitted_count = max(1, len(packet.admitted))
    unsupported_claim_rate = min(1.0, unsupported / admitted_count)
    distractor_admission_rate = min(1.0, distractor_count / admitted_count)
    tokens = packet.budget_used.get("context_tokens", 0)
    irrelevant_context_share = irrelevant_context_tokens / max(1, tokens)
    relevance_penalty = 0.5 * distractor_admission_rate + 0.5 * irrelevant_context_share

    evidence_score = (
        0.34 * slot_fill_rate
        + 0.20 * exact_clause_preservation
        + 0.19 * contradiction_recall
        + 0.19 * insufficient_evidence_calibration
        + 0.03 * (1.0 - unsupported_claim_rate)
        + 0.03 * (1.0 - min(1.0, relevance_penalty))
        + 0.02 * (1.0 - spurious_uncertainty_rate)
    )

    decision_grade_score, gate_reasons = decision_grade_from_components(
        evidence_score=evidence_score,
        present=present,
        missing=missing,
        slot_fill_rate=slot_fill_rate,
        exact_clause_preservation=exact_clause_preservation,
        contradiction_recall=contradiction_recall,
        insufficient_evidence_calibration=insufficient_evidence_calibration,
        distractor_admission_rate=distractor_admission_rate,
        irrelevant_context_share=irrelevant_context_share,
        unsupported_claim_rate=unsupported_claim_rate,
        low_authority_positive_admitted=low_authority_positive_admitted,
        high_authority_negative_admitted=high_authority_negative_admitted,
        has_contradiction=dossier.has_contradiction,
    )

    return {
        "account_id": dossier.account_id,
        "method": packet.method,
        "context_tokens": tokens,
        "evidence_score": round(evidence_score, 4),
        "decision_grade_score": round(decision_grade_score, 4),
        "decision_grade_gate_reasons": ";".join(gate_reasons) if gate_reasons else "none",
        "slot_fill_rate": round(slot_fill_rate, 4),
        "contradiction_recall": round(contradiction_recall, 4),
        "exact_clause_preservation": round(exact_clause_preservation, 4),
        "insufficient_evidence_calibration": round(insufficient_evidence_calibration, 4),
        "unsupported_claim_rate": round(unsupported_claim_rate, 4),
        "distractor_admission_rate": round(distractor_admission_rate, 4),
        "irrelevant_context_tokens": irrelevant_context_tokens,
        "irrelevant_context_share": round(irrelevant_context_share, 4),
        "spurious_uncertainty_rate": round(spurious_uncertainty_rate, 4),
        "over_budget_tokens": packet.budget_used.get("over_budget_tokens", 0),
        "over_budget": packet.budget_used.get("over_budget", False),
        "quality_per_1k_tokens": round(evidence_score / max(tokens, 1) * 1000.0, 4),
        "decision_grade_per_1k_tokens": round(decision_grade_score / max(tokens, 1) * 1000.0, 4),
        "filled_gold_slots": sorted(filled & present),
        "missing_gold_slots": sorted(missing),
        "packet_missing_slots": packet.missing_slots,
        "missing_case_type": dossier.missing_case_type,
    }


def decision_grade_from_components(
    *,
    evidence_score: float,
    present: set[str],
    missing: set[str],
    slot_fill_rate: float,
    exact_clause_preservation: float,
    contradiction_recall: float,
    insufficient_evidence_calibration: float,
    distractor_admission_rate: float,
    irrelevant_context_share: float,
    unsupported_claim_rate: float,
    low_authority_positive_admitted: bool,
    high_authority_negative_admitted: bool,
    has_contradiction: bool,
) -> tuple[float, list[str]]:
    score = evidence_score
    reasons: list[str] = []

    def cap(max_score: float, reason: str) -> None:
        nonlocal score
        if score > max_score:
            score = max_score
        reasons.append(reason)

    if slot_fill_rate < 0.80:
        cap(0.72, "slot_underfill_cap_0.72")
    if EXACT_SLOT in present and exact_clause_preservation < 1.0:
        cap(0.65, "exact_clause_missing_cap_0.65")
    if missing and insufficient_evidence_calibration < 1.0:
        cap(0.70, "missing_evidence_not_disclosed_cap_0.70")
    if has_contradiction and contradiction_recall < 1.0:
        cap(0.75, "contradiction_not_surfaced_cap_0.75")
    if low_authority_positive_admitted and high_authority_negative_admitted and contradiction_recall < 1.0:
        cap(0.60, "authority_inversion_unresolved_cap_0.60")
    if distractor_admission_rate > 0.25 or irrelevant_context_share > 0.30:
        cap(0.80, "irrelevant_context_overload_cap_0.80")
    if unsupported_claim_rate > 0.0:
        cap(0.85, "unsupported_evidence_cap_0.85")

    return score, sorted(set(reasons))
