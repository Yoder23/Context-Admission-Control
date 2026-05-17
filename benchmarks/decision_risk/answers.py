from __future__ import annotations

from typing import Dict, Any, Tuple

from cac.core.schemas import AccountDossier, EvidencePacket, EXACT_REPRESENTATIONS
from cac.core.packet import excerpt


def generate_decision_answer(packet: EvidencePacket) -> str:
    """Deterministic label-aided answer generator used by DecisionRiskBench.

    This is not an LLM. It is a fixed proxy generator that uses benchmark labels
    to produce a decision-style answer from either a CAC evidence packet or a RAG
    chunk packet. The purpose is to test whether the admitted context object is
    answer-ready under the same deterministic policy, not to simulate model
    behavior.
    """
    admitted = packet.admitted
    lines = [f"Decision answer for {packet.entity} ({packet.answer_target})."]

    negative = any(ev.item.gold_negative for ev in admitted)
    positive = any(ev.item.gold_positive for ev in admitted)
    if packet.missing_slots:
        decision = "INSUFFICIENT_EVIDENCE"
    elif negative and positive:
        decision = "ESCALATE_WITH_CONFLICT"
    elif negative:
        decision = "ESCALATE_RISK"
    else:
        decision = "PROCEED_WITH_CAUTION"
    lines.append(f"Decision: {decision}.")

    if packet.conflicts:
        lines.append("Conflict: admitted evidence contains conflicting signals that must be resolved by authority and recency.")
    if packet.uncertainties:
        lines.append("Missing evidence / uncertainty:")
        for u in packet.uncertainties[:6]:
            lines.append(f"- {u}")

    lines.append("Evidence cited:")
    for ev in admitted[:10]:
        slots = ",".join(ev.slot_matches) if ev.slot_matches else "unmapped"
        if ev.representation in EXACT_REPRESENTATIONS:
            quote = excerpt(ev.item.text, max_words=45)
            lines.append(f"- [{ev.item.source_id}] {ev.item.source_type.value} exact evidence for {slots}: {quote}")
        else:
            lines.append(f"- [{ev.item.source_id}] {ev.item.source_type.value} {ev.representation.value} evidence for {slots}: {excerpt(ev.item.text, max_words=24)}")

    return "\n".join(lines)


def score_generated_answer(dossier: AccountDossier, packet: EvidencePacket, answer: str) -> Dict[str, Any]:
    """Score the deterministic generated answer.

    This is an answer-level proxy, not a human/LLM judge. It uses benchmark
    labels to check whether the generated answer discloses missing evidence,
    cites support, includes exact wording when required, surfaces contradictions,
    and avoids distractor-heavy context.
    """
    text = answer.lower()
    present = set(dossier.present_gold_slots)
    missing = set(dossier.missing_gold_slots)
    exact_slots = {slot for s in dossier.sources for slot in s.gold_slots if s.gold_exact_required}

    cited_sources = {ev.item.source_id for ev in packet.admitted if f"[{ev.item.source_id.lower()}]" in text or ev.item.source_id.lower() in text}
    cited_gold_sources = {ev.item.source_id for ev in packet.admitted if ev.item.gold_slots and ev.item.source_id in cited_sources}
    citation_support = len(cited_gold_sources) / max(1, len([ev for ev in packet.admitted if ev.item.gold_slots]))

    filled = set()
    exact_filled = set()
    for ev in packet.admitted:
        for slot in ev.item.gold_slots:
            if slot in exact_slots:
                if ev.representation in EXACT_REPRESENTATIONS and ev.item.source_id in cited_sources:
                    filled.add(slot); exact_filled.add(slot)
            else:
                if ev.item.source_id in cited_sources:
                    filled.add(slot)
    answer_slot_coverage = len(filled & present) / max(1, len(present))
    answer_exact_use = 1.0 if not exact_slots else len(exact_filled & exact_slots) / max(1, len(exact_slots))

    if missing:
        missing_disclosed = sum(1 for m in missing if m.lower() in text or m.replace('_',' ').lower() in text or 'insufficient_evidence' in text or 'missing evidence' in text) / len(missing)
    else:
        missing_disclosed = 1.0

    contradiction_handled = 1.0 if not dossier.has_contradiction else (1.0 if ('conflict' in text or 'contradict' in text or 'escalate_with_conflict' in text) and packet.conflicts else 0.0)
    distractors = sum(1 for ev in packet.admitted if ev.item.is_distractor)
    distractor_rate = distractors / max(1, len(packet.admitted))
    unsupported = sum(1 for ev in packet.admitted if not ev.item.gold_slots and not ev.item.is_distractor)
    unsupported_rate = unsupported / max(1, len(packet.admitted))

    answer_decision_score = (
        0.28 * answer_slot_coverage
        + 0.20 * answer_exact_use
        + 0.18 * missing_disclosed
        + 0.18 * contradiction_handled
        + 0.10 * citation_support
        + 0.06 * (1 - min(1.0, distractor_rate + unsupported_rate))
    )

    # Hard caps for answer-critical failures.
    caps = []
    if answer_exact_use < 1.0:
        answer_decision_score = min(answer_decision_score, 0.72); caps.append('answer_exact_wording_missing')
    if missing and missing_disclosed < 1.0:
        answer_decision_score = min(answer_decision_score, 0.70); caps.append('answer_missing_evidence_not_disclosed')
    if dossier.has_contradiction and contradiction_handled < 1.0:
        answer_decision_score = min(answer_decision_score, 0.75); caps.append('answer_contradiction_not_handled')
    if distractor_rate > 0.25:
        answer_decision_score = min(answer_decision_score, 0.80); caps.append('answer_distractor_overload')

    return {
        'generated_answer': answer.replace('\n', ' ')[:700],
        'generated_answer_score': round(answer_decision_score, 4),
        'generated_answer_safe': answer_decision_score >= 0.80,
        'generated_answer_slot_coverage': round(answer_slot_coverage, 4),
        'generated_answer_exact_use': round(answer_exact_use, 4),
        'generated_answer_missing_disclosure': round(missing_disclosed, 4),
        'generated_answer_contradiction_handling': round(contradiction_handled, 4),
        'generated_answer_citation_support': round(citation_support, 4),
        'generated_answer_caps': ';'.join(caps) if caps else 'none',
    }
